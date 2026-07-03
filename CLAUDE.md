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
4. Looks up `~/.publish-to-medium-profile/mappings.json` for a prior post published from this file's resolved path — if found, reopens that post's editor and updates it; otherwise opens a new story
5. Fills the editor with title and pasted HTML body
6. Publishes the post, then records/updates the file→post mapping

## Republishing

Re-running the script on a markdown file it has published before **updates that same post** instead of creating a duplicate — it looks up the file's resolved absolute path in `mappings.json` and reopens `https://medium.com/p/<id>/edit`. Pass `--new` to force a brand-new post instead. If the mapping is missing (e.g. the profile directory was deleted), it falls back to creating a new post.

Because the mapping lives in `~/.publish-to-medium-profile`, it's shared across any Claude Code session on this machine — publishing the same file from a different session still updates the original post.

## Known issues: fragile Medium selectors

- **Unlisted visibility**: the script may warn `Could not find Unlisted option` and publish with default visibility. Medium's publish dialog selectors need to be inspected and updated. The publish dialog opens after clicking the "Publish" button — use Playwright's `page.pause()` or take a screenshot to find the correct selectors for the Unlisted option.
- **Update button wording**: when republishing (updating an already-published post), the confirm button's label hasn't been verified against a live Medium session — `publish_unlisted` in `scripts/publish_to_medium.py` matches both "Publish" and "Update" text, but the selector may need adjustment once tested against real usage.

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
