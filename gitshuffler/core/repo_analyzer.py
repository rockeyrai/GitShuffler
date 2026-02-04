from typing import List
from gitshuffler.utils.config_parser import ConfigDTO

class RepoAnalyzer:
    # Heuristics
    MAX_COMMITS_PER_MINUTE = 2  # Humans unlikely to commit more than 2x minute sustained
    FILES_PER_COMMIT_AVG_LOWER_BOUND = 1 # We can have 1 file per commit
    
    @staticmethod
    def analyze(files: List[str], config: ConfigDTO):
        """
        Analyzes the repository and configuration to ensure realistic execution.
        Raises ValueError if constraints are violated.
        """
        file_count = len(files)
        if file_count == 0:
            return # Nothing to do, planner will return empty
            
        duration_sec = config.duration_seconds
        
        # Estimate target commits based on density config
        # This is rough because Planner uses random logic, but we can bound it.
        # Max commits possible?
        
        # If duration < 24h, Planner uses min/max as total range.
        # If duration >= 24h, Planner uses min/max as per-day range.
        
        expected_commits = 0
        if duration_sec < 86400:
             expected_commits = config.commits_per_day_max # worst case
        else:
             days = duration_sec / 86400
             expected_commits = int(days * config.commits_per_day_max)
             
        # Check 1: Commit Density
        # If we expect X commits in Y seconds.
        if duration_sec > 0:
             commits_per_minute = expected_commits / (duration_sec / 60)
             if commits_per_minute > RepoAnalyzer.MAX_COMMITS_PER_MINUTE:
                 min_duration = expected_commits * (60 / RepoAnalyzer.MAX_COMMITS_PER_MINUTE)
                 # Format duration friendly
                 hint = f"{int(min_duration)}s" if min_duration < 60 else f"{int(min_duration/60)}m"
                 
                 raise ValueError(
                     f"Requested schedule is too aggressive. "
                     f"Planning up to {expected_commits} commits in {duration_sec}s ({commits_per_minute:.1f} cpm) "
                     f"is unrealistic for human activity. Increase duration to at least {hint}."
                 )

        # Check 2: Repo Size vs Time
        # If we have 100,000 files, and user asks for 2h...
        # Chunker splits files across commits.
        # If commits = 10, files = 100,000 -> 10,000 files/commit.
        # Git add 10,000 files takes time.
        # We enforced batching in GitWrapper, so it won't crash.
        # But is it "valid"? Yes.
        # Just a warning maybe?
        if file_count > 10000 and duration_sec < 600:
             print("Warning: Processing a large number of files in a short duration may cause system stress.")
