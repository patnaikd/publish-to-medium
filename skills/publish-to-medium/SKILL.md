---
name: publish-to-medium
description: This skill should be used when the user asks to "publish to Medium", "post this to Medium", "publish the file to Medium", "upload this article to Medium", "send this to Medium", or mentions publishing a markdown file to their Medium account.
---

# Publish to Medium

Publish a local markdown file to Medium as an unlisted post using browser automation (Playwright). No API token needed — the script uses a persistent browser session. Re-publishing a file that was already posted **updates that same post** instead of creating a duplicate.

## How It Works

1. Converts markdown to HTML
2. Opens a Playwright browser window (Chromium)
3. Logs in to Medium (first run only — session is saved to `~/.publish-to-medium-profile`)
4. Looks up the file's resolved path in `~/.publish-to-medium-profile/mappings.json` — if a prior post is found, reopens and updates it; otherwise creates a new story
5. Fills in the title and body, publishes as Unlisted, and records/updates the mapping

## Workflow

1. **Identify the file** — If the user named a file, use it. If not, ask: "Which markdown file should I publish?"

2. **Run the script:**
   ```bash
   cd /Users/debprakash/Documents/GitHub/publish-to-medium
   source .venv/bin/activate
   python3 scripts/publish_to_medium.py /path/to/file.md
   ```
   Add `--new` if the user explicitly wants a fresh post instead of updating a previous one for this file.

3. **First run only:** A browser window will open. Tell the user to sign in to Medium. The session is then saved automatically.

4. **Report the result** — Show the Medium URL on success (mentioning whether it was created or updated), or the error on failure.

## Notes

- Title is extracted from the first `# H1` in the file; falls back to the filename.
- Posts are always published as **Unlisted** (visible via direct link, not listed publicly).
- The persistent browser profile lives at `~/.publish-to-medium-profile` — deleting it clears the saved session **and** the file→post mapping (so the next publish of any file will create a new post).
- File→post mappings live in `~/.publish-to-medium-profile/mappings.json`, keyed by each markdown file's resolved absolute path, and are shared across Claude Code sessions on this machine.
- Script: `scripts/publish_to_medium.py` in the plugin directory.
