#!/usr/bin/env python3
"""
Generate a filtered directory tree for codebase analysis.

Excludes dependency/build directories by default so agents can see
project structure without drowning in irrelevant paths.

Usage:
    python tree_structure.py --path ./src
    python tree_structure.py --path ./src --depth 3 --json
    python tree_structure.py --path ./src --exclude "node_modules,dist,.git"
"""

import argparse, fnmatch, json, os
from pathlib import Path

DEFAULT_EXCLUDES = {
    "node_modules", "vendor", "dist", "build", ".git", "__pycache__",
    ".cache", ".next", ".nuxt", "target", ".gradle", "coverage", ".tox",
    ".mypy_cache", ".venv", "venv", "env", ".turbo", ".nx", ".angular",
    ".svelte-kit", ".output", ".parcel-cache", "bower_components",
    ".eggs", "*.egg-info", ".pytest_cache", ".ruff_cache",
}


def count_files(path, excludes):
    """Count non-excluded files in a directory (non-recursive)."""
    try:
        return sum(1 for f in path.iterdir()
                   if f.is_file() and f.name not in excludes)
    except PermissionError:
        return 0


def scan_tree(root, depth, excludes, current_depth=0):
    """Recursively scan directory tree, returning a nested structure."""
    if current_depth >= depth:
        return None
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    except PermissionError:
        return None

    result = {"name": root.name, "path": str(root), "children": [], "file_count": 0}
    file_count = 0

    for entry in entries:
        if entry.name in excludes or any(fnmatch.fnmatch(entry.name, pat) for pat in excludes if '*' in pat or '?' in pat):
            continue
        if entry.is_dir() and entry.name.startswith(".") and entry.name not in (".github", ".cursor", ".claude"):
            # Skip hidden directories except known useful ones (hidden files are kept)
            continue
        if entry.is_dir():
            child = scan_tree(entry, depth, excludes, current_depth + 1)
            if child:
                result["children"].append(child)
                file_count += child["file_count"]
        else:
            file_count += 1

    result["file_count"] = file_count
    return result


def format_text(node, prefix="", is_last=True, is_root=True):
    """Format tree as indented text with file counts."""
    lines = []
    connector = "" if is_root else ("└── " if is_last else "├── ")
    name = node["name"]
    count = node["file_count"]

    if node["children"]:
        lines.append(f"{prefix}{connector}{name}/ ({count} files)")
    elif not is_root:
        # Show leaf directories at depth limit with file count
        if count > 0:
            lines.append(f"{prefix}{connector}{name}/ ({count} files)")
        return lines

    child_prefix = prefix + ("" if is_root else ("    " if is_last else "│   "))
    children = node["children"]
    for i, child in enumerate(children):
        lines.extend(format_text(child, child_prefix, i == len(children) - 1, False))

    return lines


def main():
    p = argparse.ArgumentParser(description="Generate filtered directory tree")
    p.add_argument("--path", required=True, help="Directory to scan")
    p.add_argument("--depth", type=int, default=4, help="Max depth (default: 4)")
    p.add_argument("--exclude", default=None,
                   help="Comma-separated additional exclusions")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    args = p.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}")
        raise SystemExit(1)

    excludes = set(DEFAULT_EXCLUDES)
    if args.exclude:
        excludes.update(e.strip() for e in args.exclude.split(","))

    tree = scan_tree(root, args.depth, excludes)
    if not tree:
        print("Empty or inaccessible directory")
        raise SystemExit(1)

    if args.json:
        print(json.dumps(tree, indent=2))
    else:
        for line in format_text(tree):
            print(line)


if __name__ == "__main__":
    main()
