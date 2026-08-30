import tkinter as tk
import customtkinter as ctk

class CircularProgressRing(ctk.CTkFrame):
    def __init__(self, master, size=130, ring_width=7, **kwargs):
        super().__init__(
            master, 
            fg_color=("#FFFFFF", "#181922"), 
            corner_radius=8, 
            border_width=1,
            border_color=("#E0E0E0", "#262733"),
            **kwargs
        )
        
        self.size = size
        self.ring_width = ring_width
        self.percentage = 0.0

        # WOVE porcelain silver light palette & OLED dark palette
        self.colors = {
            "Light": {
                "bg": "#FFFFFF",
                "track": "#E8E8E8",
                "progress": "#222222",
                "text": "#222222",
                "sub": "#888888"
            },
            "Dark": {
                "bg": "#181922",
                "track": "#262733",
                "progress": "#FFFFFF",
                "text": "#FFFFFF",
                "sub": "#8A8C98"
            }
        }

        mode = ctk.get_appearance_mode()
        current_theme = self.colors.get(mode, self.colors["Dark"])

        self.canvas = tk.Canvas(
            self,
            width=self.size,
            height=self.size,
            bg=current_theme["bg"],
            highlightthickness=0
        )
        self.canvas.pack(expand=True, pady=(6, 2))

        self.sub_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#888888", "#8A8C98")
        )
        self.sub_label.pack(pady=(0, 6))

        self.draw(0.0)

    def draw(self, percent):
        self.percentage = max(0.0, min(100.0, percent))
        self.canvas.delete("all")
        
        mode = ctk.get_appearance_mode()
        theme = self.colors.get(mode, self.colors["Dark"])
        self.canvas.configure(bg=theme["bg"])

        padding = self.ring_width + 4
        x0 = padding
        y0 = padding
        x1 = self.size - padding
        y1 = self.size - padding

        # Draw background track
        self.canvas.create_oval(
            x0, y0, x1, y1,
            outline=theme["track"],
            width=self.ring_width
        )

        # Draw active progress arc if > 0
        if self.percentage > 0.1:
            extent = -(self.percentage / 100.0) * 359.9
            self.canvas.create_arc(
                x0, y0, x1, y1,
                start=90,
                extent=extent,
                outline=theme["progress"],
                width=self.ring_width,
                style=tk.ARC
            )

        center_x = self.size / 2
        center_y = self.size / 2
        pct_text = f"{int(self.percentage)}%" if self.percentage.is_integer() else f"{self.percentage:.1f}%"
        
        self.canvas.create_text(
            center_x, center_y,
            text=pct_text,
            fill=theme["text"],
            font=("Segoe UI", 16, "bold")
        )

    def set_progress(self, percent, status_text=None):
        self.draw(percent)
        if status_text:
            self.sub_label.configure(text=status_text)

    def refresh_theme(self):
        self.draw(self.percentage)
