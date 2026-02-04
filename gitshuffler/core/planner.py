import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List
from gitshuffler.utils.config_parser import ConfigDTO
from gitshuffler.core.chunker import Chunker

@dataclass
class CommitAction:
    author_name: str
    author_email: str
    timestamp: datetime
    files: List[str]
    message: str

class Planner:
    def __init__(self, config: ConfigDTO):
        self.config = config

    def plan(self, file_list: List[str]) -> List[CommitAction]:
        """
        Generates a list of CommitActions based on the V2 config and file list.
        Scheduling is relative to NOW.
        """
        if not file_list:
            return []

        # 1. Determine Start Time (NOW)
        start_dt = datetime.now()
        duration_sec = self.config.duration_seconds
        
        # 2. Determine Number of Commits
        if self.config.total_commits:
            num_commits = self.config.total_commits
        else:
            # Auto-calculate: Default to 1 commit per 5 files
            # But ensure at least 1 commit if files exist
            # And cap density? (RepoAnalyzer already checked safety)
            density = 5
            num_commits = max(1, len(file_list) // density)
            
            # If we have huge files but small duration, num_commits might be too high
            # RepoAnalyzer warned about this.
            # Let's trust the logic max(1, ...)
            
        if num_commits == 0:
            return []

        # 3. Chunk Files
        file_chunks = Chunker.chunk_files(file_list, num_commits)
        # Recalculate actual commits based on chunks (it might handle remainders)
        total_commits_final = len(file_chunks)
        
        # 4. Generate Timestamps
        timestamps = []
        if self.config.mode == "random":
             # Random distribution within duration
             for _ in range(total_commits_final):
                 offset = random.uniform(0, duration_sec)
                 timestamps.append(start_dt + timedelta(seconds=offset))
             timestamps.sort()
        else:
             # Even distribution (Default)
             # interval = duration / count
             # To act nicely, we spread them from T=0 to T=duration
             if total_commits_final == 1:
                  # If only 1 commit, put it likely at T=0 or T=mid?
                  # T=0 implies immediate. Let's do T=0.
                  timestamps.append(start_dt)
             else:
                  step = duration_sec / (total_commits_final - 1) if duration_sec > 0 else 0
                  for i in range(total_commits_final):
                       offset = i * step
                       timestamps.append(start_dt + timedelta(seconds=offset))

        manifest: List[CommitAction] = []
        
        # 5. Assign Actions
        for i in range(total_commits_final):
            ts = timestamps[i]
            request_files = file_chunks[i]
            self._add_action(manifest, request_files, ts)

        return manifest

    def _add_action(self, manifest: List[CommitAction], request_files: List[str], timestamp: datetime):
        # Helper to create action
        msg = f"Update {len(request_files)} files"
        # Add basic summary
        if request_files:
             msg += f"\n\n- " + "\n- ".join(request_files[:5])
             if len(request_files) > 5:
                 msg += f"\n...and {len(request_files)-5} more."
        
        # Helper to pick author
        authors_list = self.config.authors
        chosen_author = authors_list[0] # Default
        
        if len(authors_list) > 1:
             weights = [a.weight for a in authors_list]
             # random.choices returns a list [k]
             chosen_author = random.choices(authors_list, weights=weights, k=1)[0]

        action = CommitAction(
            author_name=chosen_author.name,
            author_email=chosen_author.email,
            timestamp=timestamp,
            files=request_files,
            message=msg
        )
        manifest.append(action)
