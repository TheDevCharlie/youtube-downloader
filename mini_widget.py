import tkinter as tk
import customtkinter as ctk

class MiniWidget(ctk.CTkToplevel):
    """
    A sleek, floating, always-on-top desktop widget positioned at the top-right
    of the screen allowing the user to track active download progress, speed,
    ETA, and control downloads while multitasking.
    """
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app

        # Window settings: frameless, floating, always on top
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry("320x135")

        # Position at top-right of primary display
        screen_w = self.winfo_screenwidth()
        pos_x = screen_w - 340
        pos_y = 35
        self.geometry(f"320x135+{pos_x}+{pos_y}")

        # Theme colors
        self.configure(fg_color=("#F2F2F2", "#0B0C0E"))

        # Draggable setup
        self._offset_x = 0
        self._offset_y = 0

        self._build_ui()

    def _build_ui(self):
        # Outer border card
        self.card = ctk.CTkFrame(
            self,
            fg_color=("#FFFFFF", "#181922"),
            corner_radius=8,
            border_width=1,
            border_color=("#E0E0E0", "#262733")
        )
        self.card.pack(fill="both", expand=True, padx=2, pady=2)
        self.card.grid_columnconfigure(0, weight=1)

        # 1. Header Drag Bar
        header = ctk.CTkFrame(self.card, fg_color="transparent", height=24)
        header.pack(fill="x", padx=8, pady=(6, 2))
        header.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            header,
            text="Charlie-yt • Mini Widget",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#222222", "#FFFFFF")
        )
        self.title_lbl.pack(side="left")

        # Control buttons: Expand / Restore & Close
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        self.expand_btn = ctk.CTkButton(
            btn_box,
            text="⤢",
            width=22,
            height=20,
            corner_radius=4,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E5E5E5", "#262733"),
            hover_color=("#DADADA", "#343646"),
            text_color=("#222222", "#FFFFFF"),
            command=self.restore_main_app
        )
        self.expand_btn.pack(side="left", padx=(0, 4))

        self.close_btn = ctk.CTkButton(
            btn_box,
            text="✕",
            width=22,
            height=20,
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#E5E5E5", "#262733"),
            hover_color=("#DADADA", "#343646"),
            text_color=("#222222", "#FFFFFF"),
            command=self.restore_main_app
        )
        self.close_btn.pack(side="left")

        # 2. Active Download Title Label
        self.item_title_lbl = ctk.CTkLabel(
            self.card,
            text="Ready to download",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#222222", "#FFFFFF"),
            anchor="w"
        )
        self.item_title_lbl.pack(fill="x", padx=10, pady=(2, 2))

        # 3. Progress Bar
        self.pbar = ctk.CTkProgressBar(self.card, height=8)
        self.pbar.set(0.0)
        self.pbar.pack(fill="x", padx=10, pady=(2, 4))

        # 4. Metrics & Action Row
        bot_row = ctk.CTkFrame(self.card, fg_color="transparent")
        bot_row.pack(fill="x", padx=10, pady=(0, 6))
        bot_row.grid_columnconfigure(0, weight=1)

        self.metrics_lbl = ctk.CTkLabel(
            bot_row,
            text="0% • 0.0 MB/s • ETA --",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#888888", "#8A8C98"),
            anchor="w"
        )
        self.metrics_lbl.pack(side="left")

        self.mini_pause_btn = ctk.CTkButton(
            bot_row,
            text="⏸",
            width=26,
            height=22,
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#E5E5E5", "#262733"),
            hover_color=("#DADADA", "#343646"),
            text_color=("#222222", "#FFFFFF"),
            command=self._on_mini_pause
        )
        self.mini_pause_btn.pack(side="right", padx=(4, 0))

        # Bind mouse drag events to header and card
        for w in [self.card, header, self.title_lbl]:
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.winfo_x()
        self._offset_y = event.y_root - self.winfo_y()

    def _on_drag(self, event):
        new_x = event.x_root - self._offset_x
        new_y = event.y_root - self._offset_y
        self.geometry(f"+{new_x}+{new_y}")

    def update_progress(self, percent, speed_str, eta_str, title_str, is_paused=False):
        try:
            self.pbar.set(percent / 100.0)
            status_txt = "Paused" if is_paused else f"ETA {eta_str}"
            self.metrics_lbl.configure(text=f"{int(percent)}% • {speed_str} • {status_txt}")
            if title_str:
                self.item_title_lbl.configure(text=title_str[:36] + ("..." if len(title_str) > 36 else ""))
            self.mini_pause_btn.configure(text="▶" if is_paused else "⏸")
        except Exception:
            pass

    def _on_mini_pause(self):
        self.parent_app._toggle_pause_download()

    def restore_main_app(self):
        self.destroy()
        self.parent_app.deiconify()
        self.parent_app.lift()
        self.parent_app.focus_force()
        self.parent_app.mini_widget = None
