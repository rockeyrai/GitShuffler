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
        """Adds specific files to the staging area."""
        if not files:
            return
        self.run_command(["add"] + files)

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
