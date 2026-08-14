from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
import json
import marshal
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
import types
import uuid
import winreg


_ORIGINAL_MODULE = "_side_note_original"
_ORIGINAL_CODE = "original_side_note.marshal"
_SHOW_NOTE_LINES = "show_note_lines"
_APP_ICON = "assets/sidenote-icon.png"
_ENTRY_ICON_DIR = "assets/floating-entry-themes"
_ENTRY_ICON_SIZES = tuple(range(32, 73, 2))
_ENTRY_ICON_CELL = 72
_ENTRY_TRANSPARENT = "#010203"


def _resource_path(filename: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / filename


def _clean_title(value: object) -> str:
    return " ".join(str(value).split())


def _hide_rule_widgets(widgets) -> None:
    for widget in widgets:
        widget.place_forget()


def _set_window_icon(root) -> None:
    try:
        icon = tk.PhotoImage(file=str(_resource_path(_APP_ICON)))
        root.iconphoto(True, icon)
        root._sidenote_icon = icon
    except (tk.TclError, OSError):
        pass


def _apply_entry_transparency(app) -> None:
    try:
        app.root.attributes("-transparentcolor", _ENTRY_TRANSPARENT)
        app.root.configure(bg=_ENTRY_TRANSPARENT)
        app.entry_canvas.configure(bg=_ENTRY_TRANSPARENT)
        app._entry_background = _ENTRY_TRANSPARENT
    except (AttributeError, tk.TclError):
        pass

    if os.name != "nt":
        return
    try:
        app.root.update_idletasks()
        child = app.root.winfo_id()
        hwnd = ctypes.windll.user32.GetParent(child) or child
        disabled = ctypes.c_int(1)
        no_border = ctypes.c_uint32(0xFFFFFFFE)
        for attribute, value in ((2, disabled), (33, disabled), (34, no_border)):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
    except (AttributeError, OSError, ctypes.ArgumentError, tk.TclError):
        pass


def _load_original_module() -> types.ModuleType:
    code = marshal.loads(_resource_path(_ORIGINAL_CODE).read_bytes())
    module = types.ModuleType(_ORIGINAL_MODULE)
    module.__file__ = "侧笺.pyw"
    sys.modules[_ORIGINAL_MODULE] = module
    exec(code, module.__dict__)
    return module


def _apply_patches(module: types.ModuleType) -> None:
    original_default_state = module.default_state
    original_normalize_state = module.normalize_state
    original_redraw_rules = module.NoteWindow._redraw_rules
    original_build_settings_ui = module.SideNoteApp._build_settings_ui
    original_app_init = module.SideNoteApp.__init__
    original_apply_theme = module.SideNoteApp._apply_theme
    original_draw_entry_icon = module.SideNoteApp._draw_entry_icon
    original_show_panel = module.SideNoteApp.show_panel

    def default_state() -> dict:
        state = original_default_state()
        state["settings"][_SHOW_NOTE_LINES] = True
        return state

    def app_init(self, root, store) -> None:
        _set_window_icon(root)
        original_app_init(self, root, store)
        _apply_entry_transparency(self)

    def normalize_state(raw: object) -> dict:
        state = original_normalize_state(raw)
        raw_settings = raw.get("settings") if isinstance(raw, dict) else None
        state["settings"][_SHOW_NOTE_LINES] = bool(
            raw_settings.get(_SHOW_NOTE_LINES, True)
            if isinstance(raw_settings, dict)
            else True
        )

        raw_notes = raw.get("notes") if isinstance(raw, dict) else None
        if isinstance(raw_notes, list):
            for source, target in zip(raw_notes, state["notes"]):
                if not isinstance(source, dict):
                    continue
                title = source.get("title")
                if isinstance(title, str) and not _clean_title(title):
                    target["title"] = ""
        return state

    def note_display_title(model: dict, limit: int = 16) -> str:
        title = _clean_title(model.get("title", ""))
        return title if len(title) <= limit else f"{title[: limit - 1]}…"

    def flush(self) -> None:
        try:
            title_value = (
                self.title_var.get()
                if hasattr(self, "title_var")
                else self.model.get("title", "")
            )
            title = _clean_title(title_value)
            self.model["title"] = title
            if hasattr(self, "title_var") and self.title_var.get() != title:
                self.title_var.set(title)
            self.model["text"] = self.text.get("1.0", "end-1c")
            if not self.model["docked"] and self.window.winfo_viewable():
                self.model.update(
                    x=self.window.winfo_x(),
                    y=self.window.winfo_y(),
                    width=self.window.winfo_width(),
                    height=self.window.winfo_height(),
                )
        except module.tk.TclError:
            pass

    def title_focus_out(self, _event=None) -> None:
        title = _clean_title(self.title_var.get())
        if self.title_var.get() != title:
            self.title_var.set(title)

    def draw_entry_icon(self) -> None:
        canvas = self.entry_canvas
        canvas.delete("all")
        width, height = self.entry_width, self.entry_height
        size = min(_ENTRY_ICON_SIZES, key=lambda candidate: abs(candidate - width))
        frame = _ENTRY_ICON_SIZES.index(size)
        asset = _resource_path(
            f"{_ENTRY_ICON_DIR}/{module.ACTIVE_THEME}-strip.png"
        )
        try:
            sheet = module.tk.PhotoImage(file=str(asset))
            icon = module.tk.PhotoImage(width=size, height=size)
            left = frame * _ENTRY_ICON_CELL
            icon.tk.call(
                str(icon),
                "copy",
                str(sheet),
                "-from",
                left,
                0,
                left + size,
                size,
                "-to",
                0,
                0,
            )
        except (module.tk.TclError, OSError):
            original_draw_entry_icon(self)
            return

        canvas.create_image(
            width / 2,
            height / 2,
            image=icon,
            tags=("entry-mark", "sidenote-mark"),
        )
        self._entry_icon_sheet = sheet
        self._entry_icon_image = icon

    def animate_entry_background(self, target: str) -> None:
        module.cancel_animation(self.root, self._entry_hover_motion)
        self._entry_hover_motion = None
        self._entry_background = _ENTRY_TRANSPARENT
        try:
            self.entry_canvas.configure(bg=_ENTRY_TRANSPARENT)
            alpha = module.floating_surface_alpha()
            if target == module.HOVER:
                alpha = min(1.0, alpha + 0.08)
            self.root.attributes("-alpha", alpha)
        except module.tk.TclError:
            pass

    def apply_theme(self) -> None:
        original_apply_theme(self)
        _apply_entry_transparency(self)

    def show_panel(self, animated: bool = True) -> None:
        original_show_panel(self, animated)
        windows = [view.window for view in self.note_views.values()]
        windows.extend(tab.get("win") for tab in self.tabs.values())
        for window in windows:
            try:
                if window and window.winfo_viewable():
                    window.attributes("-topmost", True)
                    window.lift()
            except module.tk.TclError:
                pass

    def create_note(
        self, x: int | None = None, y: int | None = None, title: str = ""
    ) -> None:
        self._show_all_notes()
        if x is None or y is None:
            area = (
                module.work_area_for_bounds(
                    self.entry_x,
                    self.entry_y,
                    self.entry_width,
                    self.entry_height,
                    self.areas,
                )
                or self.primary
            )
            if self.entry_x + self.entry_width / 2 >= (area.left + area.right) / 2:
                x = self.entry_x - module.NOTE_WIDTH - 12
            else:
                x = self.entry_x + self.entry_width + 12
            y = (
                self.entry_y
                + self.entry_height
                + 12
                + len(self.state["notes"]) % 6 * 22
            )
        x, y = module.clamp_bounds(
            x, y, module.NOTE_WIDTH, module.NOTE_HEIGHT, self.areas
        )

        title = _clean_title(title)
        if title in {"新便签", "新草稿"}:
            title = ""
        model = {
            "id": uuid.uuid4().hex,
            "title": title,
            "text": "",
            "docked": False,
            "x": x,
            "y": y,
            "width": module.NOTE_WIDTH,
            "height": module.NOTE_HEIGHT,
            "dock_side": "right",
            "dock_slot": 0,
            "collapsed_free": False,
            "tab_x": x,
            "tab_y": y,
            "tab_edge": None,
        }
        self.state["notes"].append(model)
        view = module.NoteWindow(self, model)
        if hasattr(view, "title_var"):
            view.title_var.set(title)
        self.note_views[model["id"]] = view
        self.save_state()
        view.show()

    def redraw_rules(self) -> None:
        settings = self.app.state.get("settings", {})
        original_redraw_rules(self)
        if not settings.get(_SHOW_NOTE_LINES, True):
            try:
                _hide_rule_widgets(self.rule_lines)
            except module.tk.TclError:
                pass

    def set_note_lines(self, enabled: bool) -> None:
        self.state["settings"][_SHOW_NOTE_LINES] = bool(enabled)
        self.save_state()
        for view in self.note_views.values():
            try:
                view._schedule_rules()
            except module.tk.TclError:
                pass

    def build_settings_ui(self, scroll_position: float = 0.0) -> None:
        original_build_settings_ui(self, scroll_position)

        host = module.tk.Frame(self.settings_content, bg=module.SURFACE)
        host.pack(fill="x", padx=10, pady=(0, 18))
        module.tk.Label(
            host,
            text="显示便签横线",
            bg=module.SURFACE,
            fg=module.TEXT,
            font=(module.BODY_FONT, 10),
        ).pack(side="left")
        self.note_lines_switch = module.ToggleSwitch(
            host,
            self.state["settings"].get(_SHOW_NOTE_LINES, True),
            self._set_note_lines,
        )
        self.note_lines_switch.pack(side="right")
        self._bind_settings_wheel(host)
        self.settings_popup.update_idletasks()

    module.default_state = default_state
    module.normalize_state = normalize_state
    module.note_display_title = note_display_title
    module.SideNoteApp.__init__ = app_init
    module.NoteWindow.flush = flush
    module.NoteWindow._title_focus_out = title_focus_out
    module.NoteWindow._redraw_rules = redraw_rules
    module.SideNoteApp._draw_entry_icon = draw_entry_icon
    module.SideNoteApp._animate_entry_background = animate_entry_background
    module.SideNoteApp._apply_theme = apply_theme
    module.SideNoteApp.show_panel = show_panel
    module.SideNoteApp.create_note = create_note
    module.SideNoteApp._set_note_lines = set_note_lines
    module.SideNoteApp._build_settings_ui = build_settings_ui


def main() -> None:
    module = _load_original_module()
    _apply_patches(module)
    module.run()


if __name__ == "__main__":
    main()
