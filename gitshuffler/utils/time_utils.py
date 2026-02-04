import re
from datetime import timedelta

class TimeUtils:
    @staticmethod
    def parse_duration(duration_str: str) -> timedelta:
        """
        Parses a duration string like "2h", "1d 30m", "500s" into a timedelta.
        Supported units: w (weeks), d (days), h (hours), m (minutes), s (seconds).
        Raises ValueError if format is invalid.
        """
        duration_str = duration_str.lower().strip()
        
        # Regex to find all (value, unit) pairs
        # Needs to handle spaces or no spaces: "1d2h", "1d 2h"
        
        matches = re.findall(r'(\d+)\s*([wdhms])', duration_str)
        if not matches:
             # Check if it's just a raw number (assume days for backward compatibility? 
             # Or maybe just raise error to be strict. The prompt says "support user input like 2h, 35h"
             # Let's support pure integers as DAYS for Config compatibility if they pass string "7".
             # But Config parser passes int for legacy days_active.
             # If string, we expect units.
             if duration_str.isdigit():
                 return timedelta(days=int(duration_str))
             raise ValueError(f"Invalid duration format: '{duration_str}'. detailed examples: '2h', '1d 30m'")

        total_seconds = 0
        units = {
            'w': 604800,
            'd': 86400,
            'h': 3600,
            'm': 60,
            's': 1
        }
        
        for value, unit in matches:
            total_seconds += int(value) * units[unit]
            
        return timedelta(seconds=total_seconds)
