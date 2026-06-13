"""Assert that strings.json and translations/en.json share identical key paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _leaf_paths(obj: object, prefix: str = "") -> set[str]:
    if not isinstance(obj, dict):
        return {prefix}
    paths: set[str] = set()
    for key, value in obj.items():
        child = f"{prefix}.{key}" if prefix else key
        paths |= _leaf_paths(value, child)
    return paths


def main() -> int:
    root = Path(__file__).parent.parent / "custom_components" / "chores"
    strings = json.loads((root / "strings.json").read_text())
    translations = json.loads((root / "translations" / "en.json").read_text())

    strings_paths = _leaf_paths(strings)
    translations_paths = _leaf_paths(translations)

    only_in_strings = strings_paths - translations_paths
    only_in_translations = translations_paths - strings_paths

    if only_in_strings:
        print("Keys in strings.json but not translations/en.json:")
        for path in sorted(only_in_strings):
            print(f"  {path}")

    if only_in_translations:
        print("Keys in translations/en.json but not strings.json:")
        for path in sorted(only_in_translations):
            print(f"  {path}")

    if only_in_strings or only_in_translations:
        return 1

    print("strings.json and translations/en.json are in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
