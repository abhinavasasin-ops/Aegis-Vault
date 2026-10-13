"""Encrypted notes view."""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from . import widgets as w


class NotesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=w.BG)
        self.app = app
        self.search_var = tk.StringVar()
        self.current_id: int | None = None
        self._build()
        self.refresh()

    def _build(self):
        # Left list
        left = ctk.CTkFrame(self, fg_color=w.PANEL, width=260, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Notes", text_color=w.TEXT,
                     font=w.FONT_H2).pack(anchor="w", padx=14, pady=(16, 8))
        e = ctk.CTkEntry(left, textvariable=self.search_var, placeholder_text="Search…",
                         fg_color=w.PANEL_2, border_color=w.BORDER, height=32)
        e.pack(fill="x", padx=12)
        e.bind("<KeyRelease>", lambda *_: self.refresh())
        w.neon_button(left, "+ New note", command=self._new_note,
                      width=230).pack(pady=10)
        self.list_box = ctk.CTkScrollableFrame(left, fg_color=w.PANEL)
        self.list_box.pack(fill="both", expand=True, padx=4, pady=(0, 10))

        # Right editor
        right = ctk.CTkFrame(self, fg_color=w.BG)
        right.pack(side="right", fill="both", expand=True)

        head = ctk.CTkFrame(right, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 6))
        self.title_entry = ctk.CTkEntry(head, placeholder_text="Untitled note",
                                        fg_color=w.PANEL_2, border_color=w.BORDER,
                                        text_color=w.TEXT, height=36, font=w.FONT_H2)
        self.title_entry.pack(side="left", fill="x", expand=True)
        w.neon_button(head, "Save", command=self._save, width=90).pack(side="left", padx=6)
        w.ghost_button(head, "Delete", command=self._delete, width=90).pack(side="left")

        meta = ctk.CTkFrame(right, fg_color="transparent")
        meta.pack(fill="x", padx=18)
        self.tags_entry = ctk.CTkEntry(meta, placeholder_text="tags (comma separated)",
                                       fg_color=w.PANEL_2, border_color=w.BORDER, height=30)
        self.tags_entry.pack(side="left", fill="x", expand=True)
        self.folder_entry = ctk.CTkEntry(meta, placeholder_text="folder",
                                         fg_color=w.PANEL_2, border_color=w.BORDER,
                                         height=30, width=140)
        self.folder_entry.pack(side="left", padx=6)

        self.body = ctk.CTkTextbox(right, fg_color=w.PANEL, text_color=w.TEXT,
                                   border_color=w.BORDER, border_width=1,
                                   corner_radius=8, font=w.FONT_MONO)
        self.body.pack(fill="both", expand=True, padx=18, pady=12)

    def refresh(self):
        for c in self.list_box.winfo_children():
            c.destroy()
        rows = self.app.db.list_notes(self.app.session.user_id, self.search_var.get())
        if not rows:
            ctk.CTkLabel(self.list_box, text="No notes yet.",
                         text_color=w.TEXT_DIM).pack(pady=10)
        for r in rows:
            self._note_item(r)

    def _note_item(self, r):
        b = ctk.CTkButton(
            self.list_box, text=f"  {r['title']}\n  {r['updated_at'][:10]}",
            anchor="w", justify="left",
            fg_color=w.PANEL_2 if r["id"] == self.current_id else "transparent",
            hover_color=w.PANEL_2, text_color=w.TEXT,
            corner_radius=6, height=46, font=("Segoe UI", 11),
            command=lambda i=r["id"]: self._load(i),
        )
        b.pack(fill="x", padx=4, pady=2)

    def _new_note(self):
        self.current_id = None
        self.title_entry.delete(0, "end")
        self.tags_entry.delete(0, "end")
        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, "General")
        self.body.delete("1.0", "end")
        self.title_entry.focus_set()

    def _load(self, nid: int):
        try:
            text = self.app.vault.open_note(nid) or ""
        except Exception as e:
            messagebox.showerror("Notes", f"Failed to decrypt: {e}")
            return
        row = self.app.db.get_note(nid)
        self.current_id = nid
        self.title_entry.delete(0, "end"); self.title_entry.insert(0, row["title"])
        self.tags_entry.delete(0, "end"); self.tags_entry.insert(0, row["tags"] or "")
        self.folder_entry.delete(0, "end"); self.folder_entry.insert(0, row["folder"] or "General")
        self.body.delete("1.0", "end"); self.body.insert("1.0", text)
        self.refresh()

    def _save(self):
        title = self.title_entry.get().strip() or "Untitled"
        body = self.body.get("1.0", "end").rstrip("\n")
        try:
            nid = self.app.vault.save_note(
                title, body,
                folder=self.folder_entry.get().strip() or "General",
                tags=self.tags_entry.get().strip(),
                note_id=self.current_id,
            )
            self.current_id = nid
            self.refresh()
        except Exception as e:
            messagebox.showerror("Notes", f"Save failed: {e}")

    def _delete(self):
        if self.current_id is None: return
        if not messagebox.askyesno("Delete note", "Delete this note?"): return
        self.app.vault.delete_note(self.current_id)
        self._new_note(); self.refresh()
