import os
import sys
import threading
import uuid
import io
import requests
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config_manager import ConfigManager
from downloader_core import DownloaderCore, DownloadCancelledException
from circular_progress import CircularProgressRing

# Configure theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# WOVE Porcelain Silver Light Palette & Deep OLED Dark Palette
THEME_BG = ("#F2F2F2", "#0B0C0E")
THEME_CARD = ("#FFFFFF", "#181922")
THEME_CARD_INNER = ("#EAEAEA", "#12131A")
THEME_BORDER = ("#E0E0E0", "#262733")

# High-Contrast Monochrome Text
THEME_TEXT_PRIMARY = ("#222222", "#FFFFFF")
THEME_TEXT_MUTED = ("#888888", "#8A8C98")

# Button Styling (Rectangular & High-Contrast)
THEME_BTN_PRIMARY_BG = ("#222222", "#FFFFFF")
THEME_BTN_PRIMARY_HOVER = ("#3D3D3D", "#E2E8F0")
THEME_BTN_PRIMARY_TEXT = ("#FFFFFF", "#000000")

THEME_BTN_SECONDARY_BG = ("#E5E5E5", "#262733")
THEME_BTN_SECONDARY_HOVER = ("#DADADA", "#343646")
THEME_BTN_SECONDARY_TEXT = ("#222222", "#FFFFFF")

THEME_ACCENT_BLUE = ("#2563EB", "#3B82F6")
THEME_ACCENT_RED = ("#DC2626", "#EF4444")
THEME_ACCENT_GREEN = ("#16A34A", "#22C55E")

# Crisp Rectangular Radius
CORNER_RADIUS = 8
CORNER_RADIUS_SM = 6


def generate_play_icon():
    """Generate a clean play button icon image."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(24, 25, 34, 255))
    draw.polygon([(26, 18), (26, 46), (46, 32)], fill=(255, 255, 255, 255))
    return img


class QueueItem:
    def __init__(self, url, info, options, save_dir, item_id=None, status="Queued"):
        self.id = item_id or str(uuid.uuid4())[:8]
        self.url = url
        self.info = info or {}
        self.options = options or {}
        self.save_dir = save_dir
        self.status = status  # Queued, Downloading, Paused, Complete, Failed, Cancelled
        self.progress = 100.0 if status == "Complete" else 0.0
        self.speed = "0.0 MB/s"
        self.eta = "--"
        self.downloaded_str = "0 MB"
        self.total_str = "0 MB"
        self.error_msg = ""
        
        # Display metadata
        self.title = self.info.get('title', 'Unknown Media')
        self.platform = self.info.get('platform', {'name': 'Media', 'badge': '🎬 Media', 'color': '#3B82F6'})
        self.is_playlist = self.info.get('type') == 'playlist'
        self.item_count = self.info.get('item_count', 1)
        self.entries = [dict(e) for e in self.info.get('entries', [])]

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'info': self.info,
            'options': self.options,
            'save_dir': self.save_dir,
            'status': self.status,
            'title': self.title,
            'platform': self.platform
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            url=d.get('url', ''),
            info=d.get('info', {'title': d.get('title', 'Media'), 'platform': d.get('platform')}),
            options=d.get('options', {}),
            save_dir=d.get('save_dir', ''),
            item_id=d.get('id'),
            status=d.get('status', 'Complete')
        )


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Universal Media & Playlist Downloader Pro")
        self.geometry("1040x960")
        self.minsize(560, 700)
        self.configure(fg_color=THEME_BG)

        # Set Window Title Bar & Taskbar Icon
        try:
            icon_img = generate_play_icon()
            self._icon_photo = ImageTk.PhotoImage(icon_img)
            self.iconphoto(False, self._icon_photo)
        except Exception:
            pass

        # Core logic & Config
        self.config_manager = ConfigManager()
        self.core = DownloaderCore()
        self.current_info = None
        self.is_fetching = False

        # Thumbnail memory cache
        self._thumb_cache = {}

        # Queue Management & Persistent History
        self.active_item = None
        self.queued_items = []
        self.completed_items = []
        self.queue_lock = threading.Lock()
        self.queue_running = False

        # Load Persistent History from disk
        self._load_saved_history()

        # Layout & Performance variables
        self.is_mobile_view = False
        self._resize_timer = None
        self._bg_photo = None
        self._last_bg_mode = None

        # Setup UI
        self._setup_ui()
        self._load_saved_preferences()

        # Bind resize with debouncing
        self.bind("<Configure>", self._on_window_configure)

    def _load_saved_history(self):
        try:
            raw_history = self.config_manager.load_history()
            for h in raw_history:
                item = QueueItem.from_dict(h)
                self.completed_items.append(item)
        except Exception as e:
            print(f"Error loading history: {e}")

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable canvas frame
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            corner_radius=0, 
            fg_color=THEME_BG
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # 1. Header Bar
        self._create_header(self.scroll_frame)

        # 2. URL Input Capsule
        self._create_url_capsule(self.scroll_frame)

        # 3. Bento Grid Container (Rectangular boxes)
        self._create_bento_grid(self.scroll_frame)

        # 4. Playlist Itemized Tracker (With item exclusion/removal option)
        self._create_playlist_tracker(self.scroll_frame)

        # 5. Settings Split Cards (Folder & Quality)
        self._create_bottom_split_cards(self.scroll_frame)

        # 6. Action Bar
        self._create_action_bar(self.scroll_frame)

        # 7. Separated Active Download & Queue/History Sections
        self._create_active_download_section(self.scroll_frame)
        self._create_queue_section(self.scroll_frame)

        # 8. Collapsible Activity Log Drawer
        self._create_log_drawer(self.scroll_frame)

        # Render background grid
        self.after(30, self._render_tear_free_grid_background)

    def _render_tear_free_grid_background(self):
        """
        Renders dot grid background appearing cleanly between UI elements.
        """
        try:
            canvas = self.scroll_frame._parent_canvas
            mode = ctk.get_appearance_mode()

            if self._bg_photo and self._last_bg_mode == mode:
                return

            self._last_bg_mode = mode
            tile_size = 28
            # WOVE porcelain silver dots in light mode, subtle dark dots in dark mode
            dot_color = (36, 38, 50, 255) if mode == "Dark" else (205, 205, 208, 255)
            bg_color = (11, 12, 14, 255) if mode == "Dark" else (242, 242, 242, 255)

            full_w, full_h = 2200, 2400
            pattern_img = Image.new("RGBA", (full_w, full_h), bg_color)
            draw = ImageDraw.Draw(pattern_img)

            for x in range(14, full_w, tile_size):
                for y in range(14, full_h, tile_size):
                    draw.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=dot_color)

            self._bg_photo = ImageTk.PhotoImage(pattern_img)
            canvas.delete("bg_pattern")
            canvas.create_image(0, 0, image=self._bg_photo, anchor="nw", tags="bg_pattern")
            canvas.tag_lower("bg_pattern")
        except Exception:
            pass

    def _create_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header_frame.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Downloader",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=THEME_TEXT_PRIMARY
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        self.theme_btn = ctk.CTkButton(
            header_frame,
            text="🌙 Dark",
            width=85,
            height=32,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._cycle_theme
        )
        self.theme_btn.grid(row=0, column=1, sticky="e")

    def _create_url_capsule(self, parent):
        url_card = ctk.CTkFrame(
            parent, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        url_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        url_card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(url_card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        inner.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            inner,
            placeholder_text="Enter or paste YouTube, TikTok, Instagram, Twitter, Pinterest URL...",
            height=38,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_CARD_INNER,
            border_width=1,
            border_color=THEME_BORDER,
            font=ctk.CTkFont(size=13),
            text_color=THEME_TEXT_PRIMARY
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self._on_fetch_clicked())

        btn_box = ctk.CTkFrame(inner, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self.paste_btn = ctk.CTkButton(
            btn_box,
            text="📋 Paste",
            width=75,
            height=36,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._paste_from_clipboard
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.fetch_btn = ctk.CTkButton(
            btn_box,
            text="🔍 Inspect",
            width=85,
            height=36,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_BTN_PRIMARY_BG,
            hover_color=THEME_BTN_PRIMARY_HOVER,
            text_color=THEME_BTN_PRIMARY_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_fetch_clicked
        )
        self.fetch_btn.pack(side="left", padx=(0, 6))

        self.clear_btn = ctk.CTkButton(
            btn_box,
            text="✕",
            width=36,
            height=36,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._clear_url
        )
        self.clear_btn.pack(side="left")

    def _create_bento_grid(self, parent):
        self.bento_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.bento_container.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self.bento_container.grid_columnconfigure(0, weight=3)
        self.bento_container.grid_columnconfigure(1, weight=2)
        self.bento_container.grid_columnconfigure(2, weight=2)

        # --- BENTO CARD 1: Media Preview ---
        self.preview_card = ctk.CTkFrame(
            self.bento_container, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS, 
            border_width=1,
            border_color=THEME_BORDER
        )
        self.preview_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.preview_card.grid_columnconfigure(1, weight=1)

        # Thumbnail
        self.thumb_label = ctk.CTkLabel(
            self.preview_card,
            text="No Media\nSelected",
            width=170,
            height=110,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_CARD_INNER,
            text_color=THEME_TEXT_MUTED,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.thumb_label.grid(row=0, column=0, padx=12, pady=12, sticky="nw")

        # Metadata details
        meta_box = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        meta_box.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        meta_box.grid_columnconfigure(0, weight=1)

        badge_row = ctk.CTkFrame(meta_box, fg_color="transparent")
        badge_row.pack(fill="x", anchor="w", pady=(0, 4))

        self.platform_badge = ctk.CTkLabel(
            badge_row,
            text="READY",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            text_color=THEME_BTN_SECONDARY_TEXT,
            corner_radius=CORNER_RADIUS_SM,
            padx=8,
            pady=2
        )
        self.platform_badge.pack(side="left", padx=(0, 6))

        self.meta_duration_label = ctk.CTkLabel(
            badge_row,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME_TEXT_MUTED
        )
        self.meta_duration_label.pack(side="left")

        # Title
        self.meta_title_label = ctk.CTkLabel(
            meta_box,
            text="Paste a link above to inspect video or playlist details.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME_TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=300
        )
        self.meta_title_label.pack(fill="x", anchor="w", pady=(2, 2))

        # Channel / Creator
        self.meta_channel_label = ctk.CTkLabel(
            meta_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=THEME_TEXT_MUTED,
            anchor="w"
        )
        self.meta_channel_label.pack(fill="x", anchor="w")

        # Playlist range capsule
        self.pl_box = ctk.CTkFrame(
            self.preview_card, 
            fg_color=THEME_CARD_INNER, 
            corner_radius=CORNER_RADIUS_SM,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.pl_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        self.pl_box.grid_columnconfigure(1, weight=1)
        self.pl_box.grid_remove()

        pl_lbl = ctk.CTkLabel(self.pl_box, text="Items Range:", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME_TEXT_MUTED)
        pl_lbl.grid(row=0, column=0, padx=(8, 6), pady=6, sticky="w")

        self.pl_range_entry = ctk.CTkEntry(
            self.pl_box,
            placeholder_text="All (or e.g. 1-10, 15)",
            height=26,
            fg_color=THEME_CARD,
            border_color=THEME_BORDER,
            text_color=THEME_TEXT_PRIMARY,
            font=ctk.CTkFont(size=11)
        )
        self.pl_range_entry.grid(row=0, column=1, padx=(0, 8), pady=6, sticky="ew")

        # --- BENTO CARD 2: Speed Metric ---
        self.speed_card = ctk.CTkFrame(
            self.bento_container, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS, 
            border_width=1,
            border_color=THEME_BORDER
        )
        self.speed_card.grid(row=0, column=1, sticky="nsew", padx=(0, 12))

        speed_inner = ctk.CTkFrame(self.speed_card, fg_color="transparent")
        speed_inner.pack(expand=True, fill="both", padx=12, pady=16)

        self.speed_val_label = ctk.CTkLabel(
            speed_inner,
            text="0.0",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color=THEME_TEXT_PRIMARY
        )
        self.speed_val_label.pack(anchor="center")

        self.speed_unit_label = ctk.CTkLabel(
            speed_inner,
            text="MB/s Speed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME_TEXT_MUTED
        )
        self.speed_unit_label.pack(anchor="center", pady=(0, 4))

        self.size_detail_label = ctk.CTkLabel(
            speed_inner,
            text="0 MB / 0 MB",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME_TEXT_MUTED
        )
        self.size_detail_label.pack(anchor="center")

        # --- BENTO CARD 3: Circular Progress Ring ---
        self.progress_card = CircularProgressRing(
            self.bento_container,
            size=130,
            ring_width=7
        )
        self.progress_card.grid(row=0, column=2, sticky="nsew")

    def _create_playlist_tracker(self, parent):
        self.playlist_track_card = ctk.CTkFrame(
            parent,
            fg_color=THEME_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.playlist_track_card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        self.playlist_track_card.grid_columnconfigure(0, weight=1)
        self.playlist_track_card.grid_remove()

        header = ctk.CTkFrame(self.playlist_track_card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(10, 6))

        self.pl_track_title = ctk.CTkLabel(
            header,
            text="📑 Playlist Items (0 selected)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME_TEXT_PRIMARY
        )
        self.pl_track_title.pack(side="left")

        # Quick select all / reset button
        self.pl_reset_btn = ctk.CTkButton(
            header,
            text="Select All",
            width=75,
            height=24,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            command=self._select_all_playlist_items
        )
        self.pl_reset_btn.pack(side="right")

        self.pl_items_container = ctk.CTkScrollableFrame(
            self.playlist_track_card,
            height=150,
            fg_color=THEME_CARD_INNER,
            corner_radius=CORNER_RADIUS_SM
        )
        self.pl_items_container.pack(fill="x", padx=12, pady=(0, 12))
        self.pl_items_container.grid_columnconfigure(1, weight=1)

    def _create_bottom_split_cards(self, parent):
        self.split_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.split_container.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        self.split_container.grid_columnconfigure(0, weight=3)
        self.split_container.grid_columnconfigure(1, weight=4)

        # 1. Custom Save Folder Card
        self.folder_card = ctk.CTkFrame(
            self.split_container, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.folder_card.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.folder_card.grid_columnconfigure(0, weight=1)

        f_inner = ctk.CTkFrame(self.folder_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=12, pady=10)
        f_inner.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(
            f_inner,
            height=36,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_CARD_INNER,
            border_width=1,
            border_color=THEME_BORDER,
            font=ctk.CTkFont(size=11),
            text_color=THEME_TEXT_PRIMARY
        )
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        f_btns = ctk.CTkFrame(f_inner, fg_color="transparent")
        f_btns.grid(row=0, column=1, sticky="e")

        self.browse_btn = ctk.CTkButton(
            f_btns,
            text="📁 Browse",
            width=75,
            height=34,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._browse_directory
        )
        self.browse_btn.pack(side="left", padx=(0, 4))

        self.open_folder_btn = ctk.CTkButton(
            f_btns,
            text="📂 Open",
            width=70,
            height=34,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_download_folder
        )
        self.open_folder_btn.pack(side="left")

        # 2. Format & Quality Segmented Pill Card
        self.format_card = ctk.CTkFrame(
            self.split_container, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.format_card.grid(row=0, column=1, sticky="ew")

        fmt_inner = ctk.CTkFrame(self.format_card, fg_color="transparent")
        fmt_inner.pack(fill="x", padx=10, pady=10)

        self.format_segment = ctk.CTkSegmentedButton(
            fmt_inner,
            values=["4K MP4", "1080p", "720p", "480p", "360p", "MP3 Audio", "WAV"],
            height=36,
            corner_radius=CORNER_RADIUS_SM,
            selected_color=THEME_ACCENT_BLUE,
            selected_hover_color=("#1D4ED8", "#2563EB"),
            unselected_color=THEME_CARD_INNER,
            unselected_hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_TEXT_PRIMARY,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_format_segment_changed
        )
        self.format_segment.set("1080p")
        self.format_segment.pack(fill="x")

    def _create_action_bar(self, parent):
        action_card = ctk.CTkFrame(
            parent, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        action_card.grid(row=5, column=0, sticky="ew", pady=(0, 14))
        action_card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(action_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)
        inner.grid_columnconfigure(0, weight=1)

        self.action_btn_box = ctk.CTkFrame(inner, fg_color="transparent")
        self.action_btn_box.pack(side="left", fill="x", expand=True)

        self.download_btn = ctk.CTkButton(
            self.action_btn_box,
            text="🚀  DOWNLOAD NOW",
            height=42,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME_BTN_PRIMARY_BG,
            hover_color=THEME_BTN_PRIMARY_HOVER,
            text_color=THEME_BTN_PRIMARY_TEXT,
            command=self._download_now
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.add_queue_btn = ctk.CTkButton(
            self.action_btn_box,
            text="➕  ADD TO QUEUE",
            height=42,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            command=self._add_to_queue
        )
        self.add_queue_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.pause_btn = ctk.CTkButton(
            inner,
            text="⏸  PAUSE",
            height=42,
            width=90,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            state="disabled",
            command=self._toggle_pause_download
        )
        self.pause_btn.pack(side="left", padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            inner,
            text="⏹  CANCEL",
            height=42,
            width=90,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME_ACCENT_RED,
            hover_color=("#B91C1C", "#DC2626"),
            text_color="#FFFFFF",
            state="disabled",
            command=self._cancel_active_download
        )
        self.cancel_btn.pack(side="right")

    def _create_active_download_section(self, parent):
        self.active_card = ctk.CTkFrame(
            parent, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.active_card.grid(row=6, column=0, sticky="ew", pady=(0, 14))
        self.active_card.grid_columnconfigure(0, weight=1)

        act_header = ctk.CTkFrame(self.active_card, fg_color="transparent")
        act_header.pack(fill="x", padx=14, pady=(10, 6))

        act_title = ctk.CTkLabel(
            act_header,
            text="⚡ Active Download",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME_TEXT_PRIMARY
        )
        act_title.pack(side="left")

        self.active_container = ctk.CTkFrame(self.active_card, fg_color=THEME_CARD_INNER, corner_radius=CORNER_RADIUS_SM)
        self.active_container.pack(fill="x", padx=12, pady=(0, 10))

        self.active_empty_lbl = ctk.CTkLabel(
            self.active_container,
            text="No active download in progress.",
            font=ctk.CTkFont(size=12),
            text_color=THEME_TEXT_MUTED,
            pady=10
        )
        self.active_empty_lbl.pack()

    def _create_queue_section(self, parent):
        self.queue_card = ctk.CTkFrame(
            parent, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.queue_card.grid(row=7, column=0, sticky="ew", pady=(0, 14))
        self.queue_card.grid_columnconfigure(0, weight=1)

        q_header = ctk.CTkFrame(self.queue_card, fg_color="transparent")
        q_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 8))
        q_header.grid_columnconfigure(0, weight=1)

        self.q_title_label = ctk.CTkLabel(
            q_header,
            text="📋 Queued Items & History",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME_TEXT_PRIMARY
        )
        self.q_title_label.pack(side="left")

        q_actions = ctk.CTkFrame(q_header, fg_color="transparent")
        q_actions.pack(side="right")

        self.clear_queued_btn = ctk.CTkButton(
            q_actions,
            text="Clear Queued",
            width=90,
            height=26,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            command=self._clear_queued_items
        )
        self.clear_queued_btn.pack(side="left", padx=(0, 6))

        self.clear_finished_btn = ctk.CTkButton(
            q_actions,
            text="Clear History",
            width=90,
            height=26,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            command=self._clear_finished_items
        )
        self.clear_finished_btn.pack(side="left")

        self.queue_items_frame = ctk.CTkFrame(self.queue_card, fg_color=THEME_CARD_INNER, corner_radius=CORNER_RADIUS_SM)
        self.queue_items_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.queue_items_frame.grid_columnconfigure(0, weight=1)

        self._refresh_queue_ui()

    def _create_log_drawer(self, parent):
        self.log_card = ctk.CTkFrame(
            parent, 
            fg_color=THEME_CARD, 
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=THEME_BORDER
        )
        self.log_card.grid(row=8, column=0, sticky="ew", pady=(0, 10))
        self.log_card.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(self.log_card, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 4))
        header_row.grid_columnconfigure(0, weight=1)

        self.status_msg_label = ctk.CTkLabel(
            header_row, 
            text="Ready to download", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME_TEXT_MUTED
        )
        self.status_msg_label.pack(side="left")

        self.toggle_log_btn = ctk.CTkButton(
            header_row, 
            text="Activity Log", 
            width=85, 
            height=26, 
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=THEME_BTN_SECONDARY_BG,
            hover_color=THEME_BTN_SECONDARY_HOVER,
            text_color=THEME_BTN_SECONDARY_TEXT,
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            self.log_card, 
            height=95, 
            corner_radius=CORNER_RADIUS_SM,
            fg_color=THEME_CARD_INNER,
            text_color=THEME_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Consolas", size=10),
            state="disabled"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.log_visible = True

    def _on_window_configure(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(60, self._process_window_resize)

    def _process_window_resize(self):
        try:
            w = self.winfo_width()
            h = self.winfo_height()

            is_phone = (w < 820) or (h > w * 1.15 and w < 900)
            if is_phone != self.is_mobile_view:
                self.is_mobile_view = is_phone
                self._apply_responsive_layout(is_phone)
        except Exception:
            pass

    def _apply_responsive_layout(self, is_phone):
        if is_phone:
            self.bento_container.grid_columnconfigure(0, weight=1)
            self.bento_container.grid_columnconfigure(1, weight=1)
            self.bento_container.grid_columnconfigure(2, weight=0)

            self.preview_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 10))
            self.meta_title_label.configure(wraplength=380)

            self.speed_card.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
            self.progress_card.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))

            self.split_container.grid_columnconfigure(0, weight=1)
            self.split_container.grid_columnconfigure(1, weight=0)
            self.folder_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 10))
            self.format_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        else:
            self.bento_container.grid_columnconfigure(0, weight=3)
            self.bento_container.grid_columnconfigure(1, weight=2)
            self.bento_container.grid_columnconfigure(2, weight=2)

            self.preview_card.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=(0, 12), pady=0)
            self.meta_title_label.configure(wraplength=300)

            self.speed_card.grid(row=0, column=1, columnspan=1, sticky="nsew", padx=(0, 12), pady=0)
            self.progress_card.grid(row=0, column=2, columnspan=1, sticky="nsew", padx=0, pady=0)

            self.split_container.grid_columnconfigure(0, weight=3)
            self.split_container.grid_columnconfigure(1, weight=4)
            self.folder_card.grid(row=0, column=0, columnspan=1, sticky="ew", padx=(0, 12), pady=0)
            self.format_card.grid(row=0, column=1, columnspan=1, sticky="ew", padx=0, pady=0)

    def _load_saved_preferences(self):
        saved_dir = self.config_manager.get("download_dir", os.path.expanduser("~/Downloads"))
        self.dir_entry.insert(0, saved_dir)
        self._log("Application ready.")

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
        
        self.progress_card.refresh_theme()
        self._render_tear_free_grid_background()

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
        self.meta_title_label.configure(text="Paste a link above to inspect video or playlist details.")
        self.meta_channel_label.configure(text="")
        self.meta_duration_label.configure(text="")
        self.platform_badge.configure(text="READY")
        self.thumb_label.configure(image=None, text="No Media\nSelected")
        self.pl_box.grid_remove()
        self.status_msg_label.configure(text="Ready")
        self.speed_val_label.configure(text="0.0")
        self.size_detail_label.configure(text="0 MB / 0 MB")
        self.progress_card.set_progress(0, "Ready")
        self.playlist_track_card.grid_remove()

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
            self.after(0, lambda: self.fetch_btn.configure(state="normal", text="🔍 Inspect"))

    def _apply_fetched_info(self, info):
        is_playlist = info.get('type') == 'playlist'
        platform = info.get('platform', {'name': 'Media', 'badge': '🎬 Media', 'color': '#3B82F6'})
        title = info.get('title', 'Unknown')
        uploader = info.get('uploader', 'Creator')

        self.meta_title_label.configure(text=title)
        self.meta_channel_label.configure(text=f"By: {uploader}")
        self.platform_badge.configure(text=platform['badge'], fg_color=platform.get('color', '#262733'))

        if is_playlist:
            count = info.get('item_count', 0)
            self.meta_duration_label.configure(text=f"• {count} items")
            self.pl_box.grid()
            self.playlist_track_card.grid()
            self._populate_playlist_tracker(info.get('entries', []))
            self.status_msg_label.configure(text=f"Loaded {platform['name']} playlist with {count} items.")
            self._log(f"Loaded Playlist: '{title}' ({count} items)")
        else:
            duration = info.get('duration', 'Clip')
            self.meta_duration_label.configure(text=f"• {duration}")
            self.pl_box.grid_remove()
            self.playlist_track_card.grid_remove()
            self.status_msg_label.configure(text=f"Loaded {platform['name']} media details.")
            self._log(f"Loaded Media: '{title}' ({duration})")

        # Load Thumbnail
        thumb_url = info.get('thumbnail')
        if thumb_url:
            if thumb_url in self._thumb_cache:
                self._set_thumbnail_image(self._thumb_cache[thumb_url])
            else:
                threading.Thread(target=self._load_thumbnail_worker, args=(thumb_url,), daemon=True).start()

    def _populate_playlist_tracker(self, entries):
        """Builds an itemized checklist with progress bars and an option to exclude/remove items."""
        for widget in self.pl_items_container.winfo_children():
            widget.destroy()

        active_entries = [e for e in entries if not e.get('excluded', False)]
        self.pl_track_title.configure(text=f"📑 Playlist Items ({len(active_entries)} of {len(entries)} selected)")
        self.pl_item_widgets = {}

        for e in entries:
            idx = e.get('index', 1)
            is_excluded = e.get('excluded', False)

            row = ctk.CTkFrame(
                self.pl_items_container, 
                fg_color=THEME_CARD if not is_excluded else THEME_CARD_INNER, 
                corner_radius=CORNER_RADIUS_SM
            )
            row.pack(fill="x", padx=4, pady=3)
            row.grid_columnconfigure(1, weight=1)

            idx_lbl = ctk.CTkLabel(
                row, 
                text=f"#{idx:02d}", 
                width=35, 
                font=ctk.CTkFont(size=11, weight="bold"), 
                text_color=THEME_TEXT_MUTED
            )
            idx_lbl.grid(row=0, column=0, padx=6, pady=4)

            t_text = e.get('title', f'Item {idx}')[:40]
            t_lbl = ctk.CTkLabel(
                row, 
                text=t_text, 
                font=ctk.CTkFont(size=11, weight="bold"), 
                text_color=THEME_TEXT_PRIMARY if not is_excluded else THEME_TEXT_MUTED, 
                anchor="w"
            )
            t_lbl.grid(row=0, column=1, padx=4, pady=4, sticky="w")

            pbar = ctk.CTkProgressBar(row, height=7, width=100)
            pbar.set(0.0)
            pbar.grid(row=0, column=2, padx=6, pady=4)

            status_text = "EXCLUDED" if is_excluded else "QUEUED"
            status_badge = ctk.CTkLabel(
                row,
                text=status_text,
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=THEME_CARD_INNER if not is_excluded else THEME_BORDER,
                text_color=THEME_TEXT_MUTED,
                corner_radius=4,
                padx=6,
                pady=1
            )
            status_badge.grid(row=0, column=3, padx=(0, 4), pady=4)

            # Toggle exclusion button
            del_icon = "+" if is_excluded else "✕"
            toggle_btn = ctk.CTkButton(
                row,
                text=del_icon,
                width=24,
                height=22,
                corner_radius=4,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=THEME_BTN_SECONDARY_BG,
                hover_color=THEME_BTN_SECONDARY_HOVER,
                text_color=THEME_BTN_SECONDARY_TEXT,
                command=lambda item_idx=idx: self._toggle_playlist_item_exclusion(item_idx)
            )
            toggle_btn.grid(row=0, column=4, padx=(0, 6), pady=4)

            self.pl_item_widgets[idx] = {
                'pbar': pbar,
                'status': status_badge,
                'title': t_lbl,
                'row': row
            }

    def _toggle_playlist_item_exclusion(self, idx):
        if self.current_info and 'entries' in self.current_info:
            for e in self.current_info['entries']:
                if e.get('index') == idx:
                    e['excluded'] = not e.get('excluded', False)
                    break
            self._populate_playlist_tracker(self.current_info['entries'])

    def _select_all_playlist_items(self):
        if self.current_info and 'entries' in self.current_info:
            for e in self.current_info['entries']:
                e['excluded'] = False
            self._populate_playlist_tracker(self.current_info['entries'])

    def _update_playlist_item_progress(self, idx, percent, is_active=True, is_done=False):
        if hasattr(self, 'pl_item_widgets') and idx in self.pl_item_widgets:
            w = self.pl_item_widgets[idx]
            if is_done:
                w['pbar'].set(1.0)
                w['status'].configure(text="DONE", fg_color=THEME_ACCENT_GREEN, text_color="#FFFFFF")
            elif is_active:
                w['pbar'].set(percent / 100.0)
                pct_str = f"{int(percent)}%"
                w['status'].configure(text=pct_str, fg_color=THEME_ACCENT_BLUE, text_color="#FFFFFF")

    def _load_thumbnail_worker(self, thumb_url):
        try:
            resp = requests.get(thumb_url, timeout=8)
            if resp.status_code == 200:
                img_data = resp.content
                image = Image.open(io.BytesIO(img_data))
                ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(170, 110))
                self._thumb_cache[thumb_url] = ctk_image
                self.after(0, lambda: self._set_thumbnail_image(ctk_image))
        except Exception as e:
            self._log(f"Thumbnail load note: {e}")

    def _set_thumbnail_image(self, ctk_image):
        self.thumb_label.configure(image=ctk_image, text="")

    def _handle_fetch_error(self, err_msg):
        self.status_msg_label.configure(text="Failed to inspect URL.")
        messagebox.showerror("Inspection Error", f"Unable to retrieve media details:\n\n{err_msg}")

    def _get_current_options(self):
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
        elif "480p" in fmt_choice:
            mode = 'video'
            quality = '480p (SD)'
            audio_format = 'mp3'
        elif "360p" in fmt_choice:
            mode = 'video'
            quality = '360p'
            audio_format = 'mp3'
        else:
            mode = 'video'
            quality = '1080p (FHD)'
            audio_format = 'mp3'

        # Compute selected playlist items filter
        playlist_items_filter = None
        if self.current_info and self.current_info.get('type') == 'playlist':
            custom_range = self.pl_range_entry.get().strip()
            if custom_range:
                playlist_items_filter = custom_range
            else:
                entries = self.current_info.get('entries', [])
                selected_indices = [str(e.get('index')) for e in entries if not e.get('excluded', False)]
                if selected_indices and len(selected_indices) < len(entries):
                    playlist_items_filter = ",".join(selected_indices)

        return {
            'mode': mode,
            'quality': quality,
            'audio_format': audio_format,
            'audio_bitrate': '320',
            'create_playlist_subfolder': True,
            'number_playlist_items': True,
            'embed_thumbnail': True,
            'embed_subtitles': False,
            'playlist_items': playlist_items_filter
        }

    def _add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a URL to add to the queue.")
            return

        download_dir = self.dir_entry.get().strip()
        if not download_dir:
            messagebox.showwarning("Folder Required", "Please specify a save folder.")
            return

        options = self._get_current_options()
        item = QueueItem(url, self.current_info, options, download_dir)

        with self.queue_lock:
            self.queued_items.append(item)

        self._refresh_queue_ui()
        self._log(f"Added to Queue: {item.title} ({options['quality']})")
        self.status_msg_label.configure(text=f"✓ Added to queue: {item.title[:35]}")

    def _download_now(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a URL.")
            return

        download_dir = self.dir_entry.get().strip()
        if not download_dir:
            messagebox.showwarning("Folder Required", "Please specify a save folder.")
            return

        self.config_manager.set("download_dir", download_dir)
        options = self._get_current_options()
        item = QueueItem(url, self.current_info, options, download_dir)

        with self.queue_lock:
            self.queued_items.insert(0, item)

        self._refresh_queue_ui()
        self._ensure_queue_running()

    def _ensure_queue_running(self):
        if not self.queue_running:
            self.queue_running = True
            self.cancel_btn.configure(state="normal")
            self.pause_btn.configure(state="normal", text="⏸  PAUSE")
            self.download_btn.configure(state="disabled", text="⏳ PROCESSING QUEUE...")
            threading.Thread(target=self._process_queue_worker, daemon=True).start()

    def _process_queue_worker(self):
        while True:
            item = None
            with self.queue_lock:
                if self.queued_items:
                    item = self.queued_items.pop(0)

            if not item:
                break

            self.active_item = item
            item.status = "Downloading"
            self.after(0, self._refresh_active_ui)
            self.after(0, self._refresh_queue_ui)

            self.after(0, lambda it=item: self.status_msg_label.configure(text=f"Downloading: {it.title[:40]}..."))
            self.after(0, lambda: self.progress_card.set_progress(0, "Starting..."))
            self.after(0, lambda: self.pause_btn.configure(state="normal", text="⏸  PAUSE"))
            self._log(f"--- Processing: {item.title} ---")

            if item.is_playlist:
                self.after(0, lambda it=item: self.playlist_track_card.grid())
                self.after(0, lambda it=item: self._populate_playlist_tracker(it.entries))

            try:
                success = self.core.download(
                    url=item.url,
                    download_dir=item.save_dir,
                    options=item.options,
                    progress_callback=self._on_download_progress,
                    status_callback=self._on_download_status
                )
                if success:
                    item.status = "Complete"
                    item.progress = 100.0
                    self.completed_items.insert(0, item)
                    self.config_manager.add_history_item(item.to_dict())
                    self._log(f"✓ Completed: {item.title}")
            except DownloadCancelledException:
                item.status = "Cancelled"
                self.completed_items.insert(0, item)
                self.config_manager.add_history_item(item.to_dict())
                self._log(f"⏹ Cancelled: {item.title}")
            except Exception as e:
                if self.core.cancel_event.is_set():
                    item.status = "Cancelled"
                else:
                    item.status = "Failed"
                    item.error_msg = str(e)
                    self._log(f"✕ Failed: {item.title} - {e}")
                self.completed_items.insert(0, item)
                self.config_manager.add_history_item(item.to_dict())

            self.active_item = None
            self.after(0, self._refresh_active_ui)
            self.after(0, self._refresh_queue_ui)

        # Queue finished
        self.queue_running = False
        self.active_item = None
        self.after(0, self._on_queue_all_finished)

    def _on_queue_all_finished(self):
        self.download_btn.configure(state="normal", text="🚀  DOWNLOAD NOW")
        self.cancel_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled", text="⏸  PAUSE")
        self.progress_card.set_progress(100.0, "All Done!")
        self.status_msg_label.configure(text="All downloads finished!")
        self._log("=== All downloads finished! ===")

    def _refresh_active_ui(self):
        for widget in self.active_container.winfo_children():
            widget.destroy()

        if not self.active_item:
            lbl = ctk.CTkLabel(
                self.active_container,
                text="No active download in progress.",
                font=ctk.CTkFont(size=12),
                text_color=THEME_TEXT_MUTED,
                pady=10
            )
            lbl.pack()
            return

        row = ctk.CTkFrame(self.active_container, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=8)
        row.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkLabel(
            row,
            text=f" {self.active_item.status.upper()} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=THEME_ACCENT_BLUE,
            text_color="#FFFFFF",
            corner_radius=4,
            padx=8,
            pady=3
        )
        badge.grid(row=0, column=0, padx=(0, 8), sticky="w")

        info_lbl = ctk.CTkLabel(
            row,
            text=f"{self.active_item.platform['badge']}  {self.active_item.title[:45]}  •  {self.active_item.options.get('quality', 'MP4')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME_TEXT_PRIMARY,
            anchor="w"
        )
        info_lbl.grid(row=0, column=1, sticky="w")

        stop_btn = ctk.CTkButton(
            row,
            text="Stop Active",
            width=80,
            height=26,
            corner_radius=CORNER_RADIUS_SM,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=THEME_ACCENT_RED,
            hover_color=("#B91C1C", "#DC2626"),
            text_color="#FFFFFF",
            command=self._cancel_active_download
        )
        stop_btn.grid(row=0, column=2, padx=4, sticky="e")

    def _refresh_queue_ui(self):
        for widget in self.queue_items_frame.winfo_children():
            widget.destroy()

        pending_count = len(self.queued_items)
        history_count = len(self.completed_items)

        self.q_title_label.configure(
            text=f"📋 Queued Items & History ({pending_count} pending • {history_count} in history)"
        )

        all_display_items = self.queued_items + self.completed_items

        if not all_display_items:
            empty_lbl = ctk.CTkLabel(
                self.queue_items_frame,
                text="No queued downloads or history. Inspect a link and click 'Add to Queue' to stage downloads.",
                font=ctk.CTkFont(size=12),
                text_color=THEME_TEXT_MUTED,
                pady=12
            )
            empty_lbl.pack()
            return

        for item in all_display_items:
            row = ctk.CTkFrame(self.queue_items_frame, fg_color=THEME_CARD, corner_radius=CORNER_RADIUS_SM)
            row.pack(fill="x", padx=8, pady=3)
            row.grid_columnconfigure(1, weight=1)

            status_colors = {
                "Queued": THEME_BTN_SECONDARY_BG,
                "Downloading": THEME_ACCENT_BLUE,
                "Paused": ("#D97706", "#F59E0B"),
                "Complete": THEME_ACCENT_GREEN,
                "Failed": THEME_ACCENT_RED,
                "Cancelled": ("#64748B", "#8A8C98")
            }
            bg_col = status_colors.get(item.status, THEME_BTN_SECONDARY_BG)
            txt_col = "#FFFFFF" if item.status in ["Downloading", "Paused", "Complete", "Failed", "Cancelled"] else THEME_BTN_SECONDARY_TEXT

            st_badge = ctk.CTkLabel(
                row,
                text=f" {item.status.upper()} ",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=bg_col,
                text_color=txt_col,
                corner_radius=4,
                padx=6,
                pady=2
            )
            st_badge.grid(row=0, column=0, padx=8, pady=6, sticky="w")

            title_text = item.title[:45] + ("..." if len(item.title) > 45 else "")
            info_lbl = ctk.CTkLabel(
                row,
                text=f"{item.platform['badge']}  {title_text}  •  {item.options.get('quality', 'MP4')}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=THEME_TEXT_PRIMARY,
                anchor="w"
            )
            info_lbl.grid(row=0, column=1, padx=4, pady=6, sticky="w")

            del_btn = ctk.CTkButton(
                row,
                text="✕",
                width=24,
                height=22,
                corner_radius=4,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=THEME_BTN_SECONDARY_BG,
                hover_color=THEME_BTN_SECONDARY_HOVER,
                text_color=THEME_BTN_SECONDARY_TEXT,
                command=lambda q_id=item.id: self._remove_single_item(q_id)
            )
            del_btn.grid(row=0, column=2, padx=8, pady=6, sticky="e")

    def _remove_single_item(self, q_id):
        with self.queue_lock:
            self.queued_items = [q for q in self.queued_items if q.id != q_id]
            self.completed_items = [q for q in self.completed_items if q.id != q_id]
            self.config_manager.history = [h for h in self.config_manager.history if h.get('id') != q_id]
            self.config_manager.save_history()
        self._refresh_queue_ui()

    def _clear_queued_items(self):
        with self.queue_lock:
            self.queued_items.clear()
        self._refresh_queue_ui()
        self._log("Pending queued items cleared.")

    def _clear_finished_items(self):
        with self.queue_lock:
            self.completed_items.clear()
            self.config_manager.clear_history()
        self._refresh_queue_ui()
        self._log("Download history cleared.")

    def _toggle_pause_download(self):
        if self.core.is_downloading:
            is_now_paused = self.core.toggle_pause()
            if is_now_paused:
                self.pause_btn.configure(text="▶  RESUME")
                self.status_msg_label.configure(text="Download Paused")
                self.progress_card.set_progress(self.progress_card.percentage, "Paused")
                if self.active_item:
                    self.active_item.status = "Paused"
                self._log("Download paused.")
            else:
                self.pause_btn.configure(text="⏸  PAUSE")
                self.status_msg_label.configure(text="Resuming download...")
                if self.active_item:
                    self.active_item.status = "Downloading"
                self._log("Download resumed.")
            self._refresh_active_ui()

    def _cancel_active_download(self):
        if self.core.is_downloading:
            self._log("Cancelling active download...")
            self.status_msg_label.configure(text="Cancelling active download...")
            self.core.cancel()
            if self.active_item:
                self.active_item.status = "Cancelled"
            self.cancel_btn.configure(state="disabled")
            self.pause_btn.configure(state="disabled")
            self.progress_card.set_progress(0, "Cancelled")
            self._refresh_active_ui()

    def _on_download_progress(self, data):
        def _update():
            status = data.get('status')
            if status == 'downloading':
                pct = data.get('percent', 0.0)
                eta = data.get('eta', 'N/A')
                status_txt = "Paused" if self.core.is_paused() else f"ETA {eta}"
                self.progress_card.set_progress(pct, status_txt)

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
                    self.status_msg_label.configure(text=f"[{pl_idx}/{pl_count}] {filename[:36]}...")
                    self._update_playlist_item_progress(pl_idx, pct, is_active=True)
                else:
                    self.status_msg_label.configure(text=f"Downloading: {filename[:42]}...")

            elif status == 'processing':
                pl_idx = data.get('playlist_index')
                if pl_idx:
                    self._update_playlist_item_progress(pl_idx, 100.0, is_done=True)
                self.progress_card.set_progress(99.0, "Merging...")
                self.status_msg_label.configure(text="Finalizing & Merging stream...")

        self.after(0, _update)

    def _on_download_status(self, msg):
        def _update():
            self.status_msg_label.configure(text=msg)
            self._log(f"[Status] {msg}")
        self.after(0, _update)
