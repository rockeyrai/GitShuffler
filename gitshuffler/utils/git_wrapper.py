import subprocess
import os
from typing import List, Optional
from datetime import datetime

class GitWrapper:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def run_command(self, args: List[str], env: Optional[dict] = None) -> str:
        """
        Runs a git command in the repository path.
        """
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                env=full_env,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {' '.join(args)}\nError: {e.stderr}")

    def init(self):
        """Initializes a new git repository."""
        self.run_command(["init"])

    def add(self, files: List[str]):
        """
        Adds specific files to the staging area. Batches commands to avoid CLI limit.
        Checks for file existence to prevent crashes if files are deleted mid-execution.
        """
        if not files:
            return
        
        # Filter existing files
        valid_files = []
        missing_count = 0
        
        # When running add, we must address files relative to repo_path
        # The input `files` are likely relative paths from repo root (as returned by scan_files).
        # Wrapper methods usually run in repo_path via CWD=repo_path in run_command.
        # So we should check existence relative to repo_path.
        
        for f in files:
            full_path = os.path.join(self.repo_path, f)
            if os.path.exists(full_path):
                valid_files.append(f)
            else:
                missing_count += 1
                if missing_count <= 5: 
                    print(f"Warning: File '{f}' missing, skipping.")
        
        if missing_count > 5:
            print(f"Warning: {missing_count} files missing in total. Skipping them.")

        if not valid_files:
            return

        BATCH_SIZE = 1000
        for i in range(0, len(valid_files), BATCH_SIZE):
            batch = valid_files[i:i + BATCH_SIZE]
            self.run_command(["add"] + batch)

    def commit(self, message: str, author_name: str, author_email: str, timestamp: datetime, dry_run: bool = False):
        """
        Commits staged changes with specific author and timestamp.
        If dry_run is True, prints the command and environment variables instead of executing.
        """
        # Format timestamp for GIT_AUTHOR_DATE and GIT_COMMITTER_DATE
        # Format: "YYYY-MM-DD HH:MM:SS" or ISO 8601
        date_str = timestamp.isoformat()

        env = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_AUTHOR_DATE": date_str,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
            "GIT_COMMITTER_DATE": date_str,
        }

        if dry_run:
            env_str = " ".join([f'{k}="{v}"' for k, v in env.items()])
            print(f"[Dry Run] Env: {env_str}")
            print(f"[Dry Run] Cmd: git commit -m \"{message}\"")
            return

        self.run_command(["commit", "-m", message], env=env)

    def verify_installed(self):
        """Checks if git is installed."""
        try:
            self.run_command(["--version"])
        except RuntimeError:
            raise RuntimeError("Git is not installed or not found in PATH.")

    def is_clean(self) -> bool:
        """
        Returns True if the working directory is clean (no uncommitted changes).
        Ignores untracked files (??) as those are likely the target of the shuffle.
        """
        output = self.run_command(["status", "--porcelain"])
        if not output:
            return True
        
        for line in output.splitlines():
            # Check for non-untracked changes
            # Porcelain format: XY Path
            # ?? = Untracked
            if not line.strip().startswith("??"):
                return False
        return True

    def current_branch(self) -> str:
        """Returns the current branch name. Returns 'HEAD' if detached or unable to determine."""
        try:
            return self.run_command(["symbolic-ref", "--short", "HEAD"])
        except RuntimeError:
            # Fallback for detached HEAD or other issues
            try:
                return self.run_command(["rev-parse", "--abbrev-ref", "HEAD"])
            except RuntimeError:
                return "HEAD"

    def is_detached(self) -> bool:
        """Returns True if HEAD is detached."""
        return self.current_branch() == "HEAD"
