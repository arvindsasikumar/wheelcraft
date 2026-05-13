"""Profile persistence to disk. One JSON file per profile in `profiles/`."""

import json
import re
import threading
from pathlib import Path

from .profile import Profile


_VALID_NAME = re.compile(r"^[A-Za-z0-9 _.-]{1,40}$")


def safe_name(name: str) -> str:
    if not _VALID_NAME.match(name):
        raise ValueError(
            f"invalid profile name {name!r} — use letters, digits, spaces, '_', '.', '-'"
        )
    return name


class ProfileStore:
    def __init__(self, dir_path: Path) -> None:
        self.dir = dir_path
        self.dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self.dir / "_state.json"
        self._lock = threading.Lock()

        if not (self.dir / "default.json").exists():
            self.save(Profile.default("default"))

    def _path(self, name: str) -> Path:
        return self.dir / f"{safe_name(name)}.json"

    def list_names(self) -> list[str]:
        names = []
        for p in self.dir.glob("*.json"):
            if p.name.startswith("_"):
                continue
            names.append(p.stem)
        return sorted(names)

    def load(self, name: str) -> Profile:
        with self._lock:
            data = json.loads(self._path(name).read_text(encoding="utf-8"))
        return Profile.model_validate(data)

    def save(self, profile: Profile) -> None:
        path = self._path(profile.name)
        payload = profile.model_dump_json(indent=2)
        with self._lock:
            path.write_text(payload, encoding="utf-8")

    def delete(self, name: str) -> None:
        if name == "default":
            raise ValueError("cannot delete the default profile")
        with self._lock:
            self._path(name).unlink(missing_ok=True)

    def get_active_name(self) -> str:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                name = data.get("active", "default")
                if (self.dir / f"{name}.json").exists():
                    return name
            except json.JSONDecodeError:
                pass
        return "default"

    def set_active_name(self, name: str) -> None:
        safe_name(name)
        if not self._path(name).exists():
            raise FileNotFoundError(name)
        with self._lock:
            self._state_path.write_text(json.dumps({"active": name}), encoding="utf-8")
