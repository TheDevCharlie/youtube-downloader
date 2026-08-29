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

# Set CustomTkinter theme and appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video & Playlist Downloader")
        self.geometry("960x860")
        self.minsize(840, 720)

        # Core logic & Config
        self.config_manager = ConfigManager()
        self.core = DownloaderCore()
        self.current_info = None
        self.is_fetching = False
        self.default_thumb_image = None

        # Setup UI
        self._setup_ui()
        self._load_saved_preferences()

    def _setup_ui(self):
        # Configure grid weight
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable container
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # 1. Header
        self._create_header(self.scroll_frame)

        # 2. URL Input Card
        self._create_url_section(self.scroll_frame)

        # 3. Metadata Preview Card
        self._create_preview_section(self.scroll_frame)

        # 4. Settings Card (Location & Format)
        self._create_settings_section(self.scroll_frame)

        # 5. Progress & Action Card
        self._create_progress_section(self.scroll_frame)

        # 6. Activity Log Section
        self._create_log_section(self.scroll_frame)

    def _create_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header_frame.grid_columnconfigure(0, weight=1)

        # Title & Subtitle
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")

        app_title = ctk.CTkLabel(
            title_box, 
            text="▶ YouTube Downloader Pro", 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#1f538d", "#3a86ff")
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_box, 
            text="High-speed video & playlist downloader with format selection and custom storage", 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        app_subtitle.pack(anchor="w")

        # Theme selector on top right
        theme_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        theme_box.grid(row=0, column=1, sticky="e")

        theme_label = ctk.CTkLabel(theme_box, text="Theme:", font=ctk.CTkFont(size=12))
        theme_label.pack(side="left", padx=(0, 6))

        self.theme_option = ctk.CTkOptionMenu(
            theme_box, 
            values=["Dark", "Light", "System"],
            width=90,
            height=28,
            command=self._change_theme
        )
        self.theme_option.set(self.config_manager.get("theme", "Dark"))
        self.theme_option.pack(side="left")

    def _create_url_section(self, parent):
        url_card = ctk.CTkFrame(parent, corner_radius=10)
        url_card.grid(row=1, column=0, sticky="ew", pady=(0, 12), padx=2)
        url_card.grid_columnconfigure(1, weight=1)

        url_icon = ctk.CTkLabel(url_card, text="🔗 URL:", font=ctk.CTkFont(size=14, weight="bold"))
        url_icon.grid(row=0, column=0, padx=(14, 8), pady=12, sticky="w")

        self.url_entry = ctk.CTkEntry(
            url_card, 
            placeholder_text="Paste video or playlist link (e.g. https://www.youtube.com/watch?v=... or playlist?list=...)",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.grid(row=0, column=1, padx=(0, 8), pady=12, sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._on_fetch_clicked())

        # Action buttons on URL row
        btn_box = ctk.CTkFrame(url_card, fg_color="transparent")
        btn_box.grid(row=0, column=2, padx=(0, 12), pady=12, sticky="e")

        self.paste_btn = ctk.CTkButton(
            btn_box, 
            text="📋 Paste", 
            width=75, 
            height=36,
            command=self._paste_from_clipboard
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.fetch_btn = ctk.CTkButton(
            btn_box, 
            text="🔍 Fetch Info", 
            width=95, 
            height=36,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
            command=self._on_fetch_clicked
        )
        self.fetch_btn.pack(side="left", padx=(0, 6))

        self.clear_btn = ctk.CTkButton(
            btn_box, 
            text="✕", 
            width=36, 
            height=36,
            fg_color="gray30",
            hover_color="gray40",
            command=self._clear_url
        )
        self.clear_btn.pack(side="left")

    def _create_preview_section(self, parent):
        self.preview_card = ctk.CTkFrame(parent, corner_radius=10)
        self.preview_card.grid(row=2, column=0, sticky="ew", pady=(0, 12), padx=2)
        self.preview_card.grid_columnconfigure(1, weight=1)

        # Thumbnail canvas/label on left
        self.thumb_label = ctk.CTkLabel(
            self.preview_card, 
            text="No Video / Playlist\nLoaded",
            width=200, 
            height=115,
            corner_radius=8,
            fg_color=("gray85", "gray20"),
            font=ctk.CTkFont(size=12)
        )
        self.thumb_label.grid(row=0, column=0, rowspan=2, padx=14, pady=14, sticky="nw")

        # Info on right
        info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=(12, 6))
        info_frame.grid_columnconfigure(0, weight=1)

        # Type badge + Duration
        top_meta = ctk.CTkFrame(info_frame, fg_color="transparent")
        top_meta.pack(fill="x", anchor="w", pady=(0, 4))

        self.badge_label = ctk.CTkLabel(
            top_meta,
            text="READY",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray75", "gray25"),
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.badge_label.pack(side="left", padx=(0, 8))

        self.meta_duration_label = ctk.CTkLabel(
            top_meta,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.meta_duration_label.pack(side="left")

        # Title
        self.meta_title_label = ctk.CTkLabel(
            info_frame, 
            text="Paste a link above and click 'Fetch Info' to inspect the video or playlist.",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.meta_title_label.pack(fill="x", anchor="w", pady=(2, 4))

        # Channel / Uploader
        self.meta_channel_label = ctk.CTkLabel(
            info_frame, 
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        self.meta_channel_label.pack(fill="x", anchor="w")

        # Playlist Items Selection bar (Shown when playlist detected)
        self.playlist_options_frame = ctk.CTkFrame(self.preview_card, fg_color=("gray90", "gray18"), corner_radius=8)
        self.playlist_options_frame.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=(0, 14))
        self.playlist_options_frame.grid_columnconfigure(1, weight=1)
        self.playlist_options_frame.grid_remove() # hidden by default

        pl_range_lbl = ctk.CTkLabel(
            self.playlist_options_frame, 
            text="📑 Download Specific Items:", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        pl_range_lbl.grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        self.pl_range_entry = ctk.CTkEntry(
            self.playlist_options_frame, 
            placeholder_text="All items (or specify range e.g. 1-10, 15, 20-25)",
            height=28,
            font=ctk.CTkFont(size=12)
        )
        self.pl_range_entry.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

    def _create_settings_section(self, parent):
        settings_card = ctk.CTkFrame(parent, corner_radius=10)
        settings_card.grid(row=3, column=0, sticky="ew", pady=(0, 12), padx=2)
        settings_card.grid_columnconfigure(1, weight=1)

        # 1. Download Location Row
        loc_icon = ctk.CTkLabel(settings_card, text="📁 Save Folder:", font=ctk.CTkFont(size=13, weight="bold"))
        loc_icon.grid(row=0, column=0, padx=(14, 8), pady=(14, 8), sticky="w")

        self.dir_entry = ctk.CTkEntry(
            settings_card,
            height=34,
            font=ctk.CTkFont(size=12)
        )
        self.dir_entry.grid(row=0, column=1, padx=(0, 8), pady=(14, 8), sticky="ew")

        dir_btn_box = ctk.CTkFrame(settings_card, fg_color="transparent")
        dir_btn_box.grid(row=0, column=2, padx=(0, 14), pady=(14, 8), sticky="e")

        self.browse_btn = ctk.CTkButton(
            dir_btn_box,
            text="Browse...",
            width=85,
            height=34,
            command=self._browse_directory
        )
        self.browse_btn.pack(side="left", padx=(0, 6))

        self.open_folder_btn = ctk.CTkButton(
            dir_btn_box,
            text="📂 Open",
            width=70,
            height=34,
            fg_color="gray30",
            hover_color="gray40",
            command=self._open_download_folder
        )
        self.open_folder_btn.pack(side="left")

        # Divider
        divider = ctk.CTkFrame(settings_card, height=1, fg_color=("gray80", "gray25"))
        divider.grid(row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=6)

        # 2. Format & Quality Selection
        format_options_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        format_options_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(6, 10))
        format_options_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Mode Selector (Video vs Audio)
        mode_box = ctk.CTkFrame(format_options_frame, fg_color="transparent")
        mode_box.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        
        mode_lbl = ctk.CTkLabel(mode_box, text="Download Mode:", font=ctk.CTkFont(size=12, weight="bold"))
        mode_lbl.pack(anchor="w", pady=(0, 4))

        self.mode_segment = ctk.CTkSegmentedButton(
            mode_box,
            values=["🎬 Video (MP4)", "🎵 Audio Only"],
            command=self._on_mode_changed,
            height=32
        )
        self.mode_segment.set("🎬 Video (MP4)")
        self.mode_segment.pack(anchor="w")

        # Quality / Resolution Selector
        self.quality_box = ctk.CTkFrame(format_options_frame, fg_color="transparent")
        self.quality_box.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=4)

        self.quality_lbl = ctk.CTkLabel(self.quality_box, text="Video Quality:", font=ctk.CTkFont(size=12, weight="bold"))
        self.quality_lbl.pack(anchor="w", pady=(0, 4))

        self.quality_dropdown = ctk.CTkOptionMenu(
            self.quality_box,
            values=[
                "Best Available",
                "4K (2160p)",
                "1440p (2K)",
                "1080p (FHD)",
                "720p (HD)",
                "480p (SD)",
                "360p"
            ],
            height=32,
            width=150,
            command=self._on_quality_changed
        )
        self.quality_dropdown.set(self.config_manager.get("video_quality", "Best Available"))
        self.quality_dropdown.pack(anchor="w")

        # Audio Format Selector (When Audio Only is selected)
        self.audio_fmt_box = ctk.CTkFrame(format_options_frame, fg_color="transparent")
        self.audio_fmt_box.grid(row=0, column=2, sticky="w", padx=(0, 10), pady=4)

        self.audio_fmt_lbl = ctk.CTkLabel(self.audio_fmt_box, text="Audio Format:", font=ctk.CTkFont(size=12, weight="bold"))
        self.audio_fmt_lbl.pack(anchor="w", pady=(0, 4))

        self.audio_fmt_dropdown = ctk.CTkOptionMenu(
            self.audio_fmt_box,
            values=["MP3", "M4A (AAC)", "FLAC", "WAV"],
            height=32,
            width=130,
            command=self._on_audio_fmt_changed
        )
        self.audio_fmt_dropdown.set(self.config_manager.get("audio_format", "MP3").upper())
        self.audio_fmt_dropdown.pack(anchor="w")

        # Audio Bitrate Selector
        self.bitrate_box = ctk.CTkFrame(format_options_frame, fg_color="transparent")
        self.bitrate_box.grid(row=0, column=3, sticky="w", padx=(0, 0), pady=4)

        self.bitrate_lbl = ctk.CTkLabel(self.bitrate_box, text="Audio Bitrate:", font=ctk.CTkFont(size=12, weight="bold"))
        self.bitrate_lbl.pack(anchor="w", pady=(0, 4))

        self.bitrate_dropdown = ctk.CTkOptionMenu(
            self.bitrate_box,
            values=["320 kbps (Best)", "256 kbps", "192 kbps", "128 kbps"],
            height=32,
            width=150,
            command=self._on_bitrate_changed
        )
        self.bitrate_dropdown.set(self.config_manager.get("audio_bitrate", "320 kbps"))
        self.bitrate_dropdown.pack(anchor="w")

        # 3. Checkbox toggles
        toggles_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        toggles_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 14))

        self.subfolder_check = ctk.CTkCheckBox(
            toggles_frame, 
            text="Create subfolder for playlists", 
            font=ctk.CTkFont(size=12),
            command=self._save_checkbox_states
        )
        self.subfolder_check.pack(side="left", padx=(0, 16))

        self.numbering_check = ctk.CTkCheckBox(
            toggles_frame, 
            text="Add playlist numbering (01, 02...)", 
            font=ctk.CTkFont(size=12),
            command=self._save_checkbox_states
        )
        self.numbering_check.pack(side="left", padx=(0, 16))

        self.thumb_embed_check = ctk.CTkCheckBox(
            toggles_frame, 
            text="Embed Cover Art/Thumbnail", 
            font=ctk.CTkFont(size=12),
            command=self._save_checkbox_states
        )
        self.thumb_embed_check.pack(side="left", padx=(0, 16))

        self.subtitles_check = ctk.CTkCheckBox(
            toggles_frame, 
            text="Embed Subtitles (CC)", 
            font=ctk.CTkFont(size=12),
            command=self._save_checkbox_states
        )
        self.subtitles_check.pack(side="left")

        # Update initial widget visibility based on mode
        self._update_format_controls_visibility()

    def _create_progress_section(self, parent):
        progress_card = ctk.CTkFrame(parent, corner_radius=10)
        progress_card.grid(row=4, column=0, sticky="ew", pady=(0, 12), padx=2)
        progress_card.grid_columnconfigure(0, weight=1)

        # Action Buttons Row
        action_box = ctk.CTkFrame(progress_card, fg_color="transparent")
        action_box.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 10))
        action_box.grid_columnconfigure(0, weight=1)

        self.download_btn = ctk.CTkButton(
            action_box,
            text="🚀  START DOWNLOAD",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=("#16a34a", "#22c55e"),
            hover_color=("#15803d", "#16a34a"),
            command=self._start_download
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            action_box,
            text="⏹  CANCEL",
            height=44,
            width=120,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#dc2626", "#ef4444"),
            hover_color=("#b91c1c", "#dc2626"),
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="right")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(progress_card, height=12)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        self.progress_bar.set(0)

        # Status text & Stats row
        stats_frame = ctk.CTkFrame(progress_card, fg_color="transparent")
        stats_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        stats_frame.grid_columnconfigure(0, weight=1)

        self.status_msg_label = ctk.CTkLabel(
            stats_frame,
            text="Ready to download",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.status_msg_label.grid(row=0, column=0, sticky="w")

        self.stats_details_label = ctk.CTkLabel(
            stats_frame,
            text="Speed: - | Downloaded: - / - | ETA: -",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="e"
        )
        self.stats_details_label.grid(row=0, column=1, sticky="e")

    def _create_log_section(self, parent):
        self.log_card = ctk.CTkFrame(parent, corner_radius=10)
        self.log_card.grid(row=5, column=0, sticky="ew", pady=(0, 12), padx=2)
        self.log_card.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(self.log_card, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        header_row.grid_columnconfigure(0, weight=1)

        log_title = ctk.CTkLabel(header_row, text="Activity Log", font=ctk.CTkFont(size=12, weight="bold"))
        log_title.pack(side="left")

        self.toggle_log_btn = ctk.CTkButton(
            header_row, 
            text="Hide Log", 
            width=70, 
            height=24, 
            font=ctk.CTkFont(size=11),
            fg_color="gray30",
            hover_color="gray40",
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            self.log_card, 
            height=120, 
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.log_visible = True

    def _load_saved_preferences(self):
        # Download directory
        saved_dir = self.config_manager.get("download_dir", os.path.expanduser("~/Downloads"))
        self.dir_entry.insert(0, saved_dir)

        # Checkboxes
        if self.config_manager.get("create_playlist_subfolder", True):
            self.subfolder_check.select()
        else:
            self.subfolder_check.deselect()

        if self.config_manager.get("number_playlist_items", True):
            self.numbering_check.select()
        else:
            self.numbering_check.deselect()

        if self.config_manager.get("embed_thumbnail", True):
            self.thumb_embed_check.select()
        else:
            self.thumb_embed_check.deselect()

        if self.config_manager.get("embed_subtitles", False):
            self.subtitles_check.select()
        else:
            self.subtitles_check.deselect()

        self._log("Application initialized. Ready.")

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
            self.toggle_log_btn.configure(text="Show Log")
            self.log_visible = False
        else:
            self.log_textbox.grid()
            self.toggle_log_btn.configure(text="Hide Log")
            self.log_visible = True

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.config_manager.set("theme", choice)

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
        self.meta_title_label.configure(text="Paste a link above and click 'Fetch Info' to inspect the video or playlist.")
        self.meta_channel_label.configure(text="")
        self.meta_duration_label.configure(text="")
        self.badge_label.configure(text="READY", fg_color=("gray75", "gray25"))
        self.thumb_label.configure(image=None, text="No Video / Playlist\nLoaded")
        self.playlist_options_frame.grid_remove()
        self.status_msg_label.configure(text="Ready")
        self.progress_bar.set(0)
        self.stats_details_label.configure(text="Speed: - | Downloaded: - / - | ETA: -")

    def _browse_directory(self):
        folder = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)
            self.config_manager.set("download_dir", folder)
            self._log(f"Download location changed to: {folder}")

    def _open_download_folder(self):
        folder = self.dir_entry.get().strip()
        if os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {e}")
        else:
            messagebox.showwarning("Warning", "The specified folder does not exist yet.")

    def _on_mode_changed(self, choice):
        self._update_format_controls_visibility()

    def _on_quality_changed(self, choice):
        self.config_manager.set("video_quality", choice)

    def _on_audio_fmt_changed(self, choice):
        self.config_manager.set("audio_format", choice.split()[0].lower())

    def _on_bitrate_changed(self, choice):
        self.config_manager.set("audio_bitrate", choice)

    def _save_checkbox_states(self):
        self.config_manager.set("create_playlist_subfolder", bool(self.subfolder_check.get()))
        self.config_manager.set("number_playlist_items", bool(self.numbering_check.get()))
        self.config_manager.set("embed_thumbnail", bool(self.thumb_embed_check.get()))
        self.config_manager.set("embed_subtitles", bool(self.subtitles_check.get()))

    def _update_format_controls_visibility(self):
        mode = self.mode_segment.get()
        if "Video" in mode:
            self.quality_box.grid()
            self.audio_fmt_box.grid_remove()
            self.bitrate_box.grid_remove()
            self.subtitles_check.configure(state="normal")
        else:
            self.quality_box.grid_remove()
            self.audio_fmt_box.grid()
            self.bitrate_box.grid()
            self.subtitles_check.configure(state="disabled")

    def _on_fetch_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a valid YouTube URL.")
            return

        if self.is_fetching:
            return

        self.is_fetching = True
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.status_msg_label.configure(text="Fetching video/playlist metadata...")
        self._log(f"Fetching metadata for: {url}")

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
            self.after(0, lambda: self.fetch_btn.configure(state="normal", text="🔍 Fetch Info"))

    def _apply_fetched_info(self, info):
        is_playlist = info.get('type') == 'playlist'
        title = info.get('title', 'Unknown')
        uploader = info.get('uploader', 'Unknown Channel')

        self.meta_title_label.configure(text=title)
        self.meta_channel_label.configure(text=f"By: {uploader}")

        if is_playlist:
            count = info.get('item_count', 0)
            self.badge_label.configure(text="📑 PLAYLIST", fg_color=("#d97706", "#f59e0b"))
            self.meta_duration_label.configure(text=f"({count} videos)")
            self.playlist_options_frame.grid()
            self.status_msg_label.configure(text=f"Loaded playlist with {count} videos.")
            self._log(f"Loaded Playlist: '{title}' ({count} items)")
        else:
            duration = info.get('duration', '00:00')
            self.badge_label.configure(text="🎬 VIDEO", fg_color=("#2563eb", "#3b82f6"))
            self.meta_duration_label.configure(text=f"Duration: {duration}")
            self.playlist_options_frame.grid_remove()
            self.status_msg_label.configure(text="Loaded video details. Ready to download.")
            self._log(f"Loaded Video: '{title}' ({duration})")

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
                
                # Resize maintaining aspect ratio
                ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(200, 115))
                self.after(0, lambda: self._set_thumbnail_image(ctk_image))
        except Exception as e:
            self._log(f"Failed to load thumbnail: {e}")

    def _set_thumbnail_image(self, ctk_image):
        self.thumb_label.configure(image=ctk_image, text="")

    def _handle_fetch_error(self, err_msg):
        self.status_msg_label.configure(text="Failed to load URL information.")
        messagebox.showerror("Fetch Error", f"Unable to retrieve details from YouTube:\n\n{err_msg}")

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a YouTube URL.")
            return

        download_dir = self.dir_entry.get().strip()
        if not download_dir:
            messagebox.showwarning("Folder Required", "Please specify a download folder.")
            return

        # Save config
        self.config_manager.set("download_dir", download_dir)
        self._save_checkbox_states()

        mode_str = self.mode_segment.get()
        mode = 'audio' if "Audio" in mode_str else 'video'

        options = {
            'mode': mode,
            'quality': self.quality_dropdown.get(),
            'audio_format': self.audio_fmt_dropdown.get().split()[0].lower(),
            'audio_bitrate': self.bitrate_dropdown.get(),
            'create_playlist_subfolder': bool(self.subfolder_check.get()),
            'number_playlist_items': bool(self.numbering_check.get()),
            'embed_thumbnail': bool(self.thumb_embed_check.get()),
            'embed_subtitles': bool(self.subtitles_check.get()),
            'playlist_items': self.pl_range_entry.get().strip() if self.current_info and self.current_info.get('type') == 'playlist' else None
        }

        # UI State update
        self.download_btn.configure(state="disabled", text="⏳ DOWNLOADING...")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_msg_label.configure(text="Initializing download...")
        self.stats_details_label.configure(text="Speed: - | Downloaded: - / - | ETA: -")

        self._log(f"--- Starting Download ---")
        self._log(f"URL: {url}")
        self._log(f"Mode: {mode.upper()} | Destination: {download_dir}")

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
                percent = data.get('percent', 0.0) / 100.0
                self.progress_bar.set(percent)

                filename = data.get('filename', '')
                pl_idx = data.get('playlist_index')
                pl_count = data.get('playlist_count')

                if pl_idx and pl_count:
                    self.status_msg_label.configure(text=f"[{pl_idx}/{pl_count}] Downloading: {filename[:45]}...")
                else:
                    self.status_msg_label.configure(text=f"Downloading: {filename[:50]}...")

                speed = data.get('speed', 'N/A')
                downloaded = data.get('downloaded_str', '')
                total = data.get('total_str', '')
                eta = data.get('eta', 'N/A')
                pct_str = f"{data.get('percent', 0.0):.1f}%"

                self.stats_details_label.configure(
                    text=f"Speed: {speed} | {downloaded} / {total} ({pct_str}) | ETA: {eta}"
                )

            elif status == 'processing':
                self.status_msg_label.configure(text=data.get('message', 'Processing / Merging...'))
                self._log(f"Processing: {data.get('filename', '')}")

        self.after(0, _update)

    def _on_download_status(self, msg):
        def _update():
            self.status_msg_label.configure(text=msg)
            self._log(f"[Status] {msg}")
        self.after(0, _update)

    def _on_download_complete(self):
        self.progress_bar.set(1.0)
        self.status_msg_label.configure(text="✓ Download Complete!")
        self.stats_details_label.configure(text="Finished successfully!")
        self._log("=== Download completed successfully! ===")
        messagebox.showinfo("Success", "Download completed successfully!\nFiles saved to selected folder.")

    def _on_download_cancelled(self):
        self.status_msg_label.configure(text="Download Cancelled.")
        self.stats_details_label.configure(text="Cancelled by user.")
        self._log("Download was cancelled.")
        messagebox.showwarning("Cancelled", "Download was cancelled.")

    def _on_download_failed(self, error):
        self.status_msg_label.configure(text="Download Failed.")
        self.stats_details_label.configure(text="Error occurred.")
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
