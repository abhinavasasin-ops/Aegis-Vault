"""Animated lock / setup screen."""
from __future__ import annotations
import math
import tkinter as tk
import customtkinter as ctk

from . import widgets as w
from ..core import strength
from ..core.auth import AuthError, LockedOut


class LockScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=w.BG)
        self.app = app
        self.is_setup = app.db.any_user() is None
        self._build()
        self._anim_phase = 0.0
        self._animate()

    # ---- layout
    def _build(self):
        # Animated canvas (left side)
        self.canvas = tk.Canvas(self, bg=w.BG, highlightthickness=0, width=420)
        self.canvas.pack(side="left", fill="both", expand=False)

        # Form panel (right)
        form = ctk.CTkFrame(self, fg_color=w.PANEL, corner_radius=0)
        form.pack(side="right", fill="both", expand=True)

        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        title_text = "Initialize Vault" if self.is_setup else "Unlock AegisVault"
        subtitle = "Create your master credentials" if self.is_setup else "Enter your master password"

        ctk.CTkLabel(inner, text="AEGIS // VAULT", text_color=w.ACCENT,
                     font=("Segoe UI Black", 11)).pack(anchor="w")
        ctk.CTkLabel(inner, text=title_text, text_color=w.TEXT,
                     font=w.FONT_TITLE).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(inner, text=subtitle, text_color=w.TEXT_DIM,
                     font=w.FONT_BODY).pack(anchor="w", pady=(0, 18))

        uframe, self.user_entry = w.labeled_entry(inner, "Username")
        uframe.pack(fill="x", pady=6)
        self.user_entry.configure(width=320)

        pframe, self.pwd_entry = w.labeled_entry(inner, "Master password", show="•")
        pframe.pack(fill="x", pady=6)

        if self.is_setup:
            cframe, self.confirm_entry = w.labeled_entry(inner, "Confirm password", show="•")
            cframe.pack(fill="x", pady=6)
            self.strength_label = ctk.CTkLabel(inner, text="Strength: —",
                                               text_color=w.TEXT_DIM, font=w.FONT_BODY)
            self.strength_label.pack(anchor="w", pady=(8, 0))
            self.pwd_entry.bind("<KeyRelease>", self._update_strength)
        else:
            self.confirm_entry = None
            self.strength_label = None

        self.status = ctk.CTkLabel(inner, text="", text_color=w.DANGER, font=w.FONT_BODY)
        self.status.pack(anchor="w", pady=(10, 0))

        btn = w.neon_button(
            inner, "Create Vault" if self.is_setup else "Unlock",
            command=self._submit, width=320,
        )
        btn.pack(pady=(18, 0))
        self.pwd_entry.bind("<Return>", lambda e: self._submit())
        if self.confirm_entry:
            self.confirm_entry.bind("<Return>", lambda e: self._submit())

        ctk.CTkLabel(inner, text="AES-256-GCM • PBKDF2-SHA256 • SQLite",
                     text_color=w.TEXT_DIM, font=("Consolas", 10)).pack(pady=(20, 0))

    def _update_strength(self, _evt=None):
        if not self.strength_label:
            return
        sc, lab, color = strength.label(self.pwd_entry.get())
        self.strength_label.configure(text=f"Strength: {lab}", text_color=color)

    # ---- animation: rotating ring + scanning bar
    def _animate(self):
        c = self.canvas
        c.delete("all")
        try:
            wpx = c.winfo_width() or 420
            hpx = c.winfo_height() or 600
        except Exception:
            wpx, hpx = 420, 600
        cx, cy = wpx // 2, hpx // 2
        # Concentric rings
        for i, r in enumerate([170, 130, 95, 65]):
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          outline=w.BORDER, width=1)
        # Rotating arc
        ang = (self._anim_phase * 60) % 360
        c.create_arc(cx - 170, cy - 170, cx + 170, cy + 170,
                     start=ang, extent=70, style="arc",
                     outline=w.ACCENT, width=2)
        c.create_arc(cx - 130, cy - 130, cx + 130, cy + 130,
                     start=-ang * 1.4, extent=50, style="arc",
                     outline=w.ACCENT_2, width=2)
        # Pulsing core
        pulse = 18 + 6 * math.sin(self._anim_phase * 2)
        c.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse,
                      fill=w.ACCENT, outline="")
        c.create_text(cx, cy + 220, text="SECURE • ENCRYPTED • LOCAL",
                      fill=w.TEXT_DIM, font=("Consolas", 10))
        c.create_text(cx, cy - 220, text="🛡  AEGIS VAULT",
                      fill=w.TEXT, font=("Segoe UI Semibold", 18))
        self._anim_phase += 0.06
        self.after(40, self._animate)

    # ---- submit
    def _submit(self):
        username = self.user_entry.get().strip()
        password = self.pwd_entry.get()
        if not username or not password:
            self.status.configure(text="Username and password are required.")
            return
        try:
            if self.is_setup:
                if password != self.confirm_entry.get():
                    self.status.configure(text="Passwords do not match.")
                    return
                if strength.score(password) < 2:
                    self.status.configure(text="Choose a stronger password (mix case, digits, symbols).")
                    return
                session = self.app.auth.register(username, password)
            else:
                session = self.app.auth.login(username, password)
        except LockedOut as e:
            self.status.configure(text=f"Account locked. Try again after {e.until} UTC.")
            return
        except AuthError as e:
            self.status.configure(text=str(e))
            return
        except Exception as e:
            self.status.configure(text=f"Error: {e}")
            return
        self.app.on_authenticated(session)
