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
        
        # Check for existing state to resume
        from gitshuffler.core.state_manager import StateManager
        state_path = os.path.join(self.config.repo_path, ".gitshuffler_state.json")
        state_manager = StateManager(state_path)
        saved_manifest = state_manager.get_saved_manifest()
        
        # We only auto-resume if the state says we are incomplete
        state = state_manager.load_state()
        if saved_manifest and state and not state.is_complete:
             print(f"Detected interrupted execution. Resuming plan with {len(saved_manifest)} commits.")
             return saved_manifest

        files = self.scan_files()
        
        from gitshuffler.core.repo_analyzer import RepoAnalyzer
        RepoAnalyzer.analyze(files, self.config)
        
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
        else:
             # Safety checks for existing repo
             if not dry_run:
                 if not self.git.is_clean():
                     raise RuntimeError("Repository is not clean. Please commit or stash changes before running.")
                 if self.git.is_detached():
                     print("Warning: You are in 'detached HEAD' state. Commits will not belong to any branch.")
                     # We can choose to abort or just warn. Let's warn for now.

        # Concurrency Lock
        lock_file = os.path.join(self.config.repo_path, ".gitshuffler.lock")
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process is alive
                try:
                    os.kill(old_pid, 0) # Signal 0 checks existence
                    print(f"Error: GitShuffler is already running (PID {old_pid}). Aborting.")
                    return
                except OSError:
                    print(f"Warning: Found stale lock file from PID {old_pid}. Overwriting.")
            except (ValueError, OSError):
                print("Warning: Found corrupt lock file. Overwriting.")
        
        # Acquire lock
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            from gitshuffler.core.state_manager import StateManager
            state_path = os.path.join(self.config.repo_path, ".gitshuffler_state.json")
            state_manager = StateManager(state_path)

            # Resume logic
            try:
                 start_index = state_manager.initialize_or_resume(manifest)
            except RuntimeError as e:
                 # Hash mismatch
                 print(f"Error: {e}")
                 return

            if start_index >= len(manifest):
                 print("Plan already completed according to state.")
                 return

            print(f"Applying {len(manifest) - start_index} (total {len(manifest)}) commits...")
            
            for i in range(start_index, len(manifest)):
                action = manifest[i]
                print(f"[{i+1}/{len(manifest)}] {action.timestamp} - {len(action.files)} files")
                
                # 1. Add files
                if not dry_run:
                    self.git.add(action.files)
                else:
                     # In dry run, we simulate add but don't output 1000 lines
                     if len(action.files) > 10:
                          print(f"[Dry Run] git add {len(action.files)} files (output truncated)")
                     else:
                          print(f"[Dry Run] git add {' '.join(action.files)}")
                
                # 2. Commit
                # Now we delegate dry-run output to the wrapper for exact env var visualization
                self.git.commit(
                    message=action.message,
                    author_name=action.author_name,
                    author_email=action.author_email,
                    timestamp=action.timestamp,
                    dry_run=dry_run
                )
                
                # 3. Update State (only if real execution)
                if not dry_run:
                     state_manager.update_progress(i, is_complete=(i == len(manifest) - 1))
                
            print("Done.")

        finally:
            if os.path.exists(lock_file):
                # Clean up lock only if it is OURS (though single threaded assumption holds)
                # To be strict we could check content, but reasonably safe.
                os.remove(lock_file)
