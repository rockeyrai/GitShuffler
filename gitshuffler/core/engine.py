import glob
import os
from typing import List
from gitshuffler.utils.config_parser import ConfigParser, ConfigDTO
from gitshuffler.utils.git_wrapper import GitWrapper
from gitshuffler.core.planner import Planner, CommitAction

class Engine:
    def __init__(self, config_path: str = "gitshuffler.json"):
        self.config_path = config_path
        self.config: ConfigDTO = None
        self.git = GitWrapper() # Default to current dir

    def load_config(self):
        self.config = ConfigParser.parse(self.config_path)
        self.git = GitWrapper(self.config.repo_path)

    def scan_files(self) -> List[str]:
        """
        Scans the repository for files matching the patterns.
        """
        if not self.config:
            raise RuntimeError("Config not loaded. Call load_config() first.")
        
        all_files = set()
        
        original_cwd = os.getcwd()
        try:
            # Move to repo path to run glob relative to it
            # Or we can construct absolute paths.
            # Let's ensure we work with paths relative to repo_path
            os.chdir(self.config.repo_path)
            
            for pattern in self.config.file_patterns:
                # recursive glob if pattern contains **
                matches = glob.glob(pattern, recursive=True)
                for m in matches:
                    if os.path.isfile(m):
                        # Normalize path
                        all_files.add(os.path.normpath(m))
        finally:
            os.chdir(original_cwd)
            
        return sorted(list(all_files))

    def plan(self) -> List[CommitAction]:
        """
        Runs the planning phase.
        """
        self.load_config()
        files = self.scan_files()
        planner = Planner(self.config)
        return planner.plan(files)

    def apply(self, manifest: List[CommitAction], dry_run: bool = False):
        """
        Executes the plan.
        """
        if not manifest:
            print("No commits to apply.")
            return

        self.git.verify_installed()
        
        # We assume the user wants to init if not already a repo?
        # Or maybe we should check. The requirements said "scans files from a repository".
        # But `gitshuffler init` generates config, not git init.
        # Let's check if .git exists, if not, maybe init it?
        # The prompt says "Scans files from a repository", implies existence.
        # But let's be safe. If we run git commands on non-repo, wrapper handles error.
        # However, for convenience, let's ensure init.
        
        if not os.path.isdir(os.path.join(self.config.repo_path, ".git")):
             if not dry_run:
                 print(f"Initializing git repository at {self.config.repo_path}...")
                 self.git.init()
             else:
                 print(f"[Dry Run] would init git repo at {self.config.repo_path}")

        print(f"Applying {len(manifest)} commits...")
        
        for i, action in enumerate(manifest):
            print(f"[{i+1}/{len(manifest)}] {action.timestamp} - {len(action.files)} files")
            
            if dry_run:
                # Just simulate
                continue

            # 1. Add files
            self.git.add(action.files)
            
            # 2. Commit
            self.git.commit(
                message=action.message,
                author_name=action.author_name,
                author_email=action.author_email,
                timestamp=action.timestamp
            )
            
        print("Done.")
