from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
import unittest


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

    def test_line_setting_defaults_on_and_survives_normalization(self):
        raw = self.app.default_state()
        self.assertTrue(raw["settings"]["show_note_lines"])

        raw["settings"]["show_note_lines"] = False
        normalized = self.app.normalize_state(raw)
        self.assertFalse(normalized["settings"]["show_note_lines"])


if __name__ == "__main__":
    unittest.main()
