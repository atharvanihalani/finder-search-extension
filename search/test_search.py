#!/usr/bin/env python3
"""Tests for the search script using unittest (no external dependencies)."""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import functions from search module
from search import (
    load_config,
    expand_directories,
    build_mdfind_command,
    matches_exclusion,
    matches_filename_exclusion,
    get_file_info,
    calculate_recency_score,
    rank_results,
    search,
)


class TestExpandDirectories(unittest.TestCase):
    def test_expands_tilde(self):
        dirs = ["~/Documents", "~/Downloads"]
        expanded = expand_directories(dirs)
        home = os.path.expanduser("~")
        self.assertEqual(expanded, [f"{home}/Documents", f"{home}/Downloads"])

    def test_handles_absolute_paths(self):
        dirs = ["/tmp/test", "/var/log"]
        expanded = expand_directories(dirs)
        self.assertEqual(expanded, ["/tmp/test", "/var/log"])

    def test_empty_list(self):
        self.assertEqual(expand_directories([]), [])


class TestBuildMdfindCommand(unittest.TestCase):
    def test_single_word_query(self):
        cmd = build_mdfind_command("test", ["/tmp"])
        self.assertEqual(cmd, ["mdfind", "-onlyin", "/tmp", "test"])

    def test_multiple_words_become_or(self):
        cmd = build_mdfind_command("hello world", ["/tmp"])
        self.assertEqual(cmd, ["mdfind", "-onlyin", "/tmp", "hello | world"])

    def test_multiple_directories(self):
        cmd = build_mdfind_command("test", ["/tmp", "/var"])
        self.assertEqual(cmd, ["mdfind", "-onlyin", "/tmp", "-onlyin", "/var", "test"])

    def test_three_words(self):
        cmd = build_mdfind_command("one two three", ["/tmp"])
        self.assertEqual(cmd, ["mdfind", "-onlyin", "/tmp", "one | two | three"])


class TestMatchesExclusion(unittest.TestCase):
    def test_matches_site_packages(self):
        self.assertTrue(matches_exclusion(
            "/Users/test/project/venv/lib/python3.9/site-packages/pkg/file.py",
            ["*/site-packages/*"]
        ))

    def test_matches_node_modules(self):
        self.assertTrue(matches_exclusion(
            "/Users/test/project/node_modules/lodash/index.js",
            ["*/node_modules/*"]
        ))

    def test_matches_git(self):
        self.assertTrue(matches_exclusion(
            "/Users/test/project/.git/config",
            ["*/.git/*"]
        ))

    def test_no_match(self):
        self.assertFalse(matches_exclusion(
            "/Users/test/Documents/report.pdf",
            ["*/site-packages/*", "*/node_modules/*"]
        ))

    def test_empty_patterns(self):
        self.assertFalse(matches_exclusion("/any/path/file.txt", []))

    def test_app_bundle(self):
        self.assertTrue(matches_exclusion(
            "/Applications/Slack.app/Contents/Resources/file.txt",
            ["*.app/*"]
        ))


class TestMatchesFilenameExclusion(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(matches_filename_exclusion("meta.json", ["meta.json"]))

    def test_wildcard_extension(self):
        self.assertTrue(matches_filename_exclusion("test.pyc", ["*.pyc"]))
        self.assertTrue(matches_filename_exclusion("debug.log", ["*.log"]))

    def test_wildcard_prefix(self):
        self.assertTrue(matches_filename_exclusion(".eslintrc.json", [".eslintrc*"]))

    def test_no_match(self):
        self.assertFalse(matches_filename_exclusion("report.pdf", ["meta.json", "*.pyc"]))

    def test_empty_exclusions(self):
        self.assertFalse(matches_filename_exclusion("anything.txt", []))

    def test_ds_store(self):
        self.assertTrue(matches_filename_exclusion(".DS_Store", [".DS_Store"]))


class TestGetFileInfo(unittest.TestCase):
    def test_valid_file(self):
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            info = get_file_info(temp_path)
            self.assertIsNotNone(info)
            self.assertEqual(info["path"], temp_path)
            self.assertEqual(info["filename"], os.path.basename(temp_path))
            self.assertIn("modified", info)
            self.assertIn("mtime", info)
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file(self):
        info = get_file_info("/nonexistent/path/file.txt")
        self.assertIsNone(info)


class TestCalculateRecencyScore(unittest.TestCase):
    def test_file_modified_now(self):
        now = time.time()
        score = calculate_recency_score(now, now)
        self.assertEqual(score, 1.0)

    def test_file_modified_30_days_ago(self):
        now = time.time()
        thirty_days_ago = now - (30 * 86400)
        score = calculate_recency_score(thirty_days_ago, now)
        self.assertEqual(score, 0.0)

    def test_file_modified_15_days_ago(self):
        now = time.time()
        fifteen_days_ago = now - (15 * 86400)
        score = calculate_recency_score(fifteen_days_ago, now)
        self.assertAlmostEqual(score, 0.5, places=1)

    def test_file_modified_older_than_30_days(self):
        now = time.time()
        old = now - (60 * 86400)  # 60 days ago
        score = calculate_recency_score(old, now)
        self.assertEqual(score, 0.0)


class TestRankResults(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(rank_results([]), [])

    def test_single_result(self):
        files = [{"mtime": time.time(), "path": "/test", "filename": "test"}]
        ranked = rank_results(files)
        self.assertEqual(len(ranked), 1)
        self.assertIn("score", ranked[0])

    def test_recent_files_ranked_higher(self):
        now = time.time()
        files = [
            {"mtime": now - (20 * 86400), "path": "/old", "filename": "old"},  # 20 days old
            {"mtime": now, "path": "/new", "filename": "new"},  # today
        ]
        # Both start at same position, so recency should determine order
        ranked = rank_results(files, relevance_weight=0.0, recency_weight=1.0)
        self.assertEqual(ranked[0]["path"], "/new")
        self.assertEqual(ranked[1]["path"], "/old")

    def test_all_results_have_scores(self):
        now = time.time()
        files = [
            {"mtime": now - (25 * 86400), "path": "/a", "filename": "a"},
            {"mtime": now, "path": "/b", "filename": "b"},
        ]
        ranked = rank_results(files)
        self.assertTrue(all("score" in f for f in ranked))


class TestLoadConfig(unittest.TestCase):
    def test_loads_existing_config(self):
        # The actual config.json should exist
        config = load_config()
        self.assertIn("include_directories", config)
        self.assertIn("exclude_patterns", config)

    def test_config_has_valid_structure(self):
        config = load_config()
        self.assertIsInstance(config["include_directories"], list)
        self.assertIsInstance(config["exclude_patterns"], list)


class TestSearch(unittest.TestCase):
    def test_empty_query_returns_empty(self):
        result = search("")
        self.assertEqual(result, [])

    def test_whitespace_query_returns_empty(self):
        result = search("   ")
        self.assertEqual(result, [])

    @patch('search.subprocess.run')
    @patch('search.load_config')
    @patch('search.os.path.isdir')
    def test_search_calls_mdfind_with_or(self, mock_isdir, mock_config, mock_run):
        mock_isdir.return_value = True
        mock_config.return_value = {
            "include_directories": ["/tmp"],
            "exclude_patterns": []
        }
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        search("test query")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        self.assertIn("mdfind", cmd)
        self.assertIn("test | query", cmd)  # OR search


class TestIntegration(unittest.TestCase):
    """Integration tests that actually run the search."""

    def test_search_returns_list(self):
        """Test that search returns a list."""
        results = search("test")
        self.assertIsInstance(results, list)

    def test_search_results_structure(self):
        """Test that search results have correct structure."""
        results = search("test")

        for result in results:
            self.assertIn("path", result)
            self.assertIn("filename", result)
            self.assertIn("modified", result)
            self.assertIn("score", result)

            # Validate types
            self.assertIsInstance(result["path"], str)
            self.assertIsInstance(result["filename"], str)
            self.assertIsInstance(result["score"], float)

            # Score should be between 0 and 1
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 1)

    def test_limit_respected(self):
        """Test that the result limit is respected."""
        results = search("a", limit=5)  # 'a' should match many files
        self.assertLessEqual(len(results), 5)

    def test_or_search_broadens_results(self):
        """Test that OR search includes files matching any term."""
        # This just verifies the search runs without error
        results = search("pdf md")
        self.assertIsInstance(results, list)


if __name__ == "__main__":
    # Run with verbosity
    unittest.main(verbosity=2)
