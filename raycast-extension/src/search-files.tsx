import { useState, useEffect } from "react";
import { List, ActionPanel, Action, showInFinder, open } from "@raycast/api";
import { execSync } from "child_process";
import { homedir } from "os";
import { join } from "path";

interface SearchResult {
  path: string;
  filename: string;
  modified: string;
  score: number;
}

const SEARCH_SCRIPT = join(
  homedir(),
  "Documents/timepass-cs/finder-search-extension/search/search.py"
);

function runSearch(query: string): SearchResult[] {
  try {
    const escapedQuery = query.replace(/"/g, '\\"');
    const output = execSync(`python3 "${SEARCH_SCRIPT}" "${escapedQuery}"`, {
      encoding: "utf-8",
      timeout: 15000,
    });
    const parsed = JSON.parse(output);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (r: SearchResult) =>
        r && typeof r.path === "string" && typeof r.filename === "string" &&
        r.path.length > 0 && r.filename.length > 0
    );
  } catch {
    return [];
  }
}

export default function Command() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setResults([]);
      return;
    }
    setIsLoading(true);
    const searchResults = runSearch(query.trim());
    setResults(searchResults);
    setIsLoading(false);
  }, [query]);

  return (
    <List
      isLoading={isLoading}
      onSearchTextChange={setQuery}
      searchBarPlaceholder="Search your files..."
      throttle
    >
      {results.map((file) => (
        <List.Item
          key={file.path}
          title={file.filename}
          subtitle={file.path.replace(/^\/Users\/[^/]+/, "~")}
          actions={
            <ActionPanel>
              <Action
                title="Reveal in Finder"
                onAction={() => showInFinder(file.path)}
              />
              <Action
                title="Open"
                onAction={() => open(file.path)}
              />
            </ActionPanel>
          }
        />
      ))}
    </List>
  );
}
