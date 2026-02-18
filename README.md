# Smart Finder Search

A Raycast extension that wraps macOS Spotlight (`mdfind`) for cleaner, scoped file search.

## Before / After

| Before (Spotlight) | After (Smart Finder Search) |
|---|---|
| ![Spotlight search showing noisy, unfiltered results](screenshots/before-spotlight.png) | ![Smart Finder Search showing clean, ranked results](screenshots/after-extension.png) |

## Features

- **Scoped search**: Only searches directories you care about (Documents, Downloads)
- **Smart filtering**: Excludes noise like `node_modules`, `site-packages`, `.git`, etc.
- **OR search**: Typing "report pdf" finds files matching "report" OR "pdf"
- **Recency boost**: Recent files rank higher in results
- **Clean UI**: Files only, no apps or web suggestions

## Installation

### 1. Install the Raycast extension

1. Open Raycast
2. Go to Extensions → + → Import Extension
3. Select the `raycast-extension` folder from this project
4. The extension will compile and install automatically

### 2. (Optional) Install Python dependencies

The search script uses only Python standard library. No pip install needed.

## Usage

1. Open Raycast (default: ⌘ + Space)
2. Type "Search Files" to find the command
3. Start typing your search query
4. Press Enter to reveal the selected file in Finder

### Actions

| Shortcut | Action |
|----------|--------|
| Enter | Reveal in Finder |
| ⌘ + Enter | Open file |
| ⌘ + Shift + C | Copy path |

## Configuration

Edit the config file to customize search behavior:

```
finder-search-extension/search/config.json
```

### Adding directories

```json
{
  "include_directories": [
    "~/Documents",
    "~/Downloads",
    "~/Desktop",
    "~/Projects"
  ],
  ...
}
```

### Adding exclusion patterns

```json
{
  ...
  "exclude_patterns": [
    "*/site-packages/*",
    "*/.venv/*",
    "*/node_modules/*",
    "*/__pycache__/*",
    "*.app/*",
    "*/Library/*",
    "*/.Trash/*",
    "*/.git/*",
    "*/your-pattern-here/*"
  ]
}
```

Patterns use glob-style matching (fnmatch).

## How It Works

```
Raycast → Python script → mdfind → Spotlight index
                ↓
         Filter & rank
                ↓
         JSON results → Raycast UI
```

1. User types query in Raycast
2. Extension calls `search.py` with the query
3. Python script calls `mdfind` with directory scopes
4. Results are filtered against exclusion patterns
5. Results are ranked by: 60% relevance + 40% recency
6. Top 20 results returned as JSON
7. Raycast displays them in a list

## Files

```
finder-search-extension/
├── search/
│   ├── search.py      # Main search logic
│   └── config.json    # Directories + exclusions (edit this!)
├── raycast-extension/
│   ├── package.json   # Raycast manifest
│   └── src/
│       └── search-files.tsx  # UI component
└── README.md
```

## Testing the Python Script Directly

```bash
cd search
python3 search.py "your query"
```

## Troubleshooting

**No results appearing?**
- Check that the directories in `config.json` exist
- Try searching in Terminal: `mdfind -onlyin ~/Documents "your query"`
- Spotlight might need to reindex: `sudo mdutil -E /`

**Wrong files appearing?**
- Add exclusion patterns to `config.json`
- Patterns use glob matching: `*/folder-name/*` excludes any path containing that folder

**Extension not loading?**
- Make sure you're importing the `raycast-extension` folder, not the parent folder
- Check Raycast's extension logs for errors
