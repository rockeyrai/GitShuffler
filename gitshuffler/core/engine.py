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

    def _validate_paths(self, files: List[str]):
        """
        Validates file paths for cross-platform safety.
        Checks for MAX_PATH limits and case conflict collisions.
        """
        # 1. MAX_PATH check (Windows usually 260, but let's be safe with 250)
        # We check the absolute path length or relative? Git usually cares about full path if checkout fail, 
        # but here we care if we can stage it.
        # Let's check relative path length < 260 for safety.
        
        long_paths = [f for f in files if len(f) > 250]
        if long_paths:
             print(f"Warning: {len(long_paths)} files have paths longer than 250 chars. This may cause issues on Windows.")
             for f in long_paths[:3]:
                 print(f"  - {f}")
        
        # 2. Case Collision Detection
        # Maps lower_case -> original_path
        seen = {}
        collisions = []
        for f in files:
            lower = f.lower()
            if lower in seen:
                collisions.append((seen[lower], f))
            else:
                seen[lower] = f
        
        if collisions:
            print(f"Warning: Detected {len(collisions)} case-insensitive path collisions.")
            print("This may cause unsafe behavior on cross-platform transfers.")
            for org, new in collisions[:3]:
                print(f"  - '{org}' vs '{new}'")

    def scan_files(self) -> List[str]:
        """
        Scans the repository for files matching the patterns.
        Strictly enforces safety by avoiding dangerous directories (node_modules)
        and skipping symbolic links.
        """
        if not self.config:
            raise RuntimeError("Config not loaded. Call load_config() first.")
        
        # Hard-coded safety excludes (directories to NEVER traverse)
        HARD_EXCLUDES = {
            'node_modules', '.git', 'dist', 'build', '.next', 'vendor', 
            '__pycache__', '.venv', 'env', 'venv'
        }
        
        all_files = set()
        
        original_cwd = os.getcwd()
        try:
            os.chdir(self.config.repo_path)
            
            # We use os.walk instead of glob to control traversal
            for root, dirs, files in os.walk(".", topdown=True):
                # 1. Prune dangerous directories in-place so we don't even enter them
                # This is critical for performance and safety (avoids deep node_modules scan)
                dirs[:] = [d for d in dirs if d not in HARD_EXCLUDES and not d.startswith('.')]
                
                # Check for symlink directories (os.walk doesn't follow by default, but let's be safe)
                # If we were following links, we'd need to check here. 
                # Since followlinks=False (default), root is safe unless it's a link itself (top level).
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    # 2. Strict Symlink Check
                    if os.path.islink(filepath):
                        continue
                        
                    # 3. Match against patterns
                    # Glob matching is tricky with os.walk. 
                    # We can use fnmatch or internal glob logic.
                    # Since config.file_patterns are globs like "**/*.py", we need to check if filepath matches.
                    # Simplest way: Check extension if pattern is simple, or match against normalized path?
                    
                    # Actually, simple globs:
                    # To support full glob power (like src/**/*.py), we might need to filter AFTER.
                    # BUT we want to avoid scanning node_modules.
                    # So: We walk EVERYTHING (that isn't excluded), then filter by pattern.
                    
                    norm_path = os.path.normpath(filepath)
                    if norm_path.startswith("./"):
                        norm_path = norm_path[2:]
                        
                    # Optimally, we check matches. 
                    # For V1 compatibility, we used glob.glob(pattern).
                    # Now we have candidate files, we see if they match ANY pattern.
                    # This is slightly expensive O(N*P).
                    # Let's use fnmatch.
                    import fnmatch
                    
                    matched = False
                    for pattern in self.config.file_patterns:
                        # fnmatch doesn't handle ** properly.
                        # Convert "**/*.py" -> "*.py" for simple extension matching
                        # Or convert "**" to "*" for broader matching
                        
                        # Strategy: If pattern starts with "**/" or is "**", we match recursively.
                        # fnmatch("foo/bar.py", "*.py") = False
                        # fnmatch("foo/bar.py", "*/*.py") = True
                        # fnmatch("bar.py", "*.py") = True
                        
                        # Best approach: Replace all "**" with "*" since we already walk all dirs.
                        # Then fnmatch should work for most cases.
                        fnmatch_pattern = pattern.replace("**/", "").replace("**", "*")
                        
                        if fnmatch.fnmatch(norm_path, fnmatch_pattern) or fnmatch.fnmatch(filename, fnmatch_pattern):
                             matched = True
                             break
                    
                    if matched:
                         all_files.add(norm_path)

        finally:
            os.chdir(original_cwd)
            
        file_list = sorted(list(all_files))
        self._validate_paths(file_list)
        return file_list

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
        
        # GPG Check
        if self.git.check_gpg_sign():
             print("Warning: GPG signing is enabled (commit.gpgsign=true).")
             print("If your key requires a passphrase, this process may hang or fail non-interactively.")
        
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
                 
                 # Resume Integrity Check
                 saved_state = state_manager.load_state()
                 if saved_state and saved_state.last_commit_hash:
                     current_head = self.git.get_head_hash()
                     if current_head and current_head != saved_state.last_commit_hash:
                         print("CRITICAL ERROR: Repository State Mismatch!")
                         print(f"Saved state expects HEAD at: {saved_state.last_commit_hash}")
                         print(f"Current repository HEAD is at: {current_head}")
                         print("The repository history has diverged (rewind, rebase, or external commits detected).")
                         print("Cannot safely resume. Please delete .gitshuffler_state.json to force a fresh run.")
                         return
            except RuntimeError as e:
                 # Hash mismatch
                 print(f"Error: {e}")
                 return

            if start_index >= len(manifest):
                 print("Plan already completed according to state.")
                 return

            if dry_run:
                print("\n=== DRY RUN / SIMULATED MODE ===")
                print("No changes will be written to disk.")
                print("================================\n")

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
                     head_hash = self.git.get_head_hash()
                     state_manager.update_progress(i, head_hash, is_complete=(i == len(manifest) - 1))
                
            print("Done.")

        finally:
            if os.path.exists(lock_file):
                # Clean up lock only if it is OURS (though single threaded assumption holds)
                # To be strict we could check content, but reasonably safe.
                os.remove(lock_file)
