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
        required_fields = [
            "repo_path", "days_active", 
            "commits_per_day_min", "commits_per_day_max",
            "start_date", "file_patterns"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in config: {field}")

        # Handle Author Configuration
        # If "authors" is present, validate it.
        # If not, ensure "author_name" and "author_email" exist.
        
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
            
            # Validate weights strictly if provided
            # If weights are all 0, we might auto-distribute? The prompt says "Validate weights sum to 1.0"
            if not (0.99 <= total_weight <= 1.01):
                 raise ValueError(f"Author weights must sum to 1.0 (got {total_weight})")
        
        else:
            # Fallback to single author
            if not default_author_name or not default_author_email:
                # If neither list nor single vals exist
                if "default_author" in data:
                    default = data["default_author"]
                    default_author_name = default.get("name")
                    default_author_email = default.get("email")

            if not default_author_name or not default_author_email:
                 raise ValueError("Must provide either 'authors' list or 'author_name'/'author_email' (or 'default_author')")
            
            # Construct a single author with weight 1.0 for the Planner to use uniformly
            authors.append(AuthorDTO(name=default_author_name, email=default_author_email, weight=1.0))

        # Basic Validation
        if data["days_active"] < 1:
            raise ValueError("days_active must be at least 1")
        if data["commits_per_day_min"] < 0:
            raise ValueError("commits_per_day_min must be non-negative")
        if data["commits_per_day_max"] < data["commits_per_day_min"]:
            raise ValueError("commits_per_day_max must be greater than or equal to commits_per_day_min")

        return ConfigDTO(
            repo_path=data["repo_path"],
            author_name=default_author_name if default_author_name else authors[0].name,
            author_email=default_author_email if default_author_email else authors[0].email,
            days_active=data["days_active"],
            commits_per_day_min=data["commits_per_day_min"],
            commits_per_day_max=data["commits_per_day_max"],
            start_date=data["start_date"],
            file_patterns=data.get("file_patterns", []),
            authors=authors
        )
