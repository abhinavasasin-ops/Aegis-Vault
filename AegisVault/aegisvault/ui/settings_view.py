"""Settings: auto-lock, import/export."""
from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from . import widgets as w
from ..config import AUTOLOCK_SECONDS, APP_DIR


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=w.BG)
        self.app = app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Settings", text_color=w.TEXT,
                     font=w.FONT_TITLE).pack(anchor="w", padx=24, pady=(20, 14))

        card = ctk.CTkFrame(self, fg_color=w.PANEL, border_color=w.BORDER,
                            border_width=1, corner_radius=12)
        card.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(card, text="Auto-lock", text_color=w.TEXT,
                     font=w.FONT_H2).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, text=f"Locks the vault after {AUTOLOCK_SECONDS // 60} minutes of inactivity.",
                     text_color=w.TEXT_DIM, font=w.FONT_BODY).pack(anchor="w", padx=16)
        self.timeout_var = tk.IntVar(value=self.app.autolock_seconds)
        slider = ctk.CTkSlider(card, from_=60, to=1800, variable=self.timeout_var,
                               command=lambda v: self.app.set_autolock(int(v)),
                               progress_color=w.ACCENT, button_color=w.ACCENT)
        slider.pack(fill="x", padx=16, pady=(8, 14))

        # Windows Hello
        h = ctk.CTkFrame(self, fg_color=w.PANEL, border_color=w.BORDER,
                         border_width=1, corner_radius=12)
        h.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(h, text="Windows Hello / fingerprint", text_color=w.TEXT,
                     font=w.FONT_H2).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            h,
            text="Require Windows Hello approval before encrypting, decrypting, exporting, or deleting files.",
            text_color=w.TEXT_DIM,
            font=w.FONT_BODY,
        ).pack(anchor="w", padx=16)
        self.biometric_var = tk.BooleanVar(value=self.app.require_biometric)
        row_hello = ctk.CTkFrame(h, fg_color="transparent")
        row_hello.pack(fill="x", padx=16, pady=(10, 6))
        self.biometric_switch = ctk.CTkSwitch(
            row_hello,
            text="Require for sensitive actions",
            variable=self.biometric_var,
            command=self._toggle_biometric,
            text_color=w.TEXT,
            fg_color=w.BORDER,
            progress_color=w.ACCENT,
            button_color=w.TEXT_DIM,
            button_hover_color=w.ACCENT_2,
        )
        self.biometric_switch.pack(side="left")
        w.ghost_button(row_hello, "Check status", command=self._refresh_biometric_status,
                       width=118).pack(side="right")
        self.biometric_status_label = ctk.CTkLabel(
            h,
            text="",
            text_color=w.TEXT_DIM,
            font=("Segoe UI", 11),
            justify="left",
        )
        self.biometric_status_label.pack(anchor="w", padx=16, pady=(0, 14))
        self._refresh_biometric_status()

        # backup
        b = ctk.CTkFrame(self, fg_color=w.PANEL, border_color=w.BORDER,
                        border_width=1, corner_radius=12)
        b.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(b, text="Backup & recovery", text_color=w.TEXT,
                     font=w.FONT_H2).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(b, text=f"Vault location: {APP_DIR}",
                     text_color=w.TEXT_DIM, font=("Consolas", 10)).pack(anchor="w", padx=16)
        row = ctk.CTkFrame(b, fg_color="transparent"); row.pack(fill="x", padx=16, pady=12)
        w.neon_button(row, "Export backup", command=self._export).pack(side="left", padx=4)
        w.ghost_button(row, "Import backup", command=self._import).pack(side="left", padx=4)

        # security info
        s = ctk.CTkFrame(self, fg_color=w.PANEL, border_color=w.BORDER,
                        border_width=1, corner_radius=12)
        s.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(s, text="Security profile", text_color=w.TEXT,
                     font=w.FONT_H2).pack(anchor="w", padx=16, pady=(14, 4))
        info = ("• Cipher: AES-256-GCM (authenticated)\n"
                "• KDF: PBKDF2-HMAC-SHA256, 200,000 iterations, 16-byte salt\n"
                "• Password storage: SHA-256(salt || password) — verification only\n"
                "• Brute-force guard: 5 failures → exponential lockout\n"
                "• Secure delete: 3-pass random overwrite + zero-fill")
        ctk.CTkLabel(s, text=info, text_color=w.TEXT_DIM, font=("Consolas", 10),
                     justify="left").pack(anchor="w", padx=16, pady=(0, 14))

    def _export(self):
        if not self.app.verify_sensitive_action("export an encrypted vault backup"):
            return
        dest = filedialog.asksaveasfilename(defaultextension=".zip",
                                            initialfile="aegisvault_backup.zip")
        if not dest: return
        try:
            self.app.vault.export_vault(dest)
            messagebox.showinfo("Backup", "Encrypted backup written.")
        except Exception as e:
            messagebox.showerror("Backup", str(e))

    def _import(self):
        if not self.app.verify_sensitive_action("import a vault backup"):
            return
        src = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")])
        if not src: return
        if not messagebox.askyesno("Import", "This will merge files into the vault directory. Continue?"):
            return
        try:
            self.app.vault.import_vault(src, APP_DIR)
            messagebox.showinfo("Import", "Backup imported. Restart AegisVault.")
        except Exception as e:
            messagebox.showerror("Import", str(e))

    def _refresh_biometric_status(self):
        status = self.app.biometric_status()
        color = w.ACCENT if status.available else w.TEXT_DIM
        self.biometric_status_label.configure(text=status.message, text_color=color)

    def _toggle_biometric(self):
        enabled = self.biometric_var.get()
        ok = self.app.set_biometric_required(enabled)
        if not ok:
            self.biometric_var.set(self.app.require_biometric)
        self._refresh_biometric_status()
