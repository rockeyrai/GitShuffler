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
        duration_sec = self.config.duration_seconds
        
        # Decide mode: Session (< 24h) or Long-Term (>= 24h)
        # Note: self.config.days_active is now derived/fallback, rely on duration_sec
        
        manifest: List[CommitAction] = []
        
        if duration_sec < 86400:
            # --- SESSION MODE ---
            # Treat as a single continuous session.
            # Total commits? derived from commits_per_day density or just min/max?
            # If I want "2h" session with "5 commits/day" density, that's small.
            # But usually "2h" implies I want to simulate a burst.
            # Let's interpret min/max as "commits per session" if < 24h?
            # Or better, just ensure we have enough commits to cover the files loosely?
            # Current Chunker requires 'total_commits_needed'.
            
            # Heuristic: For short sessions, strictly follow min/max as "per session" range
            # UNLESS min/max are clearly "per day" scales (like 1-5).
            # If user sets "2h", and "1-5 commits", we probably mean 1-5 commits in that 2h.
            
            num_commits = random.randint(
                self.config.commits_per_day_min,
                self.config.commits_per_day_max
            )
            
            if num_commits == 0:
                return []
                
            # Chunk files
            file_chunks = Chunker.chunk_files(file_list, num_commits)
            total_commits_final = len(file_chunks)
            
            # Distribute timestamps in [start, start + duration]
            # We want them sorted.
            timestamps = []
            for _ in range(total_commits_final):
                offset = random.randint(0, int(duration_sec))
                timestamps.append(start_dt + timedelta(seconds=offset))
            timestamps.sort()
            
            # Assign
            for i in range(total_commits_final):
                ts = timestamps[i]
                request_files = file_chunks[i]
                self._add_action(manifest, request_files, ts)

        else:
            # --- LONG TERM MODE ---
            # Iterate days as before
            total_days = int(duration_sec // 86400)
            remaining_sec = duration_sec % 86400
            if remaining_sec > 0:
                total_days += 1
            
            daily_plans = []
            total_commits_needed = 0
            
            for day_offset in range(total_days):
                current_date = start_dt + timedelta(days=day_offset)
                
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
            
            if total_commits_needed == 0:
                return []

            file_chunks = Chunker.chunk_files(file_list, total_commits_needed)
            actual_chunks_count = len(file_chunks)
            
            chunk_idx = 0
            for plan in daily_plans:
                date_base = plan["date"]
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
                    self._add_action(manifest, request_files, timestamp)

        return manifest

    def _add_action(self, manifest: List[CommitAction], request_files: List[str], timestamp: datetime):
        # Helper to create action
        msg = f"Update {len(request_files)} files\n\n- " + "\n- ".join(request_files[:5])
        if len(request_files) > 5:
            msg += f"\n...and {len(request_files)-5} more."
        
        authors_list = self.config.authors
        weights = [a.weight for a in authors_list]
        chosen_author = random.choices(authors_list, weights=weights, k=1)[0]

        action = CommitAction(
            author_name=chosen_author.name,
            author_email=chosen_author.email,
            timestamp=timestamp,
            files=request_files,
            message=msg
        )
        manifest.append(action)
