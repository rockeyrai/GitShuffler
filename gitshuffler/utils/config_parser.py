import json
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ConfigDTO:
    repo_path: str
    author_name: str
    author_email: str
    days_active: int
    commits_per_day_min: int
    commits_per_day_max: int
    start_date: str
    file_patterns: List[str]

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

        required_fields = [
            "repo_path", "author_name", "author_email", 
            "days_active", "commits_per_day_min", "commits_per_day_max",
            "start_date", "file_patterns"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in config: {field}")

        # Basic Validation
        if data["days_active"] < 1:
            raise ValueError("days_active must be at least 1")
        if data["commits_per_day_min"] < 0:
            raise ValueError("commits_per_day_min must be non-negative")
        if data["commits_per_day_max"] < data["commits_per_day_min"]:
            raise ValueError("commits_per_day_max must be greater than or equal to commits_per_day_min")

        return ConfigDTO(
            repo_path=data["repo_path"],
            author_name=data["author_name"],
            author_email=data["author_email"],
            days_active=data["days_active"],
            commits_per_day_min=data["commits_per_day_min"],
            commits_per_day_max=data["commits_per_day_max"],
            start_date=data["start_date"],
            file_patterns=data.get("file_patterns", [])
        )
