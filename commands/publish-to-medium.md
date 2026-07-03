---
description: Publish a local markdown file to Medium as an unlisted post
argument-hint: path/to/file.md
allowed-tools: ["Bash", "Read"]
---

# Publish to Medium

Publish the markdown file at the given path to Medium as an unlisted post using browser automation. If this file was published before, this **updates that same post** instead of creating a duplicate.

**File argument:** $ARGUMENTS

## Steps

1. Confirm the file path from `$ARGUMENTS`. If no path was provided, ask the user which markdown file to publish.

2. Run the publish script:
   ```bash
   cd /Users/debprakash/Documents/GitHub/publish-to-medium
   source .venv/bin/activate
   python3 scripts/publish_to_medium.py "$ARGUMENTS"
   ```
   Add `--new` to force creating a brand-new post even if this file was published before.

3. **First run only:** A browser window will open. Sign in to Medium, then the script will continue automatically. The session is saved for future runs.

4. Report the result:
   - On success: show the Medium URL of the published post, and note whether it was a new post or an update to an existing one
   - On failure: show the error message and suggest next steps

## Notes

- The script tracks which Medium post belongs to which markdown file in `~/.publish-to-medium-profile/mappings.json`, keyed by the file's resolved absolute path. This is shared across Claude Code sessions, so re-running from a different session still updates the right post.
