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
        Generates a list of CommitActions based on the config and file list.
        """
        if not file_list:
            return []

        start_dt = datetime.fromisoformat(self.config.start_date)
        total_days = self.config.days_active
        
        # 1. Determine total number of commits needed
        # We simulate day by day.
        
        daily_plans = []
        total_commits_needed = 0

        for day_offset in range(total_days):
            current_date = start_dt + timedelta(days=day_offset)
            
            # Randomly decide how many commits for this day
            num_commits = random.randint(
                self.config.commits_per_day_min,
                self.config.commits_per_day_max
            )
            
            if num_commits > 0:
                daily_plans.append({
                    "date": current_date,
                    "num_commits": num_commits
                })
                total_commits_needed += num_commits

        # If zero commits planned (unlikely due to min/max, but possible if min=0), return empty
        if total_commits_needed == 0:
            return []

        # 2. Chunk the files
        file_chunks = Chunker.chunk_files(file_list, total_commits_needed)
        
        # It's possible Chunker returned fewer chunks than requested if num_files < total_commits_needed
        # We need to adjust our plan to match the actual number of chunks available.
        actual_chunks_count = len(file_chunks)
        
        manifest: List[CommitAction] = []
        chunk_idx = 0

        for plan in daily_plans:
            date_base = plan["date"]
            # working hours 9am - 6pm roughly
            # spread commits out
            
            commits_today = plan["num_commits"]
            
            for _ in range(commits_today):
                if chunk_idx >= actual_chunks_count:
                    break
                
                request_files = file_chunks[chunk_idx]
                chunk_idx += 1

                # Random time between 9 AM and 6 PM
                hour = random.randint(9, 17)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                timestamp = date_base.replace(hour=hour, minute=minute, second=second)
                
                # Simple message generation
                msg = f"Update {len(request_files)} files\n\n- " + "\n- ".join(request_files[:5])
                if len(request_files) > 5:
                    msg += f"\n...and {len(request_files)-5} more."

                action = CommitAction(
                    author_name=self.config.author_name,
                    author_email=self.config.author_email,
                    timestamp=timestamp,
                    files=request_files,
                    message=msg
                )
                manifest.append(action)

        return manifest
