import ctypes
from importlib.machinery import SourceFileLoader
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch as mock_patch


ROOT = Path(__file__).resolve().parents[1]
patch = SourceFileLoader(
    "side_note_patch", str(ROOT / "src" / "side_note.pyw")
).load_module()


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class SideNotePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = patch._load_original_module()
        patch._apply_patches(cls.app)

    def create_note_window(self, root, text=""):
        side_note_app = SimpleNamespace(
            root=root,
            state={"settings": {"note_font_size": 14, "show_note_lines": True}},
            collapse_note=lambda *_args: None,
            delete_note=lambda *_args: None,
            open_settings=lambda *_args, **_kwargs: None,
        )
        model = {
            "id": "test-note",
            "title": "",
            "text": text,
            "docked": False,
            "x": 10,
            "y": 10,
            "width": 360,
            "height": 300,
            "dock_side": "right",
            "dock_slot": 0,
            "collapsed_free": False,
            "tab_x": 10,
            "tab_y": 10,
            "tab_edge": None,
        }
        return self.app.NoteWindow(side_note_app, model)

    def test_empty_title_stays_empty_in_state_and_display(self):
        raw = self.app.default_state()
        raw["notes"].append(
            {
                "id": "note-1",
                "title": "",
                "text": "正文",
                "docked": False,
                "x": 10,
                "y": 10,
                "width": 360,
                "height": 300,
            }
        )

        normalized = self.app.normalize_state(raw)

        self.assertEqual(normalized["notes"][0]["title"], "")
        self.assertEqual(self.app.note_display_title(normalized["notes"][0]), "")

    def test_flush_does_not_restore_default_title(self):
        note = SimpleNamespace(
            title_var=Value(""),
            model={"title": "旧标题", "docked": True},
            text=SimpleNamespace(get=lambda *_args: "正文"),
            window=SimpleNamespace(),
        )

        self.app.NoteWindow.flush(note)

        self.assertEqual(note.model["title"], "")
        self.assertEqual(note.title_var.get(), "")

        note.title_var.set("我的名字")
        self.app.NoteWindow.flush(note)

        self.assertEqual(note.model["title"], "我的名字")

    def test_new_note_starts_with_empty_title(self):
        class NoteView:
            def __init__(self, _app, model):
                self.model = model
                self.title_var = Value("新便签")

            def show(self):
                pass

        saved = []
        side_note_app = SimpleNamespace(
            state={"notes": []},
            areas=[],
            note_views={},
            _show_all_notes=lambda: None,
            save_state=lambda: saved.append(True),
        )

        with (
            mock_patch.object(
                self.app,
                "clamp_bounds",
                side_effect=lambda x, y, _width, _height, _areas: (x, y),
            ),
            mock_patch.object(self.app, "NoteWindow", NoteView),
        ):
            self.app.SideNoteApp.create_note(side_note_app, 10, 20)
            self.app.SideNoteApp.create_note(
                side_note_app, 30, 40, title="新草稿"
            )

        self.assertEqual(
            [note["title"] for note in side_note_app.state["notes"]], ["", ""]
        )
        self.assertEqual(
            [view.model["title"] for view in side_note_app.note_views.values()],
            ["", ""],
        )
        self.assertEqual(
            [view.title_var.get() for view in side_note_app.note_views.values()],
            ["", ""],
        )
        self.assertEqual(saved, [True, True])

    def test_batch_commit_fills_current_line_and_enter_adds_one_newline(self):
        root = self.app.tk.Tk()
        root.withdraw()
        note = None
        prefix = "prefix "
        committed = "zheshiyicichangduanwenbenshurufayicixingtijiao"

        try:
            note = self.create_note_window(root)
            note.window.geometry("360x300+0+0")
            note.window.attributes("-alpha", 0.0)
            note.window.deiconify()
            root.update()
            self.assertEqual(note.text.cget("wrap"), "char")

            def first_display_line(mode):
                note.text.configure(wrap=mode)
                note.text.delete("1.0", "end")
                note.text.insert("end", prefix)
                note.text.insert("end", committed)
                root.update()
                return note.text.get("1.0", "1.0 display lineend")

            word_line = first_display_line("word")
            char_line = first_display_line("char")

            self.assertEqual(word_line, prefix.rstrip())
            self.assertGreater(len(char_line), len(prefix))
            self.assertEqual(note.model["text"], prefix + committed)
            self.assertNotIn("\n", note.model["text"])

            note.app.state["settings"]["note_font_size"] = 16
            note.apply_theme()
            self.assertEqual(note.text.cget("wrap"), "char")

            note.text.mark_set("insert", "end-1c")
            note.text.focus_force()
            root.update()
            note.text.event_generate("<Return>")
            root.update()

            self.assertEqual(note.text.get("1.0", "end-1c"), prefix + committed + "\n")
            self.assertEqual(note.model["text"], prefix + committed + "\n")
        finally:
            if note:
                note.destroy()
            root.destroy()

    def test_line_setting_is_persisted_and_redraws_notes(self):
        scheduled = []
        saved = []
        side_note_app = SimpleNamespace(
            state={"settings": {"show_note_lines": True}},
            save_state=lambda: saved.append(True),
            note_views={
                "one": SimpleNamespace(_schedule_rules=lambda: scheduled.append("one")),
                "two": SimpleNamespace(_schedule_rules=lambda: scheduled.append("two")),
            },
        )

        self.app.SideNoteApp._set_note_lines(side_note_app, False)

        self.assertFalse(side_note_app.state["settings"]["show_note_lines"])
        self.assertEqual(saved, [True])
        self.assertEqual(scheduled, ["one", "two"])

    def test_disabled_lines_hide_rules_but_keep_paper_texture(self):
        hidden = []
        note = SimpleNamespace(
            rule_lines=[SimpleNamespace(place_forget=lambda: hidden.append("rule"))],
            paper_fibres=[
                SimpleNamespace(place_forget=lambda: hidden.append("fibre"))
            ],
        )

        patch._hide_rule_widgets(note.rule_lines)

        self.assertEqual(hidden, ["rule"])

    def test_window_icon_is_applied_and_retained(self):
        applied = []
        icon = object()
        root = SimpleNamespace(
            iconphoto=lambda default, image: applied.append((default, image))
        )

        with mock_patch.object(patch.tk, "PhotoImage", return_value=icon):
            patch._set_window_icon(root)

        self.assertEqual(applied, [(True, icon)])
        self.assertIs(root._sidenote_icon, icon)

    def test_free_note_and_docked_tab_are_topmost_toolwindows(self):
        state = self.app.default_state()
        state["settings"]["start_with_windows"] = False
        state["notes"] = [
            {
                "id": "docked-note",
                "title": "",
                "text": "",
                "docked": True,
                "x": 100,
                "y": 100,
                "width": 360,
                "height": 300,
                "dock_side": "right",
                "dock_slot": 0,
                "collapsed_free": False,
                "tab_x": 100,
                "tab_y": 100,
                "tab_edge": "right",
            }
        ]
        store = SimpleNamespace(
            load=lambda: state,
            save=lambda _state: None,
            recovered_from=None,
            can_save=True,
        )
        root = self.app.tk.Tk()
        root.withdraw()
        app = None
        note = None

        try:
            app = self.app.SideNoteApp(root, store)
            note = self.create_note_window(root)
            note.window.deiconify()
            root.update()

            windows = [note.window, app.tabs["docked-note"]["win"]]
            get_style = ctypes.windll.user32.GetWindowLongW
            for window in windows:
                with self.subTest(window=window):
                    child = window.winfo_id()
                    hwnd = ctypes.windll.user32.GetParent(child) or child
                    style = get_style(hwnd, -20) & 0xFFFFFFFF
                    self.assertEqual(window.attributes("-toolwindow"), 1)
                    self.assertEqual(window.attributes("-topmost"), 1)
                    self.assertTrue(style & 0x00000080)
                    self.assertTrue(style & 0x00000008)
                    self.assertFalse(style & 0x00040000)
        finally:
            if note:
                note.destroy()
            if app:
                app.exit_app()
            else:
                root.destroy()

    def test_entry_visual_changes_without_replacing_original_bindings(self):
        class Canvas:
            def __init__(self):
                self.bindings = {}
                self.images = []
                self.config = {}

            def pack(self, **_kwargs):
                pass

            def bind(self, event, handler):
                self.bindings[event] = handler

            def delete(self, _tag):
                pass

            def create_image(self, *position, **options):
                self.images.append((position, options))

            def configure(self, **options):
                self.config.update(options)

        class PhotoImage:
            next_id = 0

            def __init__(self, **options):
                type(self).next_id += 1
                self.name = f"photo-{self.next_id}"
                self.options = options
                self.calls = []
                self.tk = SimpleNamespace(call=lambda *args: self.calls.append(args))

            def __str__(self):
                return self.name

        canvas = Canvas()
        toggled = []
        side_note_app = SimpleNamespace(
            root=object(),
            entry_width=40,
            entry_height=50,
            state={"settings": {"entry_edge": "right"}},
            _entry_drag_start=object(),
            _entry_drag_move=object(),
            _entry_drag_end=object(),
            _create_note_from_pointer=object(),
            _animate_entry_background=lambda _color: None,
            toggle_panel=lambda force: toggled.append(force),
        )
        side_note_app._draw_entry_icon = lambda: self.app.SideNoteApp._draw_entry_icon(
            side_note_app
        )

        with (
            mock_patch.object(self.app.tk, "Canvas", return_value=canvas),
            mock_patch.object(self.app.tk, "PhotoImage", PhotoImage),
            mock_patch.object(self.app, "ACTIVE_THEME", "sun_yellow"),
        ):
            self.app.SideNoteApp._build_entry(side_note_app)

        self.assertEqual(canvas.images[0][0], (20, 25))
        self.assertEqual(
            canvas.images[0][1]["tags"], ("entry-mark", "sidenote-mark")
        )
        self.assertTrue(
            side_note_app._entry_icon_sheet.options["file"].endswith(
                "sun_yellow-strip.png"
            )
        )
        self.assertEqual(
            side_note_app._entry_icon_image.options, {"width": 40, "height": 40}
        )
        self.assertIs(
            canvas.bindings["<ButtonPress-1>"], side_note_app._entry_drag_start
        )
        self.assertIs(
            canvas.bindings["<ButtonRelease-1>"], side_note_app._entry_drag_end
        )
        self.assertIs(
            canvas.bindings["<B1-Motion>"], side_note_app._entry_drag_move
        )
        self.assertIs(
            canvas.bindings["<Button-3>"], side_note_app._create_note_from_pointer
        )
        self.assertEqual(
            set(canvas.bindings),
            {
                "<ButtonPress-1>",
                "<B1-Motion>",
                "<ButtonRelease-1>",
                "<Button-3>",
                "<Return>",
                "<space>",
                "<Enter>",
                "<Leave>",
            },
        )
        canvas.bindings["<Return>"](None)
        canvas.bindings["<space>"](None)
        self.assertEqual(toggled, [False, False])

    def test_entry_transparency_removes_square_background(self):
        calls = []
        root_config = {}
        canvas_config = {}
        app = SimpleNamespace(
            root=SimpleNamespace(
                attributes=lambda *args: calls.append(args),
                configure=lambda **options: root_config.update(options),
            ),
            entry_canvas=SimpleNamespace(
                configure=lambda **options: canvas_config.update(options)
            ),
        )

        patch._apply_entry_transparency(app)

        self.assertEqual(calls, [("-transparentcolor", "#010203")])
        self.assertEqual(root_config["bg"], "#010203")
        self.assertEqual(canvas_config["bg"], "#010203")
        self.assertEqual(app._entry_background, "#010203")

    def test_all_seven_theme_sprite_strips_cover_every_scale_slot(self):
        expected_size = (72 * 21, 72)
        for theme in self.app.THEMES:
            asset = (
                ROOT
                / "assets"
                / "floating-entry-themes"
                / f"{theme}-strip.png"
            )
            with self.subTest(theme=theme):
                data = asset.read_bytes()[:24]
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", data[16:24]), expected_size)

    def test_open_panel_keeps_every_visible_note_surface_above_it(self):
        lifted = []
        made_topmost = []

        class Window:
            def __init__(self, name, visible=True):
                self.name = name
                self.visible = visible

            def geometry(self, _value):
                pass

            def attributes(self, *_args):
                if _args == ("-topmost", True):
                    made_topmost.append(self.name)

            def deiconify(self):
                pass

            def lift(self):
                lifted.append(self.name)

            def winfo_viewable(self):
                return self.visible

        app = SimpleNamespace(
            panel_visible=False,
            panel=Window("panel"),
            _place_panel=lambda: (100, 200),
            _panel_motion=None,
            panel_width=320,
            panel_height=448,
            motion=False,
            task_entry=SimpleNamespace(focus_force=lambda: None),
            note_views={
                "visible": SimpleNamespace(window=Window("free-note")),
                "hidden": SimpleNamespace(window=Window("hidden-note", False)),
            },
            tabs={"docked": {"win": Window("docked-note")}},
        )

        with (
            mock_patch.object(self.app, "cancel_animation"),
            mock_patch.object(self.app, "round_window"),
            mock_patch.object(self.app, "apply_window_material"),
        ):
            self.app.SideNoteApp.show_panel(app, animated=False)

        self.assertEqual(lifted, ["panel", "free-note", "docked-note"])
        self.assertEqual(made_topmost, ["free-note", "docked-note"])

    def test_line_setting_defaults_on_and_survives_normalization(self):
        raw = self.app.default_state()
        self.assertTrue(raw["settings"]["show_note_lines"])

        raw["settings"]["show_note_lines"] = False
        normalized = self.app.normalize_state(raw)
        self.assertFalse(normalized["settings"]["show_note_lines"])


if __name__ == "__main__":
    unittest.main()
