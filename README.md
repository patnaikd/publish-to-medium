# publish-to-medium

A Claude Code plugin that publishes local markdown files to Medium as unlisted posts using browser automation. No API token required.

## How it works

The plugin uses Playwright to drive a Chromium browser window, convert your markdown to HTML, fill in Medium's story editor, and publish. On the first run you sign in to Medium manually; after that the session is saved and future runs are fully automatic.

## Installation

**1. Clone the repo and set up the Python environment:**

```bash
git clone https://github.com/debprakash/publish-to-medium
cd publish-to-medium
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

**2. Install the Claude Code plugin:**

```bash
# Add the local marketplace (one-time)
claude plugin marketplace add ~/.claude/local-plugins

# Install the plugin
claude plugin install publish-to-medium@local-plugins
```

> The local marketplace is set up with a symlink: `~/.claude/local-plugins/publish-to-medium` → this repo. If you cloned to a different path, update the symlink:
> ```bash
> ln -sf /path/to/publish-to-medium ~/.claude/local-plugins/publish-to-medium
> ```

**3. Restart Claude Code.** The plugin loads on startup.

## Usage

### Natural language (via skill)

Just tell Claude what you want:

```
Publish ~/articles/my-post.md to Medium
Post this file to Medium: ~/drafts/essay.md
Publish the file to Medium
```

### Slash command

```
/publish-to-medium ~/articles/my-post.md
```

### Direct script

```bash
source .venv/bin/activate
python3 scripts/publish_to_medium.py ~/articles/my-post.md
```

## First run

A Chromium browser window will open and navigate to medium.com. Sign in to your Medium account. Once logged in, the script continues automatically and the session is saved to `~/.publish-to-medium-profile` for all future runs.

## Markdown formatting

- **Title** is extracted from the first `# H1` heading. If none exists, the filename is used (hyphens and underscores replaced with spaces, title-cased).
- The H1 line is removed from the body before publishing to avoid duplication.
- Markdown is converted to HTML via the `markdown` library with `extra`, `fenced_code`, and `tables` extensions.
- Posts are always published as **Unlisted** — visible to anyone with the link, not listed on your Medium profile.

## Resetting the session

Delete the saved browser profile to force a fresh login:

```bash
rm -rf ~/.publish-to-medium-profile
```

## Project structure

```
publish-to-medium/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── commands/
│   └── publish-to-medium.md # /publish-to-medium slash command
├── skills/
│   └── publish-to-medium/
│       └── SKILL.md         # Natural language trigger
├── scripts/
│   └── publish_to_medium.py # Playwright automation script
└── requirements.txt
```
