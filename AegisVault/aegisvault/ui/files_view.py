"""Files view: encrypted file explorer with in-vault folders."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from . import widgets as w

try:
    from tkinterdnd2 import DND_FILES  # noqa: F401
    HAS_DND = True
except Exception:
    HAS_DND = False


ALL_FILES = "__all__"
GENERAL = "General"


class FilesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=w.BG)
        self.app = app
        self.search_var = tk.StringVar()
        self.fav_only = tk.BooleanVar(value=False)
        self.current_folder: str = ALL_FILES
        self.folder_names: list[str] = [GENERAL]
        self._folder_buttons: dict[str, ctk.CTkButton] = {}
        self._build()
        self.refresh()

    def _build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.folder_panel = ctk.CTkFrame(self, fg_color=w.PANEL, width=260, corner_radius=0)
        self.folder_panel.grid(row=0, column=0, sticky="nsew")
        self.folder_panel.grid_propagate(False)

        ctk.CTkLabel(
            self.folder_panel,
            text="Vault folders",
            text_color=w.TEXT,
            font=w.FONT_H2,
        ).pack(anchor="w", padx=16, pady=(18, 8))

        folder_actions = ctk.CTkFrame(self.folder_panel, fg_color="transparent")
        folder_actions.pack(fill="x", padx=12, pady=(0, 10))
        w.neon_button(
            folder_actions,
            "New folder",
            command=self._new_folder,
            width=112,
        ).pack(side="left", padx=(0, 6))
        self.rename_btn = w.ghost_button(
            folder_actions,
            "Rename",
            command=self._rename_folder,
            width=94,
        )
        self.rename_btn.pack(side="left")

        self.folder_list = ctk.CTkScrollableFrame(self.folder_panel, fg_color=w.PANEL)
        self.folder_list.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self.delete_folder_btn = w.ghost_button(
            self.folder_panel,
            "Delete folder",
            command=self._delete_folder,
            width=228,
        )
        self.delete_folder_btn.pack(padx=16, pady=(0, 14))

        content = ctk.CTkFrame(self, fg_color=w.BG)
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(3, weight=1)
        content.columnconfigure(0, weight=1)

        top = ctk.CTkFrame(content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        top.columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            top,
            text="Encrypted Files",
            text_color=w.TEXT,
            font=w.FONT_TITLE,
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        w.ghost_button(top, "Export vault", command=self._export_vault, width=120).grid(
            row=0,
            column=1,
            padx=(8, 0),
        )
        w.neon_button(top, "Add file", command=self._add_dialog, width=110).grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        bar = ctk.CTkFrame(content, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=24)
        bar.columnconfigure(0, weight=1)

        search = ctk.CTkEntry(
            bar,
            textvariable=self.search_var,
            placeholder_text="Search files and tags...",
            fg_color=w.PANEL_2,
            border_color=w.BORDER,
            text_color=w.TEXT,
            height=34,
        )
        search.grid(row=0, column=0, sticky="ew")
        search.bind("<KeyRelease>", lambda *_: self.refresh_files())
        ctk.CTkCheckBox(
            bar,
            text="Favorites",
            variable=self.fav_only,
            command=self.refresh_files,
            text_color=w.TEXT,
            fg_color=w.ACCENT,
        ).grid(row=0, column=1, padx=(12, 0))

        self.drop = ctk.CTkFrame(
            content,
            fg_color=w.PANEL,
            border_color=w.BORDER,
            border_width=1,
            corner_radius=8,
            height=70,
        )
        self.drop.grid(row=2, column=0, sticky="ew", padx=24, pady=12)
        self.drop.grid_propagate(False)
        msg = "Drop files here to encrypt into the selected folder" if HAS_DND else (
            "Use Add file to encrypt files into the selected folder"
        )
        ctk.CTkLabel(
            self.drop,
            text=msg,
            text_color=w.TEXT_DIM,
            font=w.FONT_BODY,
        ).pack(expand=True)
        if HAS_DND:
            try:
                self.drop.drop_target_register(DND_FILES)
                self.drop.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        self.list_frame = ctk.CTkScrollableFrame(content, fg_color=w.BG)
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 16))

    def refresh(self):
        self.refresh_folders()
        self.refresh_files()

    def refresh_folders(self):
        for child in self.folder_list.winfo_children():
            child.destroy()
        self._folder_buttons.clear()

        user_id = self.app.session.user_id
        self.folder_names = self.app.db.list_file_folders(user_id)
        counts = self.app.db.file_folder_counts(user_id)
        total = sum(counts.values())

        self._folder_item(ALL_FILES, "All files", total)
        for folder in self.folder_names:
            self._folder_item(folder, folder, counts.get(folder, 0))

        self._sync_folder_action_state()

    def refresh_files(self):
        for child in self.list_frame.winfo_children():
            child.destroy()

        user_id = self.app.session.user_id
        folder = None if self.current_folder == ALL_FILES else self.current_folder
        rows = self.app.db.list_files(
            user_id,
            self.search_var.get().strip(),
            folder=folder,
            favorites_only=self.fav_only.get(),
        )

        title = "All encrypted files" if self.current_folder == ALL_FILES else self.current_folder
        self.title_label.configure(text=title)

        if not rows:
            self._empty_state(folder)
            return

        for row in rows:
            self._file_row(row)

    def _folder_item(self, key: str, label: str, count: int):
        active = key == self.current_folder
        text = f"  {label}   {count}"
        button = ctk.CTkButton(
            self.folder_list,
            text=text,
            anchor="w",
            fg_color=w.PANEL_2 if active else "transparent",
            hover_color=w.PANEL_2,
            text_color=w.ACCENT if active else w.TEXT,
            corner_radius=6,
            height=38,
            font=("Segoe UI", 12),
            command=lambda item=key: self._select_folder(item),
        )
        button.pack(fill="x", padx=4, pady=2)
        self._folder_buttons[key] = button

    def _empty_state(self, folder: str | None):
        target = "this folder" if folder else "the vault"
        box = ctk.CTkFrame(self.list_frame, fg_color=w.PANEL, border_color=w.BORDER, border_width=1, corner_radius=8)
        box.pack(fill="x", padx=4, pady=8)
        ctk.CTkLabel(
            box,
            text=f"No files in {target}.",
            text_color=w.TEXT,
            font=w.FONT_H2,
        ).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            box,
            text="Add files or drag them into the drop zone to encrypt and store them here.",
            text_color=w.TEXT_DIM,
            font=w.FONT_BODY,
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def _file_row(self, row):
        card = ctk.CTkFrame(
            self.list_frame,
            fg_color=w.PANEL,
            corner_radius=8,
            border_color=w.BORDER,
            border_width=1,
        )
        card.pack(fill="x", padx=4, pady=4)
        card.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew", padx=14, pady=10)
        left.columnconfigure(0, weight=1)

        name = row["name"]
        if row["favorite"]:
            name = f"* {name}"
        ctk.CTkLabel(
            left,
            text=name,
            text_color=w.TEXT,
            font=w.FONT_H2,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        folder = row["folder"] or GENERAL
        meta = (
            f"{w.human_size(row['size_bytes'])} | {folder} | "
            f"AES-256-GCM | SHA-256: {row['sha256'][:16]}..."
        )
        ctk.CTkLabel(
            left,
            text=meta,
            text_color=w.TEXT_DIM,
            font=("Consolas", 10),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        if row["tags"]:
            ctk.CTkLabel(
                left,
                text=f"Tags: {row['tags']}",
                text_color=w.ACCENT_2,
                font=("Segoe UI", 10),
                anchor="w",
            ).grid(row=2, column=0, sticky="w", pady=(2, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=10, pady=10)

        move_menu = ctk.CTkOptionMenu(
            right,
            values=self.folder_names or [GENERAL],
            command=lambda choice, fid=row["id"]: self._move_file(fid, choice),
            fg_color=w.PANEL_2,
            button_color=w.BORDER,
            button_hover_color=w.PANEL_2,
            text_color=w.TEXT,
            dropdown_fg_color=w.PANEL,
            dropdown_hover_color=w.PANEL_2,
            dropdown_text_color=w.TEXT,
            width=126,
            height=32,
            font=("Segoe UI", 11),
        )
        move_menu.set(folder)
        move_menu.pack(side="left", padx=2)

        w.ghost_button(
            right,
            "Fav",
            width=58,
            command=lambda fid=row["id"]: self._toggle_fav(fid),
        ).pack(side="left", padx=2)
        w.ghost_button(
            right,
            "Verify",
            width=68,
            command=lambda fid=row["id"]: self._verify(fid),
        ).pack(side="left", padx=2)
        w.ghost_button(
            right,
            "Export",
            width=68,
            command=lambda fid=row["id"]: self._export(fid),
        ).pack(side="left", padx=2)
        w.neon_button(
            right,
            "Delete",
            danger=True,
            width=68,
            command=lambda fid=row["id"]: self._delete(fid),
        ).pack(side="left", padx=2)

    def _select_folder(self, folder: str):
        self.current_folder = folder
        self.refresh()

    def _sync_folder_action_state(self):
        protected = self.current_folder in (ALL_FILES, GENERAL)
        state = "disabled" if protected else "normal"
        self.rename_btn.configure(state=state)
        self.delete_folder_btn.configure(state=state)

    def _new_folder(self):
        name = simpledialog.askstring("New folder", "Folder name:", parent=self)
        name = (name or "").strip()
        if not name:
            return
        try:
            self.app.db.ensure_folder(self.app.session.user_id, name)
            self.app.db.log(self.app.session.user_id, "folder_create", name)
            self.current_folder = name
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Folder", str(exc))

    def _rename_folder(self):
        if self.current_folder in (ALL_FILES, GENERAL):
            return
        new_name = simpledialog.askstring(
            "Rename folder",
            "New folder name:",
            initialvalue=self.current_folder,
            parent=self,
        )
        new_name = (new_name or "").strip()
        if not new_name:
            return
        old_name = self.current_folder
        try:
            self.current_folder = self.app.db.rename_file_folder(
                self.app.session.user_id,
                old_name,
                new_name,
            )
            self.app.db.log(self.app.session.user_id, "folder_rename", f"{old_name} -> {self.current_folder}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Folder", str(exc))

    def _delete_folder(self):
        if self.current_folder in (ALL_FILES, GENERAL):
            return
        if not messagebox.askyesno("Delete folder", f"Delete empty folder '{self.current_folder}'?"):
            return
        folder = self.current_folder
        try:
            self.app.db.delete_file_folder(self.app.session.user_id, folder)
            self.app.db.log(self.app.session.user_id, "folder_delete", folder)
            self.current_folder = ALL_FILES
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Folder", str(exc))

    def _current_destination_folder(self) -> str:
        if self.current_folder == ALL_FILES:
            return GENERAL
        return self.current_folder

    def _add_dialog(self):
        if not self.app.verify_sensitive_action("encrypt files"):
            return
        paths = filedialog.askopenfilenames(title="Add files to vault")
        if not paths:
            return
        for path in paths:
            self._add(path)
        self.refresh()

    def _on_drop(self, event):
        if not self.app.verify_sensitive_action("encrypt files"):
            return
        paths = self._parse_drop(event.data)
        for path in paths:
            self._add(path)
        self.refresh()

    def _parse_drop(self, data: str) -> list[str]:
        out, buf, in_brace = [], "", False
        for ch in data:
            if ch == "{":
                in_brace = True
                continue
            if ch == "}":
                in_brace = False
                out.append(buf)
                buf = ""
                continue
            if ch == " " and not in_brace:
                if buf:
                    out.append(buf)
                    buf = ""
                continue
            buf += ch
        if buf:
            out.append(buf)
        return [path for path in out if os.path.isfile(path)]

    def _add(self, path: str):
        try:
            self.app.vault.add_file(path, folder=self._current_destination_folder())
        except Exception as exc:
            messagebox.showerror("AegisVault", f"Failed to add {path}\n{exc}")

    def _move_file(self, fid: int, folder: str):
        try:
            self.app.db.move_file_to_folder(fid, self.app.session.user_id, folder)
            self.app.db.log(self.app.session.user_id, "file_move", f"id={fid} -> {folder}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Move file", str(exc))

    def _toggle_fav(self, fid: int):
        self.app.db.toggle_favorite_file(fid)
        self.refresh_files()

    def _verify(self, fid: int):
        try:
            ok = self.app.vault.verify_file(fid)
            messagebox.showinfo("Integrity", "File integrity OK" if ok else "Integrity mismatch")
        except Exception as exc:
            messagebox.showerror("Integrity", str(exc))

    def _export(self, fid: int):
        if not self.app.verify_sensitive_action("decrypt and export this file"):
            return
        row = self.app.db.get_file(fid)
        if not row:
            return
        dest = filedialog.asksaveasfilename(initialfile=row["name"])
        if not dest:
            return
        try:
            self.app.vault.export_file(fid, dest)
            messagebox.showinfo("AegisVault", "Decrypted file written.")
        except Exception as exc:
            messagebox.showerror("Export", str(exc))

    def _delete(self, fid: int):
        if not self.app.verify_sensitive_action("delete this vaulted file"):
            return
        if not messagebox.askyesno("Securely delete", "Securely wipe this file from the vault?"):
            return
        self.app.vault.delete_file(fid)
        self.refresh()

    def _export_vault(self):
        if not self.app.verify_sensitive_action("export an encrypted vault backup"):
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile="aegisvault_backup.zip",
        )
        if not dest:
            return
        try:
            self.app.vault.export_vault(dest)
            messagebox.showinfo("Backup", "Encrypted backup created.")
        except Exception as exc:
            messagebox.showerror("Backup", str(exc))
