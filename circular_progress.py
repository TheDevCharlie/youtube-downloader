import tkinter as tk
import customtkinter as ctk

class CircularProgressRing(ctk.CTkFrame):
    def __init__(self, master, size=140, ring_width=8, bg_color="#181922", 
                 track_color="#262733", progress_color="#ffffff", text_color="#ffffff", **kwargs):
        super().__init__(master, fg_color=bg_color, corner_radius=18, **kwargs)
        
        self.size = size
        self.ring_width = ring_width
        self.track_color = track_color
        self.progress_color = progress_color
        self.percentage = 0.0

        # Canvas for drawing the ring
        self.canvas = tk.Canvas(
            self,
            width=self.size,
            height=self.size,
            bg=bg_color,
            highlightthickness=0
        )
        self.canvas.pack(expand=True, pady=(8, 4))

        self.sub_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color="#8a8c98"
        )
        self.sub_label.pack(pady=(0, 8))

        self.draw(0.0)

    def draw(self, percent):
        self.percentage = max(0.0, min(100.0, percent))
        self.canvas.delete("all")
        
        padding = self.ring_width + 4
        x0 = padding
        y0 = padding
        x1 = self.size - padding
        y1 = self.size - padding

        # Draw background track
        self.canvas.create_oval(
            x0, y0, x1, y1,
            outline=self.track_color,
            width=self.ring_width
        )

        # Draw active progress arc if > 0
        if self.percentage > 0.1:
            extent = -(self.percentage / 100.0) * 359.9
            self.canvas.create_arc(
                x0, y0, x1, y1,
                start=90,
                extent=extent,
                outline=self.progress_color,
                width=self.ring_width,
                style=tk.ARC
            )

        # Center percentage text
        center_x = self.size / 2
        center_y = self.size / 2
        pct_text = f"{int(self.percentage)}%" if self.percentage.is_integer() else f"{self.percentage:.1f}%"
        
        self.canvas.create_text(
            center_x, center_y,
            text=pct_text,
            fill="#ffffff",
            font=("Segoe UI", 18, "bold")
        )

    def set_progress(self, percent, status_text=None):
        self.draw(percent)
        if status_text:
            self.sub_label.configure(text=status_text)
