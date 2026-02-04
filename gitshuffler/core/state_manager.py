import json
import os
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Optional, Any
from gitshuffler.core.planner import CommitAction

STATE_FILE = ".gitshuffler_state.json"

@dataclass
class ExecutionState:
    manifest_hash: str
    last_applied_index: int
    total_commits: int
    is_complete: bool
    manifest_data: List[dict] # Serialized manifest

class StateManager:
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file

    def _serialize_manifest(self, manifest: List[CommitAction]) -> List[dict]:
        return [{
            "author_name": a.author_name,
            "author_email": a.author_email,
            "timestamp": a.timestamp.isoformat(),
            "files": a.files,
            "message": a.message
        } for a in manifest]

    def _deserialize_manifest(self, data: List[dict]) -> List[CommitAction]:
        from datetime import datetime
        return [CommitAction(
            author_name=d["author_name"],
            author_email=d["author_email"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            files=d["files"],
            message=d["message"]
        ) for d in data]

    def _compute_manifest_hash(self, manifest: List[CommitAction]) -> str:
        """Computes a deterministic hash of the manifest content."""
        # We can just hash the serialized json string for consistency
        data = self._serialize_manifest(manifest)
        # Sort to ensure order? Manifest order matters for execution!
        # So we should NOT sort the list, but we can rely on json.dumps being deterministic if we sort keys.
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def load_state(self) -> Optional[ExecutionState]:
        """Loads the execution state if it exists."""
        if not os.path.exists(self.state_file):
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            return ExecutionState(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            print(f"Warning: State file {self.state_file} corrupted or invalid. Ignoring.")
            return None

    def save_state(self, state: ExecutionState):
        """Saves the execution state to disk."""
        with open(self.state_file, 'w') as f:
            json.dump(asdict(state), f, indent=2)

    def get_saved_manifest(self) -> Optional[List[CommitAction]]:
        """Returns the manifest from the saved state if available."""
        state = self.load_state()
        if state and state.manifest_data:
            return self._deserialize_manifest(state.manifest_data)
        return None

    def initialize_or_resume(self, manifest: List[CommitAction]) -> int:
        """
        Checks state and determines the next commit index to apply.
        Returns the index of the first commit to apply.
        """
        current_hash = self._compute_manifest_hash(manifest)
        saved_state = self.load_state()

        if not saved_state:
            # New execution
            self.save_state(ExecutionState(
                manifest_hash=current_hash,
                last_applied_index=-1,
                total_commits=len(manifest),
                is_complete=False,
                manifest_data=self._serialize_manifest(manifest)
            ))
            return 0

        # Existing state found check hash
        if saved_state.manifest_hash != current_hash:
             raise RuntimeError(
                 "Manifest mismatch! The current plan differs from the saved execution state.\n"
                 "To force restart, remove .gitshuffler_state.json"
             )
        
        if saved_state.is_complete:
            print("Plan already fully executed.")
            return len(manifest)

        print(f"Resuming execution from commit {saved_state.last_applied_index + 2}/{len(manifest)}...")
        return saved_state.last_applied_index + 1

    def update_progress(self, index: int, is_complete: bool = False):
        """Updates the state with the last successfully applied commit index."""
        # We need to preserve the hash and other info. 
        # Ideally we kept the state object in memory, but stateless load/save is robust too.
        saved_state = self.load_state()
        if not saved_state:
             # Should not happen if initialized properly
             return
        
        saved_state.last_applied_index = index
        saved_state.is_complete = is_complete
        self.save_state(saved_state)

    def clear(self):
        """Removes the state file (e.g. after successful dry run or explicit clean)."""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
