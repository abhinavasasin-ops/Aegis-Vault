"""Dashboard with vault stats and recent activity."""
from __future__ import annotations
import customtkinter as ctk
from . import widgets as w


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=w.BG)
        self.app = app
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        self.greeting = ctk.CTkLabel(top, text="", text_color=w.TEXT, font=w.FONT_TITLE)
        self.greeting.pack(side="left")

        # stats row
        self.stats_row = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_row.pack(fill="x", padx=24, pady=10)

        # activity
        ctk.CTkLabel(self, text="Recent activity", text_color=w.TEXT_DIM,
                     font=w.FONT_H2).pack(anchor="w", padx=24, pady=(18, 6))
        self.activity = ctk.CTkScrollableFrame(self, fg_color=w.PANEL,
                                               border_color=w.BORDER, border_width=1,
                                               corner_radius=10)
        self.activity.pack(fill="both", expand=True, padx=24, pady=(0, 18))

    def refresh(self):
        self.greeting.configure(text=f"Welcome back, {self.app.session.username}")
        for c in self.stats_row.winfo_children(): c.destroy()
        for c in self.activity.winfo_children(): c.destroy()

        files = self.app.db.list_files(self.app.session.user_id)
        notes = self.app.db.list_notes(self.app.session.user_id)
        total_size = sum(f["size_bytes"] for f in files)

        for label, value, accent in [
            ("Files",      str(len(files)),         w.ACCENT),
            ("Notes",      str(len(notes)),         w.ACCENT_2),
            ("Total size", w.human_size(total_size), w.ACCENT),
            ("Cipher",     "AES-256-GCM",           w.ACCENT_2),
        ]:
            self._stat(label, value, accent)

        for log in self.app.db.recent_logs(40):
            row = ctk.CTkFrame(self.activity, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=log["ts"], text_color=w.TEXT_DIM,
                         font=("Consolas", 10), width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=log["action"], text_color=w.ACCENT,
                         font=("Consolas", 10), width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=log["detail"] or "", text_color=w.TEXT,
                         font=("Consolas", 10), anchor="w").pack(side="left", fill="x", expand=True)

    def _stat(self, label, value, accent):
        card = ctk.CTkFrame(self.stats_row, fg_color=w.PANEL, border_color=w.BORDER,
                            border_width=1, corner_radius=12)
        card.pack(side="left", fill="x", expand=True, padx=6, ipady=10)
        ctk.CTkLabel(card, text=label, text_color=w.TEXT_DIM,
                     font=("Segoe UI", 11)).pack(anchor="w", padx=14, pady=(10, 0))
        ctk.CTkLabel(card, text=value, text_color=accent,
                     font=("Segoe UI Semibold", 22)).pack(anchor="w", padx=14)
