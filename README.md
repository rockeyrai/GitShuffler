# GitShuffler

GitShuffler is a tool designed to simulate natural Git commit history by planning and executing commits based on a configuration. It helps in creating realistic commit graphs for projects.

## Installation

Since this is a Python package, you can install it in editable mode:

```bash
pip install -e .
```

## Usage

### 1. Initialize Configuration

First, generate a default configuration file in your target repository:

```bash
python3 -m gitshuffler.cli init
```

This creates `gitshuffler.json`. Edit this file to customize:
- `repo_path`: Path to the repository you want to shuffle (default is current directory `.`).
- `author_name` & `author_email`: The identity used for the commits.
- `days_active`: How many days of history to generate.
- `start_date`: The date when the commit history should start.
- `file_patterns`: Glob patterns for files to include in the commit history (e.g., `["**/*.py", "**/*.md"]`).

### 2. Preview the Plan

Before applying any changes, run the planning phase to see what commits will be generated:

```bash
python3 -m gitshuffler.cli plan
```

This will output a list of scheduled commits with timestamps and file counts, without making any changes.

### 3. Apply Commits

To execute the plan and create the actual git commits:

```bash
python3 -m gitshuffler.cli apply
```

**Tip**: You can use the `--dry-run` flag to simulate the execution sequence without writing to the git history:

```bash
python3 -m gitshuffler.cli apply --dry-run
```

## How to Test

### Running Unit Tests

The project includes unit tests for core logic. Run them using:

```bash
python3 -m unittest discover tests
```

### Manual Verification (The "Dry Run" Method)

1.  Initialize a new empty folder or use a dummy repo.
2.  Run `python3 -m gitshuffler.cli init`.
3.  Add some dummy files matching your patterns (e.g., `touch test1.py test2.py`).
4.  Run `python3 -m gitshuffler.cli plan`.
5.  Run `python3 -m gitshuffler.cli apply --dry-run`.
6.  Check the output to ensure the dates, authors, and file groupings look correct.

### Verification in a Real Repo

1.  Make sure your git status is clean.
2.  Run `python3 -m gitshuffler.cli apply`.
3.  Use `git log` to see the newly created commit history with backdated timestamps.

## Architecture

- **Planner**: deterministic scheduling of commits.
- **Chunker**: groups files into commits.
- **Engine**: orchestrates the process.
- **GitWrapper**: handles low-level git commands.
