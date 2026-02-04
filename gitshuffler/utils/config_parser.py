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
    # Legacy/Default single author fields (kept for backward compatibility/fallback)
    author_name: str
    author_email: str
    
    days_active: int
    commits_per_day_min: int
    commits_per_day_max: int
    start_date: str
    file_patterns: List[str]
    
    # New multi-author fields
    authors: List[AuthorDTO]
    
    # New Time Model
    duration_seconds: float = 0.0 # Calculated from days_active or duration string

class ConfigParser:
    @staticmethod
    def parse(config_path: str) -> ConfigDTO:
        """
        Parses the JSON configuration file and returns a ConfigDTO object.
        Raises ValueError if the config is invalid.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

        # Required fields for backward compatibility
        # We now accept EITHER days_active OR duration (or both, duration wins)
        # But for strictly required, we check existence specially below.
        required_fields = [
            "repo_path", 
            "commits_per_day_min", "commits_per_day_max",
            "start_date", "file_patterns"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in config: {field}")

        # Time Configuration Logic
        from gitshuffler.utils.time_utils import TimeUtils
        
        duration_seconds = 0.0
        
        if "duration" in data:
             try:
                 td = TimeUtils.parse_duration(data["duration"])
                 duration_seconds = td.total_seconds()
             except ValueError as e:
                 raise ValueError(f"Invalid 'duration' in config: {e}")
        elif "days_active" in data:
             if data["days_active"] < 1:
                 raise ValueError("days_active must be at least 1")
             # Convert days to seconds: days * 24 * 3600
             # Note: The old Planner simulated 9am-6pm. We should respect that implicit expectation 
             # if using days? Or just treat it as raw time?
             # To be safe and precise: days_active usually meant "Total span in days".
             # Let's convert to seconds directly.
             duration_seconds = data["days_active"] * 86400
        else:
             raise ValueError("Must provide either 'duration' or 'days_active' in config.")

        # Basic Validation
        if data["commits_per_day_min"] < 0:
            raise ValueError("commits_per_day_min must be non-negative")
        if data["commits_per_day_max"] < data["commits_per_day_min"]:
            raise ValueError("commits_per_day_max must be greater than or equal to commits_per_day_min")

        # Handle Author Configuration
        authors: List[AuthorDTO] = []
        default_author_name = data.get("author_name")
        default_author_email = data.get("author_email")

        if "authors" in data and data["authors"]:
            raw_authors = data["authors"]
            total_weight = 0.0
            for a in raw_authors:
                if "name" not in a or "email" not in a:
                    raise ValueError("Each author in 'authors' must have 'name' and 'email'")
                weight = a.get("weight", 0.0)
                total_weight += weight
                authors.append(AuthorDTO(name=a["name"], email=a["email"], weight=weight))
            
            if not (0.99 <= total_weight <= 1.01):
                 raise ValueError(f"Author weights must sum to 1.0 (got {total_weight})")
        
        else:
            if not default_author_name or not default_author_email:
                if "default_author" in data:
                    default = data["default_author"]
                    default_author_name = default.get("name")
                    default_author_email = default.get("email")

            if not default_author_name or not default_author_email:
                 raise ValueError("Must provide either 'authors' list or 'author_name'/'author_email'")
            
            authors.append(AuthorDTO(name=default_author_name, email=default_author_email, weight=1.0))

        return ConfigDTO(
            repo_path=data["repo_path"],
            author_name=default_author_name if default_author_name else authors[0].name,
            author_email=default_author_email if default_author_email else authors[0].email,
            days_active=data.get("days_active", int(duration_seconds // 86400)), # fallback for legacy read
            commits_per_day_min=data["commits_per_day_min"],
            commits_per_day_max=data["commits_per_day_max"],
            start_date=data["start_date"],
            file_patterns=data.get("file_patterns", []),
            authors=authors,
            duration_seconds=duration_seconds
        )
