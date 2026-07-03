---
description: Publish a local markdown file to Medium as an unlisted post
argument-hint: path/to/file.md
allowed-tools: ["Bash", "Read"]
---

# Publish to Medium

Publish the markdown file at the given path to Medium as an unlisted post using browser automation.

**File argument:** $ARGUMENTS

## Steps

1. Confirm the file path from `$ARGUMENTS`. If no path was provided, ask the user which markdown file to publish.

2. Run the publish script:
   ```bash
   cd /Users/debprakash/Documents/GitHub/publish-to-medium
   source .venv/bin/activate
   python3 scripts/publish_to_medium.py "$ARGUMENTS"
   ```

3. **First run only:** A browser window will open. Sign in to Medium, then the script will continue automatically. The session is saved for future runs.

4. Report the result:
   - On success: show the Medium URL of the published post
   - On failure: show the error message and suggest next steps
