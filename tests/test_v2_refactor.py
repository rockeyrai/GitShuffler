import unittest
import os
import shutil
import json
from unittest.mock import MagicMock, patch
from gitshuffler.core.engine import Engine
from gitshuffler.utils.config_parser import ConfigParser

class TestV2Refactor(unittest.TestCase):
    def setUp(self):
        self.test_dir = "v2_test_env"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Create dummy repo
        os.makedirs(os.path.join(self.test_dir, ".git"))
        self.repo_path = os.path.abspath(self.test_dir)
        
        # Create safe files
        with open(os.path.join(self.test_dir, "safe.py"), "w") as f:
            f.write("print('hello')")
            
        # Create dangerous files (node_modules)
        nm_dir = os.path.join(self.test_dir, "node_modules")
        os.makedirs(nm_dir)
        with open(os.path.join(nm_dir, "dangerous.js"), "w") as f:
            f.write("alert('bad')")
            
        # Create symlink if on posix
        if os.name == 'posix':
            os.symlink(os.path.join(nm_dir, "dangerous.js"), os.path.join(self.test_dir, "bad_link.js"))

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_config_v2_parsing(self):
        # Create valid V2 config
        config_path = os.path.join(self.test_dir, "gitshuffler.json")
        conf_data = {
            "repo_path": self.repo_path,
            "duration": "2h",
            "file_patterns": ["**/*.py", "**/*.js"],
            "total_commits": 5,
            "author_name": "Test Author",
            "author_email": "test@example.com"
        }
        with open(config_path, "w") as f:
            json.dump(conf_data, f)
            
        parser = ConfigParser()
        config = parser.parse(config_path)
        
        self.assertEqual(config.duration_seconds, 7200)
        self.assertEqual(config.total_commits, 5)

    def test_safety_scan_excludes(self):
        # Engine should ignore node_modules and symlinks
        with open(os.path.join(self.test_dir, "gitshuffler.json"), "w") as f:
            json.dump({
                "repo_path": self.repo_path,
                "duration": "1h",
                "file_patterns": ["**/*"],
                "author_name": "Test",
                "author_email": "test@test.com"
            }, f)
            
        engine = Engine(os.path.join(self.test_dir, "gitshuffler.json"))
        engine.load_config()
        
        files = engine.scan_files()
        
        # Should contain 'safe.py'
        # Should NOT contain 'node_modules/dangerous.js'
        # Should NOT contain 'bad_link.js'
        
        print("Scanned files:", files)
        
        self.assertTrue(any("safe.py" in f for f in files))
        self.assertFalse(any("node_modules" in f for f in files))
        self.assertFalse(any("bad_link" in f for f in files))

    def test_planner_v2_schedule(self):
        # Test V2 planning logic
        # Create more files to allow 3 commits
        for i in range(6):
            with open(os.path.join(self.test_dir, f"file{i}.py"), "w") as f:
                f.write(f"# file {i}")
                
        with open(os.path.join(self.test_dir, "gitshuffler.json"), "w") as f:
            json.dump({
                "repo_path": self.repo_path,
                "duration": "10m",
                "total_commits": 3,
                "file_patterns": ["**/*.py"],
                "author_name": "Planner",
                "author_email": "planner@test.com"
            }, f)
            
        engine = Engine(os.path.join(self.test_dir, "gitshuffler.json"))
        manifest = engine.plan()
        
        # Should have 3 commits (or less if Chunker merges)
        self.assertGreaterEqual(len(manifest), 1)
        self.assertLessEqual(len(manifest), 3)
        
        # Check timestamps are increasing and within 10m (600s)
        if len(manifest) > 1:
            start = manifest[0].timestamp
            end = manifest[-1].timestamp
            diff = (end - start).total_seconds()
            
            self.assertLessEqual(diff, 600)

if __name__ == '__main__':
    unittest.main()
