# tests/test_tools24.py
"""
Unit tests for the tools24 game module.

This test module follows PEP8 and PEP257/PEP287-style docstring guidelines.
It targets the following functions from tools24:
 - load_scores
 - save_scores
 - choose_difficulty
 - play_game
 - show_scores

The tests use unittest and unittest.mock to:
 - simulate user input
 - control randomness
 - route file IO to temporary directories
 - capture stdout for checking printed output

Edge cases covered:
 - Non-ASCII characters in player names (Chinese, Arabic)
 - Extremely long player names
 - Malformed and partially malformed score files
 - Floating-point infinity values saved as scores (expecting loader to raise)
 - Unexpected working directory vs. script directory (SCORE_FILE patched)
 - Invalid inputs for choose_difficulty (defaults handled)
"""

import io
import os
import tempfile
import unittest
from unittest import mock

# Import module under test
import tools24


class Tools24Tests(unittest.TestCase):
    """Tests for the tools24 module."""

    def setUp(self):
        """Prepare a temporary directory and patch SCORE_FILE to it."""
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        # Patch SCORE_FILE inside the module
        self.test_score_path = os.path.join(self.tempdir.name, "highscores_test.txt")
        self._original_score_file = getattr(tools24, "SCORE_FILE", None)
        tools24.SCORE_FILE = self.test_score_path

    def tearDown(self):
        """Restore SCORE_FILE after test."""
        if self._original_score_file is not None:
            tools24.SCORE_FILE = self._original_score_file

    def test_save_and_load_scores_non_ascii_and_long_names(self):
        """Saving and loading supports non-ASCII and long names (round-trip)."""
        scores_in = {
            "张伟": 3,
            "علي": 5,
            "a" * 500: 10,
            "NormalName": 2
        }
        tools24.save_scores(scores_in)
        loaded = tools24.load_scores()
        self.assertEqual(len(loaded), len(scores_in))
        for name, score in scores_in.items():
            self.assertIn(name, loaded)
            self.assertEqual(loaded[name], score)

    def test_load_scores_ignores_malformed_lines(self):
        """load_scores should ignore lines with wrong format."""
        lines = [
            "Good|3\n",
            "BadLineWithoutSeparator\n",
            "AlsoBad|NotANumber|Extra\n",
            "AnotherGood|7\n",
            "Empty|\n"
        ]
        with open(self.test_score_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        loaded = tools24.load_scores()
        self.assertIn("Good", loaded)
        self.assertEqual(loaded["Good"], 3)
        self.assertIn("AnotherGood", loaded)
        self.assertEqual(loaded["AnotherGood"], 7)
        self.assertNotIn("BadLineWithoutSeparator", loaded)
        self.assertNotIn("AlsoBad", loaded)
        self.assertNotIn("Empty", loaded)

    def test_save_with_inf_then_load_raises_value_error(self):
        """
        If save_scores writes infinity floats,
        load_scores() should raise ValueError when parsing them.
        """
        scores = {"PositiveInf": float("inf"), "NegativeInf": -float("inf")}
        tools24.save_scores(scores)
        with self.assertRaises(ValueError):
            _ = tools24.load_scores()

    def test_choose_difficulty_valid_and_invalid_inputs(self):
        """Test choose_difficulty with valid and invalid inputs."""
        with mock.patch("builtins.input", side_effect=["1"]):
            self.assertEqual(tools24.choose_difficulty(), 10)
        with mock.patch("builtins.input", side_effect=["2"]):
            self.assertEqual(tools24.choose_difficulty(), 50)
        with mock.patch("builtins.input", side_effect=["3"]):
            self.assertEqual(tools24.choose_difficulty(), 100)
        with mock.patch("builtins.input", side_effect=["4"]):
            self.assertEqual(tools24.choose_difficulty(), 500)
        with mock.patch("builtins.input", side_effect=["garbage"]):
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(tools24.choose_difficulty(), 10)

    def test_play_game_updates_personal_best_and_not_overwrite_worse_score(self):
        """play_game updates score only if new attempt count is better."""
        # Case 1: new personal best
        scores = {"alice": 5}
        with mock.patch.object(tools24, "choose_difficulty", return_value=5):
            with mock.patch("random.randint", return_value=3):
                inputs = ["alice", "1", "3"]
                with mock.patch("builtins.input", side_effect=inputs):
                    with mock.patch("sys.stdout", new_callable=io.StringIO):
                        tools24.play_game(scores)
        self.assertEqual(scores["alice"], 2)

        # Case 2: worse than best
        scores2 = {"bob": 2}
        with mock.patch.object(tools24, "choose_difficulty", return_value=5):
            with mock.patch("random.randint", return_value=4):
                inputs2 = ["bob", "1", "2", "3", "4"]
                with mock.patch("builtins.input", side_effect=inputs2):
                    with mock.patch("sys.stdout", new_callable=io.StringIO):
                        tools24.play_game(scores2)
        self.assertEqual(scores2["bob"], 2)

    def test_show_scores_output_sorted_and_format(self):
        """show_scores should print scores sorted by attempts (ascending)."""
        scores = {"jane": 5, "adam": 2, "zoe": 10}
        fake_out = io.StringIO()
        with mock.patch("sys.stdout", new=fake_out):
            tools24.show_scores(scores)
        output = fake_out.getvalue()
        idx_adam = output.find("adam: 2")
        idx_jane = output.find("jane: 5")
        idx_zoe = output.find("zoe: 10")
        self.assertTrue(idx_adam != -1 and idx_jane != -1 and idx_zoe != -1)
        self.assertLess(idx_adam, idx_jane)
        self.assertLess(idx_jane, idx_zoe)

    def test_game_working_directory_independence(self):
        """Test that SCORE_FILE path works even if cwd changes."""
        old_cwd = os.getcwd()
        try:
            os.chdir(self.tempdir.name)
            scores = {"cwdtester": 1}
            tools24.save_scores(scores)
            self.assertTrue(os.path.exists(tools24.SCORE_FILE))
            loaded = tools24.load_scores()
            self.assertIn("cwdtester", loaded)
            self.assertEqual(loaded["cwdtester"], 1)
        finally:
            os.chdir(old_cwd)

    def test_save_scores_creates_file_and_content_matches(self):
        """save_scores writes file lines in expected format."""
        scores = {"x": 1, "y": 2}
        tools24.save_scores(scores)
        with open(self.test_score_path, "r", encoding="utf-8") as f:
            contents = f.read().splitlines()
        expected = {f"{k}|{v}" for k, v in scores.items()}
        self.assertEqual(set(contents), expected)


if __name__ == "__main__":
    unittest.main()
