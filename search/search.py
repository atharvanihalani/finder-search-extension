#!/usr/bin/env python3
"""
Smart Finder Search - wraps mdfind with scoping, filtering, and ranking.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

def load_config():
    """Load configuration from config.json in the same directory as this script."""
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.json"

    if not config_path.exists():
        return {
            "include_directories": ["~/Documents", "~/Downloads"],
            "exclude_patterns": []
        }

    with open(config_path) as f:
        return json.load(f)


def expand_directories(directories):
    """Expand ~ in directory paths."""
    return [os.path.expanduser(d) for d in directories]


def build_mdfind_command(query, directories):
    """Build the mdfind command with -onlyin flags."""
    cmd = ["mdfind"]

    for directory in directories:
        cmd.extend(["-onlyin", directory])

    # Transform space-separated words to OR search
    # "word1 word2" becomes "word1 | word2"
    words = query.split()
    if len(words) > 1:
        or_query = " | ".join(words)
    else:
        or_query = query

    cmd.append(or_query)
    return cmd


def matches_exclusion(path, patterns):
    """Check if a path matches any exclusion pattern."""
    for pattern in patterns:
        if fnmatch(path, pattern):
            return True
    return False


def matches_filename_exclusion(filename, exclusions):
    """Check if a filename matches any exclusion (supports wildcards)."""
    for exclusion in exclusions:
        if fnmatch(filename, exclusion):
            return True
    return False


def get_file_info(path):
    """Get file metadata."""
    try:
        stat = os.stat(path)
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        return {
            "path": path,
            "filename": os.path.basename(path),
            "modified": modified_time.isoformat(),
            "mtime": stat.st_mtime
        }
    except OSError:
        return None


def calculate_recency_score(mtime, now):
    """
    Calculate recency score (0 to 1).
    1.0 for files modified today, decays over 30 days.
    """
    age_days = (now - mtime) / 86400  # seconds to days
    if age_days <= 0:
        return 1.0
    elif age_days >= 30:
        return 0.0
    else:
        return 1.0 - (age_days / 30)


def rank_results(files, relevance_weight=0.6, recency_weight=0.4):
    """
    Rank results combining mdfind order (relevance) with recency.
    """
    if not files:
        return []

    now = datetime.now().timestamp()
    total = len(files)

    for i, f in enumerate(files):
        # Position-based relevance (earlier in mdfind results = more relevant)
        relevance_score = 1.0 - (i / total) if total > 1 else 1.0

        # Recency score
        recency_score = calculate_recency_score(f["mtime"], now)

        # Combined score
        f["score"] = relevance_weight * relevance_score + recency_weight * recency_score

    # Sort by score descending
    files.sort(key=lambda x: x["score"], reverse=True)

    return files


def search(query, limit=20):
    """
    Main search function.
    """
    if not query or not query.strip():
        return []

    config = load_config()
    directories = expand_directories(config.get("include_directories", []))
    exclude_patterns = config.get("exclude_patterns", [])
    exclude_filenames = config.get("exclude_filenames", [])

    # Verify directories exist
    directories = [d for d in directories if os.path.isdir(d)]
    if not directories:
        return []

    # Run mdfind
    cmd = build_mdfind_command(query.strip(), directories)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        paths = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []

    # Filter and collect file info
    files = []
    for path in paths:
        if not path:
            continue

        # Check path exclusions
        if matches_exclusion(path, exclude_patterns):
            continue

        # Check filename exclusions
        filename = os.path.basename(path)
        if matches_filename_exclusion(filename, exclude_filenames):
            continue

        # Get file info
        info = get_file_info(path)
        if info:
            files.append(info)

    # Rank results
    ranked = rank_results(files)

    # Limit and clean up output
    results = []
    for f in ranked[:limit]:
        results.append({
            "path": f["path"],
            "filename": f["filename"],
            "modified": f["modified"],
            "score": round(f["score"], 3)
        })

    return results


def main():
    if len(sys.argv) < 2:
        print("[]")
        return

    query = " ".join(sys.argv[1:])
    results = search(query)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
