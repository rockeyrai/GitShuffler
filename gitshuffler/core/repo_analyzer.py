from typing import List
from gitshuffler.utils.config_parser import ConfigDTO
import math

class RepoAnalyzer:
    # Heuristics
    # We allow up to 10 commits per minute to handle bursts or small demos.
    # Higher than that might be spammy or unrealistic for "natural" history.
    MAX_COMMITS_PER_MINUTE = 10  
    FILES_PER_COMMIT_AVG_LOWER_BOUND = 1 
    
    @staticmethod
    def analyze(files: List[str], config: ConfigDTO):
        """
        Analyzes the repository and configuration to ensure realistic execution.
        Raises ValueError if constraints are violated.
        """
        file_count = len(files)
        if file_count == 0:
            return 
            
        duration_sec = config.duration_seconds
        
        # Estimate expected commits
        if config.total_commits:
             expected_commits = config.total_commits
        else:
             # Heuristic: If explicit total not provided, we assume roughly 1 commit per 5 files.
             # This is just for density checking. Planner might decide otherwise if logic differs.
             # We should align this heuristic with Planner's default.
             expected_commits = max(1, file_count // 5)

        # Check 1: Commit Density
        if duration_sec > 0:
             commits_per_minute = expected_commits / (duration_sec / 60)
             
             if commits_per_minute > RepoAnalyzer.MAX_COMMITS_PER_MINUTE:
                  min_seconds = expected_commits * (60 / RepoAnalyzer.MAX_COMMITS_PER_MINUTE)
                  hint_m = math.ceil(min_seconds / 60)
                  
                  raise ValueError(
                      f"Requested schedule is too aggressive ({commits_per_minute:.1f} commits/min). "
                      f"Planning {expected_commits} commits in {int(duration_sec)}s. "
                      f"Please increase duration to at least {hint_m}m "
                      f"or reduce the number of commits."
                  )

        # Check 2: Repo Size vs Time (Warning)
        # If processing > 10k files in < 10 mins, might be heavy.
        if file_count > 10000 and duration_sec < 600:
             print("Warning: Processing a large number of files in a short duration may cause system stress.")
