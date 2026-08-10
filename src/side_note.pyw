from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
import json
import marshal
import math
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


def _resource_path(filename: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / filename


def _clean_title(value: object) -> str:
    return " ".join(str(value).split())


def _hide_rule_widgets(widgets) -> None:
    for widget in widgets:
        widget.place_forget()


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

    def default_state() -> dict:
        state = original_default_state()
        state["settings"][_SHOW_NOTE_LINES] = True
        return state

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
                else self.model.get("title", "新便签")
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
    module.NoteWindow.flush = flush
    module.NoteWindow._title_focus_out = title_focus_out
    module.NoteWindow._redraw_rules = redraw_rules
    module.SideNoteApp._set_note_lines = set_note_lines
    module.SideNoteApp._build_settings_ui = build_settings_ui


def main() -> None:
    module = _load_original_module()
    _apply_patches(module)
    module.run()


if __name__ == "__main__":
    main()
