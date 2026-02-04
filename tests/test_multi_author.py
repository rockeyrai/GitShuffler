import unittest
import json
import os
from unittest.mock import MagicMock, patch
from gitshuffler.utils.config_parser import ConfigParser, ConfigDTO
from gitshuffler.core.planner import Planner

class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.test_config = "test_config.json"

    def tearDown(self):
        if os.path.exists(self.test_config):
            os.remove(self.test_config)

    def write_config(self, data):
        with open(self.test_config, "w") as f:
            json.dump(data, f)

    def test_valid_multi_author(self):
        data = {
            "repo_path": ".",
            "authors": [
                {"name": "A", "email": "a@a.com", "weight": 0.5},
                {"name": "B", "email": "b@b.com", "weight": 0.5}
            ],
            "days_active": 1,
            "commits_per_day_min": 1,
            "commits_per_day_max": 2,
            "start_date": "2023-01-01",
            "file_patterns": ["*"]
        }
        self.write_config(data)
        config = ConfigParser.parse(self.test_config)
        self.assertEqual(len(config.authors), 2)
        self.assertEqual(config.authors[0].name, "A")

    def test_invalid_weights(self):
        data = {
            "repo_path": ".",
            "authors": [
                {"name": "A", "email": "a@a.com", "weight": 0.1},
                {"name": "B", "email": "b@b.com", "weight": 0.1}
            ],
            "days_active": 1,
            "commits_per_day_min": 1,
            "commits_per_day_max": 2,
            "start_date": "2023-01-01",
            "file_patterns": ["*"]
        }
        self.write_config(data)
        with self.assertRaises(ValueError) as cm:
            ConfigParser.parse(self.test_config)
        self.assertIn("Author weights must sum to 1.0", str(cm.exception))

    def test_missing_author_info(self):
        data = {
            "repo_path": ".",
            "days_active": 1,
            "commits_per_day_min": 1,
            "commits_per_day_max": 2,
            "start_date": "2023-01-01",
            "file_patterns": ["*"]
        }
        self.write_config(data)
        with self.assertRaises(ValueError):
            ConfigParser.parse(self.test_config)

    def test_fallback_defaults(self):
        data = {
            "repo_path": ".",
            "author_name": "Old",
            "author_email": "old@old.com",
            "days_active": 1,
            "commits_per_day_min": 1,
            "commits_per_day_max": 2,
            "start_date": "2023-01-01",
             "file_patterns": ["*"]
        }
        self.write_config(data)
        config = ConfigParser.parse(self.test_config)
        self.assertEqual(len(config.authors), 1)
        self.assertEqual(config.authors[0].name, "Old")
        self.assertEqual(config.authors[0].weight, 1.0)

class TestPlanner(unittest.TestCase):
    def test_planner_assigns_authors(self):
        # Mock ConfigDTO
        mock_config = MagicMock()
        mock_config.start_date = "2023-01-01"
        mock_config.days_active = 1
        mock_config.commits_per_day_min = 5
        mock_config.commits_per_day_max = 5
        
        # Test Authors
        author1 = MagicMock()
        author1.name = "A"
        author1.email = "a@a.com"
        author1.weight = 1.0 # Force A
        
        mock_config.authors = [author1]
        
        planner = Planner(mock_config)
        
        # Mock files
        files = ["f1", "f2", "f3", "f4", "f5"]
        
        # Chunking will likely put 1 file per commit if total commits needed matches file count
        # or similar.
        
        manifest = planner.plan(files)
        self.assertTrue(len(manifest) > 0)
        for action in manifest:
            self.assertEqual(action.author_name, "A")
            self.assertEqual(action.author_email, "a@a.com")

if __name__ == '__main__':
    unittest.main()
