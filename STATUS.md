# Smart Finder Search - Project Status

**Last updated:** 2026-01-28
**Status:** Minimal working version, needs feature development

---

## A) Motivation

macOS Finder/Spotlight search is frustrating despite being technically sophisticated:

1. **No control over scope** - Searches everything: system files, app bundles, Python packages, caches. You want to find YOUR documents, not a README buried in `site-packages/`.

2. **Poor ranking** - Apple's relevance algorithm is a black box. Recent files you actually care about get buried under random matches.

3. **UI clutter** - Spotlight mixes apps, web suggestions, calculator results with file search.

4. **Not fuzzy** - Typos or slight misremembering returns nothing.

### Solution

A Raycast extension that searches files using Spotlight's existing index (`mdfind`), but with:
- Scoped directories (only ~/Documents, ~/Downloads, etc.)
- Exclusion filters (no site-packages, node_modules, .app internals)
- Custom ranking (recency + match quality)
- Clean, files-only interface

### Why This Architecture

- **Wrap mdfind, don't build indexer** - Spotlight already handles file content extraction, live updates via FSEvents, and maintains an efficient index. Building our own would take weeks.
- **Raycast extension** - Provides hotkey invocation, search UI, keyboard nav, action system for free.
- **Python for search logic** - Easy to shell out to mdfind, simple JSON output, can add complexity later.

---

## B) What's Been Built

### Project Structure

```
finder-search-extension/
├── search/
│   ├── search.py           # Main search logic (working)
│   ├── config.json         # Directories + exclusions (working)
│   └── test_search.py      # Unit tests (32 tests, all passing)
├── raycast-extension/
│   ├── package.json
│   ├── tsconfig.json
│   ├── assets/
│   │   └── extension-icon.png
│   └── src/
│       └── search-files.tsx  # Raycast UI (minimal working version)
├── finder-search-handoff.md  # Original design doc
├── STATUS.md                 # This file
└── README.md                 # User documentation
```

### Python Search Script (`search/search.py`)

**Working features:**
- Accepts search query as CLI argument
- Loads config from `config.json` (same directory)
- Calls `mdfind` with `-onlyin` flags for scoped directories
- **OR search**: "word1 word2" becomes "word1 | word2" for mdfind
- Filters results against exclusion patterns (fnmatch glob matching)
- Ranks results: `score = 0.6 * relevance + 0.4 * recency`
  - Relevance = position in mdfind results (earlier = better)
  - Recency = 1.0 for today, decays to 0 over 30 days
- Returns top 20 results as JSON

**Test coverage:** 38 unit tests covering all core functions.

### Configuration (`search/config.json`)

```json
{
  "include_directories": ["~/Documents", "~/Downloads"],
  "exclude_patterns": [
    "*/site-packages/*", "*/.venv/*", "*/venv/*", "*/node_modules/*",
    "*/__pycache__/*", "*.app/*", "*/Library/*", "*/.Trash/*", "*/.git/*",
    "*/.tox/*", "*/.mypy_cache/*", "*/.pytest_cache/*", "*/recordings/*",
    "*/.cache/*", "*/Caches/*", "*/build/*", "*/dist/*", "..."
  ],
  "exclude_filenames": [
    "meta.json", "package-lock.json", "yarn.lock", ".DS_Store",
    "*.pyc", "*.log", "*.tmp", "..."
  ]
}
```

**New in latest version:** `exclude_filenames` - filters out specific filenames (supports wildcards).

### Raycast Extension (`raycast-extension/`)

**Working features:**
- Search bar with debouncing (Raycast's `throttle`)
- Calls Python script, displays results as list
- Actions: "Reveal in Finder" (Enter), "Open"

**Key technical issue resolved:**
- Raycast API v1.50.0 has different action component API than current versions
- `Action.ShowInFinder` doesn't work - must use generic `Action` with `onAction` callback
- The newer API requires Node 22.14+ which wasn't available

**Current code uses:**
```tsx
<Action
  title="Reveal in Finder"
  onAction={() => showInFinder(file.path)}
/>
```

Instead of the newer (broken on v1.50.0):
```tsx
<Action.ShowInFinder path={file.path} />
```

---

## C) Features To Build

### Priority 1: Keyboard Shortcut - DONE

**Status:** User configuration, not code. Set up in Raycast Preferences → Extensions → Smart Finder Search → Hotkey.

### Priority 2: Better Filtering - DONE

**Status:** Implemented. Added:
- 25+ path exclusion patterns (venv, cache dirs, build dirs, recordings, etc.)
- New `exclude_filenames` feature for filtering specific files (`meta.json`, `*.pyc`, `*.log`, etc.)

**If still seeing junk:** Edit `search/config.json`:
- Path patterns: `*/folder/*` matches any path containing that folder
- Filename patterns: `*.log`, `.eslintrc*` (wildcards supported)

**Possible future improvements:**
- Raycast preferences UI for exclusions
- Exclude by file size

### Priority 3: Better Ranking & Fuzzy Search

**Problem:**
- Current ranking is basic (mdfind order + recency)
- No fuzzy matching - typos return nothing

**Possible solutions:**

**For better ranking:**
- Boost exact filename matches
- Boost matches in file name vs. content
- Consider file type (PDFs, docs more important than .json, .log)
- Learn from user selections (track what gets opened)

**For fuzzy search:**
- mdfind doesn't support fuzzy matching natively
- Options:
  1. **Filename fuzzy:** After mdfind returns results, also search filenames with Levenshtein distance
  2. **Query expansion:** If few results, try removing characters or using wildcards
  3. **Build secondary index:** Use something like `fzf` or a Python fuzzy library on filenames

**Trade-off:** Fuzzy on file contents would require our own index (complex). Fuzzy on filenames only is much easier and probably sufficient.

---

## Technical Notes for Future Development

### Running the Dev Server

```bash
cd raycast-extension
npm run dev
```

This watches for changes and auto-rebuilds. Keep it running while developing.

### Testing Python Changes

```bash
cd search
python3 search.py "your query"        # Test search
python3 -m unittest test_search -v    # Run tests
```

### Raycast API Compatibility

We're using `@raycast/api@1.50.0` because newer versions require Node 22.14+. If Node is upgraded, consider updating the API version for access to newer components like `Action.ShowInFinder`.

### Debug Logging

If issues occur, add this to the TypeScript:
```typescript
import { writeFileSync } from "fs";
const DEBUG_LOG = join(homedir(), "raycast-search-debug.log");
function debugLog(msg: string, data?: unknown) {
  writeFileSync(DEBUG_LOG, `${new Date().toISOString()} - ${msg}: ${JSON.stringify(data)}\n`, { flag: "a" });
}
```

Then check `~/raycast-search-debug.log`.

---

## Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `search/search.py` | Core search logic | Working |
| `search/config.json` | User configuration | Working |
| `search/test_search.py` | Unit tests | 32 passing |
| `raycast-extension/src/search-files.tsx` | Raycast UI | Minimal working |
| `finder-search-handoff.md` | Original design doc | Reference |
| `README.md` | User documentation | Complete |

---

## Quick Start for New Session

1. **Understand the architecture:** User types in Raycast → TypeScript calls Python script → Python calls mdfind → filters/ranks → returns JSON → TypeScript displays in Raycast

2. **The Python script works well** - 32 tests passing, core logic is solid

3. **Raycast API quirks** - Use `Action` with `onAction`, not `Action.ShowInFinder` (API version issue)

4. **Main work needed:** Better filtering and fuzzy search in the Python layer
