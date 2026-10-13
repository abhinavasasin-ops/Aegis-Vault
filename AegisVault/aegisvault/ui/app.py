"""Root application: bootstraps DB, routes lock <-> dashboard, auto-lock timer."""
from __future__ import annotations
import time
from tkinter import messagebox
import customtkinter as ctk

from . import widgets as w
from .lock_screen import LockScreen
from .sidebar import Sidebar
from .dashboard import DashboardView
from .files_view import FilesView
from .notes_view import NotesView
from .settings_view import SettingsView

from ..core.database import Database
from ..core.auth import AuthManager, Session
from ..core import platform_auth
from ..core.vault import Vault
from ..config import AUTOLOCK_SECONDS

try:
    from tkinterdnd2 import TkinterDnD
    BASE = TkinterDnD.Tk
except Exception:
    BASE = None


class _RootMixinTk(ctk.CTk):
    pass


def _make_root():
    """Use TkinterDnD root if available, otherwise plain CTk."""
    if BASE is None:
        return ctk.CTk()

    class _Root(BASE):  # type: ignore[misc]
        pass
    root = _Root()
    # CTk styling helpers
    ctk.set_appearance_mode("dark")
    return root


class AegisApp(ctk.CTk):
    def __init__(self):
        w.apply_theme()
        super().__init__()
        self.title("AegisVault")
        self.geometry("1180x720")
        self.minsize(960, 620)
        self.configure(fg_color=w.BG)

        # Try to enable DnD on the underlying Tk root
        try:
            from tkinterdnd2 import TkinterDnD
            self.tk.eval("package require tkdnd")
            self.TkdndVersion = self.tk.eval("package present tkdnd")
        except Exception:
            pass

        self.db = Database()
        self.auth = AuthManager(self.db)
        self.session: Session | None = None
        self.vault: Vault | None = None
        self.autolock_seconds = AUTOLOCK_SECONDS
        self.require_biometric = False
        self._last_activity = time.time()

        self._current_view: ctk.CTkFrame | None = None
        self._views: dict[str, ctk.CTkFrame] = {}
        self.sidebar: Sidebar | None = None
        self.main_area: ctk.CTkFrame | None = None

        self._show_lock()

        # global activity tracking
        for ev in ("<Motion>", "<Key>", "<Button>"):
            self.bind_all(ev, self._mark_activity, add="+")
        self.after(5000, self._autolock_tick)

    # ---- routing
    def _clear(self):
        for child in self.winfo_children():
            child.destroy()
        self.sidebar = None
        self.main_area = None
        self._views.clear()
        self._current_view = None

    def _show_lock(self):
        self._clear()
        self.session = None
        self.vault = None
        LockScreen(self, self).pack(fill="both", expand=True)

    def on_authenticated(self, session: Session):
        self.session = session
        self.vault = Vault(self.db, session.key, session.user_id)
        self.require_biometric = self.db.get_user_setting(session.user_id, "require_biometric", "0") == "1"
        if self.require_biometric and not self.verify_sensitive_action("open the vault"):
            self.lock()
            return
        self._mark_activity()
        self._build_main()

    def _build_main(self):
        self._clear()
        self.sidebar = Sidebar(self, on_nav=self._nav, on_lock=self.lock)
        self.sidebar.pack(side="left", fill="y")
        self.main_area = ctk.CTkFrame(self, fg_color=w.BG)
        self.main_area.pack(side="right", fill="both", expand=True)
        self._views = {
            "dashboard": DashboardView(self.main_area, self),
            "files":     FilesView(self.main_area, self),
            "notes":     NotesView(self.main_area, self),
            "settings":  SettingsView(self.main_area, self),
        }
        self._nav("dashboard")

    def _nav(self, key: str):
        if self._current_view:
            self._current_view.pack_forget()
        view = self._views[key]
        view.pack(fill="both", expand=True)
        if hasattr(view, "refresh"):
            try: view.refresh()
            except Exception: pass
        self._current_view = view
        if self.sidebar:
            self.sidebar.set_active(key)

    def lock(self):
        if self.session:
            self.db.log(self.session.user_id, "lock", "manual/auto")
        self._show_lock()

    # ---- auto-lock
    def _mark_activity(self, _evt=None):
        self._last_activity = time.time()

    def set_autolock(self, seconds: int):
        self.autolock_seconds = max(30, int(seconds))

    def _autolock_tick(self):
        if self.session and (time.time() - self._last_activity) > self.autolock_seconds:
            self.lock()
        self.after(5000, self._autolock_tick)

    # ---- Windows Hello / fingerprint gate
    def biometric_status(self) -> platform_auth.PlatformAuthStatus:
        return platform_auth.check_availability()

    def set_biometric_required(self, enabled: bool) -> bool:
        if enabled:
            status = platform_auth.check_availability()
            if not status.available:
                messagebox.showerror("Windows Hello", status.message)
                return False
            verified = platform_auth.verify_user("Enable Windows Hello protection for AegisVault.")
            if not verified.available:
                messagebox.showerror("Windows Hello", verified.message)
                return False
            self.require_biometric = True
            if self.session:
                self.db.set_user_setting(self.session.user_id, "require_biometric", "1")
                self.db.log(self.session.user_id, "windows_hello_enable", "sensitive actions")
            return True

        if self.require_biometric and not self.verify_sensitive_action("disable Windows Hello protection"):
            return False
        self.require_biometric = False
        if self.session:
            self.db.set_user_setting(self.session.user_id, "require_biometric", "0")
            self.db.log(self.session.user_id, "windows_hello_disable", "sensitive actions")
        return True

    def verify_sensitive_action(self, action: str) -> bool:
        if not self.require_biometric:
            return True
        result = platform_auth.verify_user(f"AegisVault needs your approval to {action}.")
        if result.available:
            if self.session:
                self.db.log(self.session.user_id, "windows_hello_verified", action)
            return True
        if self.session:
            self.db.log(self.session.user_id, "windows_hello_failed", action)
        messagebox.showerror("Windows Hello", result.message)
        return False
