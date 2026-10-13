"""Sidebar navigation."""
from __future__ import annotations
import customtkinter as ctk
from . import widgets as w


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_nav, on_lock):
        super().__init__(master, fg_color=w.PANEL, width=220, corner_radius=0)
        self.pack_propagate(False)
        self.on_nav = on_nav
        self._buttons: dict[str, ctk.CTkButton] = {}

        ctk.CTkLabel(self, text="🛡  AEGIS", text_color=w.ACCENT,
                     font=("Segoe UI Black", 16)).pack(pady=(22, 0), padx=20, anchor="w")
        ctk.CTkLabel(self, text="VAULT", text_color=w.TEXT_DIM,
                     font=("Consolas", 10)).pack(padx=20, anchor="w")

        ctk.CTkFrame(self, fg_color=w.BORDER, height=1).pack(fill="x", pady=18, padx=14)

        for key, label, icon in [
            ("dashboard", "Dashboard", "▦"),
            ("files",     "Files",     "🗎"),
            ("notes",     "Notes",     "✎"),
            ("settings",  "Settings",  "⚙"),
        ]:
            self._buttons[key] = self._nav_btn(key, f"  {icon}   {label}")

        # spacer
        ctk.CTkFrame(self, fg_color="transparent").pack(expand=True, fill="both")

        w.neon_button(self, "🔒  Lock Vault", command=on_lock,
                      danger=True, width=180).pack(pady=(0, 18))

        self.set_active("dashboard")

    def _nav_btn(self, key: str, text: str):
        b = ctk.CTkButton(
            self, text=text, anchor="w",
            fg_color="transparent", hover_color=w.PANEL_2,
            text_color=w.TEXT, corner_radius=8, height=40,
            font=("Segoe UI", 12),
            command=lambda: self.on_nav(key),
        )
        b.pack(fill="x", padx=12, pady=3)
        return b

    def set_active(self, key: str):
        for k, b in self._buttons.items():
            if k == key:
                b.configure(fg_color=w.PANEL_2, text_color=w.ACCENT)
            else:
                b.configure(fg_color="transparent", text_color=w.TEXT)
