# 🔀 GitShuffler

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**GitShuffler** is a high-reliability CLI tool designed for developers to simulate and reconstruct natural Git commit history. Whether you are testing local CI/CD pipelines, migrating repositories with complex history requirements, or simulating realistic developer activity in a sandbox environment, GitShuffler provides a deterministic and crash-safe solution.

---

## ⚖️ Ethics, Safety & Policy Disclosure

**GitShuffler is an educational and utility tool for local repository management.** 

- **Compliance**: Users are responsible for ensuring that the use of this tool complies with the Terms of Service of any hosting provider (e.g., GitHub, GitLab, Bitbucket). 
- **Integrity**: We discourage using this tool to inflate contribution graphs or misrepresent work history on public platforms.
- **Privacy**: GitShuffler operates entirely locally and does not transmit data to external services.
- **History Safety**: The tool includes internal safeguards (Idempotency, PID Locking, Atomic Writes) to prevent repository corruption.

---

## 🚀 Key Features

- **🛡️ Crash-Safe Resume**: Interrupted sessions (e.g., system crash, Ctrl+C) can be resumed exactly where they left off using persistent state tracking.
- **🕒 Human-Readable Scheduling**: Define history spans using natural language like `"2h 30m"` or `"15d"`.
- **👥 Multi-Author Simulation**: Shuffle commits across multiple developer identities with weighted probability.
- **⚡ High-Performance Batching**: Efficiently handles repositories with 100,000+ files using batched Git operations.
- **🔒 Production Hardening**: Feature-set includes Atomic state writes, PID locking, and automated pre-flight safety checks (HEAD integrity, dirty-repo detection).

---

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/rockeyrai/GitShuffler.git
cd GitShuffler

# Install in editable mode
pip install -e .
```

---

## 📖 Usage Guide

### 1. Initialize
Generate a configuration template in your target repository:
```bash
python3 -m gitshuffler.cli init
```

### 2. Configure
Edit the generated `gitshuffler.json`. See the [Configuration Reference](#configuration-reference) below.

### 3. Plan & Preview
Generate a deterministic execution plan without modifying history:
```bash
python3 -m gitshuffler.cli plan
```

### 4. Apply (or Resume)
Execute the plan. If interrupted, running this again will resume automatically.
```bash
python3 -m gitshuffler.cli apply

# Simulated dry-run
python3 -m gitshuffler.cli apply --dry-run
```

---

## ⚙️ Configuration Reference

The `gitshuffler.json` file is the brain of the operation. Below are the supported fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `repo_path` | `string` | Absolute or relative path to the target Git repository. |
| `start_date` | `string` | The point in time to begin history (Format: `YYYY-MM-DD`). |
| `duration` | `string` | The length of the history window (e.g., `"2d"`, `"5h"`, `"30m"`). **Supersedes `days_active`.** |
| `days_active` | `int` | Legacy field for duration in days. |
| `commits_per_day_min` | `int` | Minimum commits to generate per 24h window. |
| `commits_per_day_max` | `int` | Maximum commits to generate per 24h window. |
| `file_patterns` | `list` | Glob patterns to include in shuffling (e.g., `["**/*.py", "docs/*.md"]`). |
| `authors` | `list` | List of author objects `{"name": "...", "email": "...", "weight": 0.5}`. |
| `author_name` | `string` | Fallback author name if `authors` list is empty. |
| `author_email` | `string` | Fallback author email if `authors` list is empty. |

### Example Multi-Author Config
```json
{
  "duration": "7d",
  "start_date": "2024-01-01",
  "authors": [
    { "name": "Alice Developer", "email": "alice@company.com", "weight": 0.7 },
    { "name": "Bob Reviewer", "email": "bob@company.com", "weight": 0.3 }
  ],
  "file_patterns": ["src/**/*.ts", "package.json"]
}
```

---

## 📂 Internal Safety & Reliability

When you run `apply`, GitShuffler creates internal metadata to ensure stability:

- **`.gitshuffler_state.json`**: Tracks the current progress and manifest hash. **Do not modify** if you intend to resume an interrupted run.
- **`.gitshuffler.lock`**: A PID file that prevents multiple instances from corrupting the same repository concurrently.
- **Pre-flight Check**: The tool validates repository cleanliness and ensures you aren't in a detached HEAD state (unless warned).

---

## 🧪 Testing

We value reliability. To run the test suite:
```bash
python3 -m unittest discover tests
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
