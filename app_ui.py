import os
import sys
import threading
import io
import requests
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config_manager import ConfigManager
from downloader_core import DownloaderCore, DownloadCancelledException
from circular_progress import CircularProgressRing

# Configure theme & colors
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Theme Palette Constants
BG_BLACK = "#0B0C0E"
CARD_BG = "#181922"
CARD_HOVER = "#20222e"
TEXT_PRIMARY = "#FFFFFF"
TEXT_MUTED = "#8A8C98"
ACCENT_BLUE = "#2563eb"
ACCENT_GREEN = "#16a34a"
BORDER_DARK = "#262733"


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal Media & Playlist Downloader")
        self.geometry("980x880")
        self.minsize(860, 760)
        self.configure(fg_color=BG_BLACK)

        # Core logic & Config
        self.config_manager = ConfigManager()
        self.core = DownloaderCore()
        self.current_info = None
        self.is_fetching = False

        # Setup UI
        self._setup_ui()
        self._load_saved_preferences()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable canvas container
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            corner_radius=0, 
            fg_color=BG_BLACK
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # 1. Header Bar
        self._create_header(self.scroll_frame)

        # 2. URL Input Capsule
        self._create_url_capsule(self.scroll_frame)

        # 3. 3-Column Bento Grid (Media Preview, Speed Metric, Progress Ring)
        self._create_bento_grid(self.scroll_frame)

        # 4. Settings Split Cards (Storage Location & Quality/Format)
        self._create_bottom_split_cards(self.scroll_frame)

        # 5. Download Action Bar
        self._create_action_bar(self.scroll_frame)

        # 6. Collapsible Activity Log Drawer
        self._create_log_drawer(self.scroll_frame)

    def _create_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header_frame.grid_columnconfigure(0, weight=1)

        # Title & Supported Platforms pills
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")

        title_lbl = ctk.CTkLabel(
            title_box,
            text="Downloader",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        title_lbl.pack(side="left", padx=(0, 14))

        # Platform badges pill
        platforms_pill = ctk.CTkFrame(title_box, fg_color=CARD_BG, corner_radius=20)
        platforms_pill.pack(side="left", pady=2)

        badge_text = "▶ YouTube • 📸 Instagram • 𝕏 Twitter • 📌 Pinterest • 🎵 TikTok"
        badge_lbl = ctk.CTkLabel(
            platforms_pill,
            text=badge_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
            padx=12,
            pady=4
        )
        badge_lbl.pack()

        # Action pills on right
        ctrl_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        ctrl_box.grid(row=0, column=1, sticky="e")

        self.theme_btn = ctk.CTkButton(
            ctrl_box,
            text="🌙 Dark",
            width=70,
            height=32,
            corner_radius=16,
            fg_color=CARD_BG,
            hover_color=CARD_HOVER,
            font=ctk.CTkFont(size=12),
            command=self._cycle_theme
        )
        self.theme_btn.pack(side="left", padx=(0, 8))

    def _create_url_capsule(self, parent):
        url_card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=18)
        url_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        url_card.grid_columnconfigure(0, weight=1)

        inner_frame = ctk.CTkFrame(url_card, fg_color="transparent")
        inner_frame.pack(fill="x", padx=16, pady=10)
        inner_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            inner_frame,
            placeholder_text="Enter or paste video, reel, post, or playlist URL...",
            height=40,
            corner_radius=12,
            fg_color="#101117",
            border_color=BORDER_DARK,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self._on_fetch_clicked())

        btn_box = ctk.CTkFrame(inner_frame, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self.paste_btn = ctk.CTkButton(
            btn_box,
            text="Paste",
            width=70,
            height=36,
            corner_radius=14,
            fg_color="#262733",
            hover_color="#343646",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._paste_from_clipboard
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.fetch_btn = ctk.CTkButton(
            btn_box,
            text="Inspect",
            width=85,
            height=36,
            corner_radius=14,
            fg_color=TEXT_PRIMARY,
            text_color="#000000",
            hover_color="#e0e0e0",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_fetch_clicked
        )
        self.fetch_btn.pack(side="left", padx=(0, 6))

        self.clear_btn = ctk.CTkButton(
            btn_box,
            text="✕",
            width=36,
            height=36,
            corner_radius=14,
            fg_color="#262733",
            hover_color="#343646",
            font=ctk.CTkFont(size=12),
            command=self._clear_url
        )
        self.clear_btn.pack(side="left")

    def _create_bento_grid(self, parent):
        bento_container = ctk.CTkFrame(parent, fg_color="transparent")
        bento_container.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        bento_container.grid_columnconfigure(0, weight=3) # Preview card (wider)
        bento_container.grid_columnconfigure(1, weight=2) # Speed metric card
        bento_container.grid_columnconfigure(2, weight=2) # Progress ring card

        # --- BENTO CARD 1: Media Preview ---
        self.preview_card = ctk.CTkFrame(bento_container, fg_color=CARD_BG, corner_radius=18, height=210)
        self.preview_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.preview_card.grid_propagate(False)
        self.preview_card.grid_columnconfigure(1, weight=1)

        # Thumbnail canvas / placeholder
        self.thumb_label = ctk.CTkLabel(
            self.preview_card,
            text="No Media\nSelected",
            width=170,
            height=110,
            corner_radius=12,
            fg_color="#101117",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=12)
        )
        self.thumb_label.grid(row=0, column=0, padx=14, pady=14, sticky="nw")

        # Metadata details
        meta_box = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        meta_box.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)
        meta_box.grid_columnconfigure(0, weight=1)

        # Platform + Type badge row
        badge_row = ctk.CTkFrame(meta_box, fg_color="transparent")
        badge_row.pack(fill="x", anchor="w", pady=(0, 4))

        self.platform_badge = ctk.CTkLabel(
            badge_row,
            text="READY",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#262733",
            corner_radius=8,
            padx=8,
            pady=2,
            text_color=TEXT_PRIMARY
        )
        self.platform_badge.pack(side="left", padx=(0, 6))

        self.meta_duration_label = ctk.CTkLabel(
            badge_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED
        )
        self.meta_duration_label.pack(side="left")

        # Title
        self.meta_title_label = ctk.CTkLabel(
            meta_box,
            text="Paste a link above to preview video, reel, or playlist details.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=230
        )
        self.meta_title_label.pack(fill="x", anchor="w", pady=(2, 2))

        # Channel / Creator
        self.meta_channel_label = ctk.CTkLabel(
            meta_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        self.meta_channel_label.pack(fill="x", anchor="w")

        # Playlist range capsule (embedded inside preview card)
        self.pl_box = ctk.CTkFrame(self.preview_card, fg_color="#101117", corner_radius=10)
        self.pl_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        self.pl_box.grid_columnconfigure(1, weight=1)
        self.pl_box.grid_remove() # hidden by default

        pl_lbl = ctk.CTkLabel(self.pl_box, text="Items Range:", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED)
        pl_lbl.grid(row=0, column=0, padx=(10, 6), pady=6, sticky="w")

        self.pl_range_entry = ctk.CTkEntry(
            self.pl_box,
            placeholder_text="All (or e.g. 1-10, 15)",
            height=26,
            fg_color=CARD_BG,
            border_color=BORDER_DARK,
            font=ctk.CTkFont(size=11)
        )
        self.pl_range_entry.grid(row=0, column=1, padx=(0, 10), pady=6, sticky="ew")

        # --- BENTO CARD 2: Speed Metric ---
        self.speed_card = ctk.CTkFrame(bento_container, fg_color=CARD_BG, corner_radius=18, height=210)
        self.speed_card.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        self.speed_card.grid_propagate(False)

        speed_inner = ctk.CTkFrame(self.speed_card, fg_color="transparent")
        speed_inner.pack(expand=True, padx=14, pady=14)

        self.speed_val_label = ctk.CTkLabel(
            speed_inner,
            text="0.0",
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.speed_val_label.pack(anchor="center")

        self.speed_unit_label = ctk.CTkLabel(
            speed_inner,
            text="MB/s Speed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_MUTED
        )
        self.speed_unit_label.pack(anchor="center", pady=(0, 8))

        self.size_detail_label = ctk.CTkLabel(
            speed_inner,
            text="0 MB / 0 MB",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED
        )
        self.size_detail_label.pack(anchor="center")

        # --- BENTO CARD 3: Circular Progress Ring ---
        self.progress_card = CircularProgressRing(
            bento_container,
            size=130,
            ring_width=8,
            bg_color=CARD_BG,
            track_color="#262733",
            progress_color=TEXT_PRIMARY
        )
        self.progress_card.grid(row=0, column=2, sticky="nsew")

    def _create_bottom_split_cards(self, parent):
        split_container = ctk.CTkFrame(parent, fg_color="transparent")
        split_container.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        split_container.grid_columnconfigure(0, weight=3) # Folder path card
        split_container.grid_columnconfigure(1, weight=3) # Format pill card

        # 1. Custom Save Folder Card
        folder_card = ctk.CTkFrame(split_container, fg_color=CARD_BG, corner_radius=18)
        folder_card.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        folder_card.grid_columnconfigure(0, weight=1)

        f_inner = ctk.CTkFrame(folder_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=14, pady=12)
        f_inner.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(
            f_inner,
            height=36,
            corner_radius=12,
            fg_color="#101117",
            border_color=BORDER_DARK,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_PRIMARY
        )
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        f_btns = ctk.CTkFrame(f_inner, fg_color="transparent")
        f_btns.grid(row=0, column=1, sticky="e")

        self.browse_btn = ctk.CTkButton(
            f_btns,
            text="Browse",
            width=70,
            height=34,
            corner_radius=12,
            fg_color="#262733",
            hover_color="#343646",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._browse_directory
        )
        self.browse_btn.pack(side="left", padx=(0, 4))

        self.open_folder_btn = ctk.CTkButton(
            f_btns,
            text="📂 Open",
            width=70,
            height=34,
            corner_radius=12,
            fg_color="#262733",
            hover_color="#343646",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_download_folder
        )
        self.open_folder_btn.pack(side="left")

        # 2. Format & Quality Segmented Pill Card
        format_card = ctk.CTkFrame(split_container, fg_color=CARD_BG, corner_radius=18)
        format_card.grid(row=0, column=1, sticky="ew")

        fmt_inner = ctk.CTkFrame(format_card, fg_color="transparent")
        fmt_inner.pack(fill="x", padx=14, pady=12)

        self.format_segment = ctk.CTkSegmentedButton(
            fmt_inner,
            values=["4K MP4", "1080p", "720p", "MP3 Audio", "WAV"],
            height=36,
            corner_radius=12,
            selected_color="#ffffff",
            selected_hover_color="#e0e0e0",
            unselected_color="#101117",
            unselected_hover_color="#20222e",
            text_color="#000000",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_format_segment_changed
        )
        self.format_segment.set("1080p")
        self.format_segment.pack(fill="x")

    def _create_action_bar(self, parent):
        action_card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=18)
        action_card.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        action_card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(action_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)
        inner.grid_columnconfigure(0, weight=1)

        self.download_btn = ctk.CTkButton(
            inner,
            text="🚀  START DOWNLOAD",
            height=46,
            corner_radius=14,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=TEXT_PRIMARY,
            text_color="#000000",
            hover_color="#e0e0e0",
            command=self._start_download
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            inner,
            text="⏹  CANCEL",
            height=46,
            width=110,
            corner_radius=14,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="right")

    def _create_log_drawer(self, parent):
        self.log_card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=18)
        self.log_card.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        self.log_card.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(self.log_card, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 6))
        header_row.grid_columnconfigure(0, weight=1)

        self.status_msg_label = ctk.CTkLabel(
            header_row, 
            text="Ready to download", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_MUTED
        )
        self.status_msg_label.pack(side="left")

        self.toggle_log_btn = ctk.CTkButton(
            header_row, 
            text="Activity Log", 
            width=85, 
            height=26, 
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            fg_color="#262733",
            hover_color="#343646",
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            self.log_card, 
            height=100, 
            corner_radius=10,
            fg_color="#101117",
            text_color="#c0c2ce",
            font=ctk.CTkFont(family="Consolas", size=10),
            state="disabled"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.log_visible = True

    def _load_saved_preferences(self):
        saved_dir = self.config_manager.get("download_dir", os.path.expanduser("~/Downloads"))
        self.dir_entry.insert(0, saved_dir)
        self._log("Application initialized in OLED Bento mode. Ready.")

    def _log(self, message):
        def _update():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _update)

    def _toggle_log(self):
        if self.log_visible:
            self.log_textbox.grid_remove()
            self.log_visible = False
        else:
            self.log_textbox.grid()
            self.log_visible = True

    def _cycle_theme(self):
        curr = ctk.get_appearance_mode()
        if curr == "Dark":
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="☀️ Light")
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="🌙 Dark")

    def _paste_from_clipboard(self):
        try:
            clipboard = self.clipboard_get().strip()
            if clipboard:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard)
                self._on_fetch_clicked()
        except Exception as e:
            self._log(f"Clipboard paste error: {e}")

    def _clear_url(self):
        self.url_entry.delete(0, "end")
        self.current_info = None
        self.meta_title_label.configure(text="Paste a link above to preview video, reel, or playlist details.")
        self.meta_channel_label.configure(text="")
        self.meta_duration_label.configure(text="")
        self.platform_badge.configure(text="READY", fg_color="#262733")
        self.thumb_label.configure(image=None, text="No Media\nSelected")
        self.pl_box.grid_remove()
        self.status_msg_label.configure(text="Ready")
        self.speed_val_label.configure(text="0.0")
        self.size_detail_label.configure(text="0 MB / 0 MB")
        self.progress_card.set_progress(0, "Ready")

    def _browse_directory(self):
        folder = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.config_manager.set("download_dir", folder)
            self._log(f"Location changed: {folder}")

    def _open_download_folder(self):
        folder = self.dir_entry.get().strip()
        if os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {e}")
        else:
            messagebox.showwarning("Warning", "The folder does not exist yet.")

    def _on_format_segment_changed(self, choice):
        self._log(f"Selected format: {choice}")

    def _on_fetch_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a valid media or playlist URL.")
            return

        if self.is_fetching:
            return

        self.is_fetching = True
        self.fetch_btn.configure(state="disabled", text="...")
        self.status_msg_label.configure(text="Inspecting media source...")
        self._log(f"Inspecting URL: {url}")

        threading.Thread(target=self._fetch_info_worker, args=(url,), daemon=True).start()

    def _fetch_info_worker(self, url):
        try:
            info = self.core.fetch_info(url)
            self.current_info = info
            self.after(0, lambda: self._apply_fetched_info(info))
        except Exception as e:
            self._log(f"Error fetching info: {e}")
            self.after(0, lambda: self._handle_fetch_error(str(e)))
        finally:
            self.is_fetching = False
            self.after(0, lambda: self.fetch_btn.configure(state="normal", text="Inspect"))

    def _apply_fetched_info(self, info):
        is_playlist = info.get('type') == 'playlist'
        platform = info.get('platform', {'name': 'Media', 'badge': '🎬 Media', 'color': '#3b82f6'})
        title = info.get('title', 'Unknown')
        uploader = info.get('uploader', 'Creator')

        self.meta_title_label.configure(text=title)
        self.meta_channel_label.configure(text=f"By: {uploader}")
        self.platform_badge.configure(text=platform['badge'], fg_color=platform.get('color', '#262733'))

        if is_playlist:
            count = info.get('item_count', 0)
            self.meta_duration_label.configure(text=f"• {count} items")
            self.pl_box.grid()
            self.status_msg_label.configure(text=f"Loaded {platform['name']} playlist with {count} items.")
            self._log(f"Loaded Playlist: '{title}' ({count} items)")
        else:
            duration = info.get('duration', 'Clip')
            self.meta_duration_label.configure(text=f"• {duration}")
            self.pl_box.grid_remove()
            self.status_msg_label.configure(text=f"Loaded {platform['name']} media details.")
            self._log(f"Loaded Media: '{title}' ({duration})")

        # Load Thumbnail
        thumb_url = info.get('thumbnail')
        if thumb_url:
            threading.Thread(target=self._load_thumbnail_worker, args=(thumb_url,), daemon=True).start()

    def _load_thumbnail_worker(self, thumb_url):
        try:
            resp = requests.get(thumb_url, timeout=10)
            if resp.status_code == 200:
                img_data = resp.content
                image = Image.open(io.BytesIO(img_data))
                ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(170, 110))
                self.after(0, lambda: self._set_thumbnail_image(ctk_image))
        except Exception as e:
            self._log(f"Thumbnail load failed: {e}")

    def _set_thumbnail_image(self, ctk_image):
        self.thumb_label.configure(image=ctk_image, text="")

    def _handle_fetch_error(self, err_msg):
        self.status_msg_label.configure(text="Failed to inspect URL.")
        messagebox.showerror("Inspection Error", f"Unable to retrieve media details:\n\n{err_msg}")

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a media URL.")
            return

        download_dir = self.dir_entry.get().strip()
        if not download_dir:
            messagebox.showwarning("Folder Required", "Please specify a save folder.")
            return

        self.config_manager.set("download_dir", download_dir)

        # Parse selected format
        fmt_choice = self.format_segment.get()
        if "MP3" in fmt_choice:
            mode = 'audio'
            quality = 'Best Available'
            audio_format = 'mp3'
        elif "WAV" in fmt_choice:
            mode = 'audio'
            quality = 'Best Available'
            audio_format = 'wav'
        elif "4K" in fmt_choice:
            mode = 'video'
            quality = '4K (2160p)'
            audio_format = 'mp3'
        elif "720p" in fmt_choice:
            mode = 'video'
            quality = '720p (HD)'
            audio_format = 'mp3'
        else:
            mode = 'video'
            quality = '1080p (FHD)'
            audio_format = 'mp3'

        options = {
            'mode': mode,
            'quality': quality,
            'audio_format': audio_format,
            'audio_bitrate': '320',
            'create_playlist_subfolder': True,
            'number_playlist_items': True,
            'embed_thumbnail': True,
            'embed_subtitles': False,
            'playlist_items': self.pl_range_entry.get().strip() if self.current_info and self.current_info.get('type') == 'playlist' else None
        }

        # UI State update
        self.download_btn.configure(state="disabled", text="⏳ DOWNLOADING...")
        self.cancel_btn.configure(state="normal")
        self.progress_card.set_progress(0, "Starting...")
        self.speed_val_label.configure(text="0.0")
        self.status_msg_label.configure(text="Connecting to media stream...")

        self._log(f"--- Starting Download ---")
        self._log(f"Destination: {download_dir}")

        threading.Thread(target=self._download_worker, args=(url, download_dir, options), daemon=True).start()

    def _download_worker(self, url, download_dir, options):
        try:
            success = self.core.download(
                url=url,
                download_dir=download_dir,
                options=options,
                progress_callback=self._on_download_progress,
                status_callback=self._on_download_status
            )
            if success:
                self.after(0, self._on_download_complete)
        except DownloadCancelledException:
            self.after(0, self._on_download_cancelled)
        except Exception as e:
            self._log(f"Download Error: {str(e)}")
            self.after(0, lambda: self._on_download_failed(str(e)))
        finally:
            self.after(0, self._reset_download_ui)

    def _on_download_progress(self, data):
        def _update():
            status = data.get('status')
            if status == 'downloading':
                pct = data.get('percent', 0.0)
                eta = data.get('eta', 'N/A')
                self.progress_card.set_progress(pct, f"ETA {eta}")

                speed_str = data.get('speed', '0.0 MB/s')
                speed_match = speed_str.split()[0] if speed_str else "0.0"
                self.speed_val_label.configure(text=speed_match)

                downloaded = data.get('downloaded_str', '')
                total = data.get('total_str', '')
                self.size_detail_label.configure(text=f"{downloaded} / {total}")

                filename = data.get('filename', '')
                pl_idx = data.get('playlist_index')
                pl_count = data.get('playlist_count')

                if pl_idx and pl_count:
                    self.status_msg_label.configure(text=f"[{pl_idx}/{pl_count}] {filename[:40]}...")
                else:
                    self.status_msg_label.configure(text=f"Downloading: {filename[:45]}...")

            elif status == 'processing':
                self.progress_card.set_progress(99.0, "Processing...")
                self.status_msg_label.configure(text="Finalizing & Merging stream...")

        self.after(0, _update)

    def _on_download_status(self, msg):
        def _update():
            self.status_msg_label.configure(text=msg)
            self._log(f"[Status] {msg}")
        self.after(0, _update)

    def _on_download_complete(self):
        self.progress_card.set_progress(100.0, "Complete!")
        self.status_msg_label.configure(text="✓ Download Complete!")
        self._log("=== Download completed successfully! ===")
        messagebox.showinfo("Success", "Download completed successfully!\nFiles saved to selected folder.")

    def _on_download_cancelled(self):
        self.progress_card.set_progress(0.0, "Cancelled")
        self.status_msg_label.configure(text="Download Cancelled.")
        self._log("Download was cancelled.")
        messagebox.showwarning("Cancelled", "Download was cancelled.")

    def _on_download_failed(self, error):
        self.progress_card.set_progress(0.0, "Failed")
        self.status_msg_label.configure(text="Download Failed.")
        messagebox.showerror("Download Error", f"An error occurred during download:\n\n{error}")

    def _reset_download_ui(self):
        self.download_btn.configure(state="normal", text="🚀  START DOWNLOAD")
        self.cancel_btn.configure(state="disabled")

    def _cancel_download(self):
        if self.core.is_downloading:
            self._log("Cancelling download...")
            self.status_msg_label.configure(text="Cancelling download...")
            self.core.cancel()
            self.cancel_btn.configure(state="disabled")
