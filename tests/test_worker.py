"""T7: worker prompt v2 — event type + one German phrase, no network."""

import unittest

from worker.main import EVENT_TYPES, MAX_SUMMARY, PROMPT, to_finding


class WorkerAnswerTest(unittest.TestCase):
    def test_good_answer(self):
        self.assertEqual(to_finding({"event_type": "Konzert", "summary": " Deutschpunk "}), ("Konzert", "Deutschpunk"))

    def test_unknown_type_becomes_sonstiges(self):
        self.assertEqual(to_finding({"event_type": "Lesung", "summary": "Science Slam"})[0], "Sonstiges")

    def test_empty_summary_is_an_error(self):
        with self.assertRaises(ValueError):
            to_finding({"event_type": "Party", "summary": ""})

    def test_long_summary_is_cut(self):
        _, summary = to_finding({"event_type": "Party", "summary": "x" * 200})
        self.assertLessEqual(len(summary), MAX_SUMMARY)

    def test_prompt_asks_for_german_and_types(self):
        text = PROMPT.format(venue="Molotow", title="FAT DOG", text="", types=", ".join(EVENT_TYPES))
        self.assertIn("auf Deutsch", text)
        for t in EVENT_TYPES:
            self.assertIn(t, text)
        self.assertNotIn("about_ai", text)


if __name__ == "__main__":
    unittest.main()
