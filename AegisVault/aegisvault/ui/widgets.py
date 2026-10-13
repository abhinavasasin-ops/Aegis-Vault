"""Shared theme constants and small widget helpers."""
from __future__ import annotations
import customtkinter as ctk

# Cybersecurity dark palette
BG        = "#0a0f14"
PANEL     = "#0f1620"
PANEL_2   = "#131c28"
BORDER    = "#1c2a3a"
ACCENT    = "#00e5a8"   # neon mint/cyan
ACCENT_2  = "#00b4ff"   # electric blue
DANGER    = "#ff3b6b"
TEXT      = "#dbe7ef"
TEXT_DIM  = "#7c8a99"

FONT_TITLE = ("Segoe UI Semibold", 22)
FONT_H2    = ("Segoe UI Semibold", 16)
FONT_BODY  = ("Segoe UI", 12)
FONT_MONO  = ("Consolas", 11)


def apply_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


def neon_button(parent, text: str, command=None, danger: bool = False, width: int = 140):
    color = DANGER if danger else ACCENT
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=color, hover_color="#00b48a" if not danger else "#cc2a55",
        text_color="#001018", corner_radius=10, height=36, width=width,
        font=("Segoe UI Semibold", 12),
    )


def ghost_button(parent, text: str, command=None, width: int = 140):
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color="transparent", hover_color=PANEL_2,
        text_color=TEXT, border_color=BORDER, border_width=1,
        corner_radius=10, height=36, width=width,
        font=("Segoe UI", 12),
    )


def labeled_entry(parent, label: str, show: str | None = None):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=label, text_color=TEXT_DIM, font=FONT_BODY,
                 anchor="w").pack(fill="x", padx=2)
    entry = ctk.CTkEntry(
        frame, show=show or "", fg_color=PANEL_2, border_color=BORDER,
        text_color=TEXT, height=36, corner_radius=8,
    )
    entry.pack(fill="x", pady=(4, 0))
    return frame, entry


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
