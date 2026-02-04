import argparse
import sys
import json
import os
from gitshuffler.core.engine import Engine
from gitshuffler.utils.config_parser import ConfigDTO

def main():
    parser = argparse.ArgumentParser(description="GitShuffler - Simulate natural git history")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    parser_init = subparsers.add_parser("init", help="Generate a default configuration file")

    # plan
    parser_plan = subparsers.add_parser("plan", help="Preview the commit plan without executing")

    # apply
    parser_apply = subparsers.add_parser("apply", help="Apply the plan to the repository")
    parser_apply.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying git history")

    args = parser.parse_args()

    if args.command == "init":
        do_init()
    elif args.command == "plan":
        do_plan()
    elif args.command == "apply":
        do_apply(args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)

def do_init():
    target = "gitshuffler.json"
    if os.path.exists(target):
        print(f"Error: {target} already exists.")
        sys.exit(1)
    
    # We can read the template we created in root or just dump a dict
    # Since we can't easily import the template file text, let's just write the default dict again
    # or better, use the one we created in root if we are in root.
    # But this CLI might be installed. Code duplication is safer for standalone tool.
    
    default_config = {
        "repo_path": ".",
        "authors": [
            {
                "name": "Alice",
                "email": "alice@example.com",
                "weight": 0.5
            },
            {
                "name": "Bob",
                "email": "bob@example.com",
                "weight": 0.5
            }
        ],
        "default_author": {
            "name": "Ghost Writer",
            "email": "ghost@example.com"
        },
        "days_active": 7,
        "commits_per_day_min": 1,
        "commits_per_day_max": 5,
        "start_date": "2023-01-01",
        "file_patterns": ["**/*.py", "**/*.md", "**/*.txt"]
    }
    
    with open(target, "w") as f:
        json.dump(default_config, f, indent=4)
        
    print(f"Generated {target}")

def do_plan():
    try:
        engine = Engine()
        manifest = engine.plan()
        
        print(f"Generated plan with {len(manifest)} commits.")
        print("-" * 40)
        for action in manifest:
            print(f"Time:   {action.timestamp}")
            print(f"Author: {action.author_name} <{action.author_email}>")
            print(f"Files:  {len(action.files)}")
            print(f"Msg:    {action.message.splitlines()[0]}...")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def do_apply(dry_run: bool):
    try:
        engine = Engine()
        manifest = engine.plan() # Re-plan to get fresh manifest
        engine.apply(manifest, dry_run=dry_run)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
