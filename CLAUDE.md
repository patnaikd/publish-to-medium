# publish-to-medium

A Claude Code plugin that publishes local markdown files to Medium as unlisted posts using Playwright browser automation.

## Running the script

Always activate the venv first:

```bash
source .venv/bin/activate
python3 scripts/publish_to_medium.py path/to/file.md
```

## Setup (first time)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## How it works

1. Extracts title from first `# H1` (falls back to filename)
2. Converts markdown body to HTML via the `markdown` library
3. Launches a persistent Playwright Chromium browser (`~/.publish-to-medium-profile`)
4. Fills Medium's story editor with title and pasted HTML body
5. Publishes the post

## Known issue: Unlisted visibility

The script currently warns `Could not find Unlisted option` and publishes with default visibility. Medium's publish dialog selectors need to be inspected and updated. The publish dialog opens after clicking the "Publish" button — use Playwright's `page.pause()` or take a screenshot to find the correct selectors for the Unlisted option.

## Plugin structure

| Path | Purpose |
|---|---|
| `scripts/publish_to_medium.py` | Main Playwright automation script |
| `commands/publish-to-medium.md` | `/publish-to-medium` slash command |
| `skills/publish-to-medium/SKILL.md` | Natural language trigger ("publish to Medium") |
| `.claude-plugin/plugin.json` | Plugin manifest |

## Session storage

The browser session is saved to `~/.publish-to-medium-profile`. Delete it to force a fresh login.

## Dependencies

Key packages in `requirements.txt`: `playwright`, `markdown`. After any `pip install`, run `pip freeze > requirements.txt`.
