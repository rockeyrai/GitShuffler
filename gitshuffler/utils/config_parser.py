import json
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AuthorDTO:
    name: str
    email: str
    weight: float = 0.0

@dataclass
class ConfigDTO:
    repo_path: str
    duration_str: str  # e.g. "2h", "5d"
    file_patterns: List[str]
    
    # Optional V2 fields
    total_commits: Optional[int] = None
    mode: str = "even" # "even" or "random"
    
    # Authors
    authors: List[AuthorDTO] = None
    
    # Internal calculated
    duration_seconds: float = 0.0

class ConfigParser:
    @staticmethod
    def parse(config_path: str) -> ConfigDTO:
        """
        Parses the JSON configuration file (V2 Schema).
        Raises ValueError if the config is invalid.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

        # Required fields V2
        required_fields = ["repo_path", "duration", "file_patterns"]
        for field in required_fields:
            if field not in data:
                 # Check for legacy fields to give helpful error
                 if field == "duration" and "days_active" in data:
                      raise ValueError("Config outdated: 'days_active' is deprecated. Please use 'duration' (e.g. \"5d\").")
                 raise ValueError(f"Missing required field in config: {field}")

        # Duration Parsing
        from gitshuffler.utils.time_utils import TimeUtils
        try:
             td = TimeUtils.parse_duration(data["duration"])
             duration_seconds = td.total_seconds()
             if duration_seconds <= 0:
                  raise ValueError("Duration must be positive.")
        except ValueError as e:
             raise ValueError(f"Invalid 'duration': {e}")

        # Total Commits
        total_commits = data.get("total_commits")
        if total_commits is not None:
             if not isinstance(total_commits, int) or total_commits < 1:
                  raise ValueError("total_commits must be a positive integer.")

        # Authors
        authors: List[ConfigParser.AuthorDTO] = []
        # Support V2 authors list primarily
        if "authors" in data and data["authors"]:
            raw_authors = data["authors"]
            total_weight = 0.0
            for a in raw_authors:
                if "name" not in a or "email" not in a:
                    raise ValueError("Each author in 'authors' must have 'name' and 'email'")
                weight = a.get("weight", 0.0)
                total_weight += weight
                authors.append(AuthorDTO(name=a["name"], email=a["email"], weight=weight))
            
            if raw_authors and any("weight" in a for a in raw_authors):
                 if not (0.99 <= total_weight <= 1.01):
                      raise ValueError(f"Author weights must sum to 1.0 (got {total_weight})")
        else:
             # Legacy fallback support for author_name/email -> converted to list
             name = data.get("author_name")
             email = data.get("author_email")
             
             if not name or not email:
                  # Check 'default_author' object fallback
                  default = data.get("default_author", {})
                  name = default.get("name")
                  email = default.get("email")
             
             if not name or not email:
                  raise ValueError("Must provide 'authors' list OR 'author_name'/'author_email'.")
             
             authors.append(AuthorDTO(name=name, email=email, weight=1.0))

        return ConfigDTO(
            repo_path=data["repo_path"],
            duration_str=data["duration"],
            file_patterns=data["file_patterns"],
            total_commits=total_commits,
            mode=data.get("mode", "even"),
            authors=authors,
            duration_seconds=duration_seconds
        )
    
    # Exposing AuthorDTO for type hinting externally if needed, or relying on module level
    AuthorDTO = AuthorDTO
