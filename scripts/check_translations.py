"""Assert that strings.json and translations/en.json share the same key structure."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _collect_paths(obj: object, prefix: str = "") -> set[str]:
    """Return every leaf key path in a nested dict as dot-separated strings."""
    if not isinstance(obj, dict):
        return {prefix} if prefix else set()
    paths: set[str] = set()
    for key, value in obj.items():
        child = f"{prefix}.{key}" if prefix else key
        paths |= _collect_paths(value, child)
    return paths


def main() -> None:
    root = Path(__file__).parent.parent / "custom_components" / "chores"
    strings = json.loads((root / "strings.json").read_text())
    translations = json.loads((root / "translations" / "en.json").read_text())

    strings_paths = _collect_paths(strings)
    translations_paths = _collect_paths(translations)

    only_in_strings = strings_paths - translations_paths
    only_in_translations = translations_paths - strings_paths

    if only_in_strings or only_in_translations:
        if only_in_strings:
            print("Keys in strings.json but not translations/en.json:")
            for path in sorted(only_in_strings):
                print(f"  {path}")
        if only_in_translations:
            print("Keys in translations/en.json but not strings.json:")
            for path in sorted(only_in_translations):
                print(f"  {path}")
        sys.exit(1)

    print("strings.json and translations/en.json are in sync.")


if __name__ == "__main__":
    main()
