# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an **agent skills repository** containing skills for Claude Code and OpenClaw platforms. Skills are installed via `npx skills add` or by copying to `~/.claude/skills/` (Claude Code) or `~/.openclaw/skills/` (OpenClaw).

## Skill Structure

Each skill follows this pattern:
```
<skill-name>/
  SKILL.md       # Skill metadata (YAML frontmatter + documentation)
  scripts/       # Executable scripts (if any)
```

The SKILL.md frontmatter defines:
- `name`: Skill name (used as `/name` command)
- `description`: Trigger conditions and capability summary
- `agent_created`: Whether this was auto-generated

## xjtu-doctor-scraper Skill

### Architecture

The scraper targets XJTU First Affiliated Hospital (`http://www.dyyy.xjtu.edu.cn`). Key patterns:

| Layer | URL Pattern | Purpose |
|-------|-------------|---------|
| Main page | `/zjjs.htm` | Static HTML with ~730 doctor links |
| Dept pages | `/zjjs/{大类}/{小类}.htm` | Category pages (3-level path) - skip these |
| Doctor pages | `/zjjs/{大类}/{小类}/{医生}.htm` | Vue.js rendered, contains account_id |
| Data API | `/services/industry/patient/static/userDoctor/detailByAccount/{account_id}` | JSON response with doctor details |

### Commands

Windows requires UTF-8 encoding first:
```bash
export PYTHONIOENCODING=utf-8  # or: chcp 65001
```

Then run from `xjtu-doctor-scraper/scripts/`:
```bash
# Step 1: Parse main page -> JSON list
python scrape.py parse doctors_list.json

# Step 2: Batch crawl details (100 per batch, 5 threads)
python scrape.py batch doctors_list.json output.csv 0 100
python scrape.py batch doctors_list.json output.csv 100 100

# Step 3: Fix existing CSV fields
python scrape.py fix doctors_list.json input.csv output.csv
```

### Critical Pitfalls (from SKILL.md)

1. **Photo URL**: Use `photoShortUrl` (UUID format), NOT `doctorAccount` (numeric ID)
2. **Research field**: Use `acaTitle` (readable text), NOT `goodDirectionList` (UUID codes)
3. **Concurrency**: Low concurrency (5 threads) with 0.2s delay; high concurrency causes interruptions

## Pushing to GitHub from China

Use ghfast.top proxy for GitHub access:
```bash
# Clone/fetch public repos
git clone https://ghfast.top/https://github.com/user/repo.git

# Push private repos (requires PAT)
git remote set-url origin https://user:TOKEN@ghfast.top/https://github.com/user/repo.git
git push
git remote set-url origin https://github.com/user/repo.git  # remove token after
```