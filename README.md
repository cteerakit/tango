# Dota 2 Match Monitor

> **This project is no longer maintained.**
>
> This was an experiment to work with the [OpenDota](https://www.opendota.com/) API and a Discord bot. Development has moved to **[APEM](https://github.com/cteerakit/apem)**, a Windows desktop companion for Dota 2.
>
> [![GitHub Sponsors](https://img.shields.io/github/sponsors/cteerakit?style=flat-square)](https://github.com/sponsors/cteerakit)
> [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

Lightweight, free-tier match notifier for Dota 2. Polls [OpenDota](https://www.opendota.com/) on a schedule, posts rich match summaries to Discord, and tracks state in `last_match.json` via GitHub Actions.

**Monitored player:** [OpenDota profile 1088417288](https://www.opendota.com/players/1088417288)

## How it works

```text
GitHub Actions (cron, GMT+7 evening window)
→ monitor.py polls OpenDota recentMatches
→ New match? POST Discord webhook embed
→ Update last_match.json and commit [skip ci]
```

Active hours: **21:00–02:00 GMT+7** (enforced in `monitor.py`). GitHub Actions fires every **5 minutes** (scheduler minimum); outside the window the job exits immediately without calling OpenDota. Use **Run workflow** with **force** to test anytime.

## Setup

### 1. Discord webhook

1. Discord server → channel → **Edit Channel** → **Integrations** → **Webhooks**
2. **New Webhook** → copy the webhook URL

### 2. GitHub repository

1. Push this repo to GitHub (public repo = unlimited Actions minutes).
2. **Settings → Actions → General**
   - **Workflow permissions:** Read and write permissions
   - Allow GitHub Actions (all or selected workflows)
3. **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: your Discord webhook URL

No other secrets are required.

### 3. First run (bootstrap)

1. **Actions** → **Dota 2 Match Monitor** → **Run workflow**
2. Enable **Bypass GMT+7 time window** (default on)
3. Run

The first successful run sets `last_match_id` to your latest match **without** sending Discord messages. Later runs notify only for newer matches.

## Local testing

```powershell
pip install -r requirements.txt
$env:FORCE_RUN = "true"
$env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
python monitor.py
```

`DOTA_ACCOUNT_ID` defaults to `1088417288` if unset.

## Configuration

| Variable | Required | Default |
|----------|----------|---------|
| `DISCORD_WEBHOOK_URL` | Yes (for notifications) | — |
| `DOTA_ACCOUNT_ID` | No | `1088417288` |
| `STATE_FILE` | No | `last_match.json` |
| `FORCE_RUN` | No | `false` |

OpenDota is used without an API key (~60 requests/minute anonymous tier).

## Discord message format

Each new match sends an embed with:

- Victory/Defeat and hero name
- K/D/A
- Match duration and match ID
- Link to OpenDota match page
- Hero portrait thumbnail

## Files

| File | Purpose |
|------|---------|
| `monitor.py` | Polling, time guard, Discord payloads |
| `last_match.json` | Last processed `match_id` (updated by Actions) |
| `.github/workflows/dota-monitor.yml` | Schedule + manual trigger + state commit |

## Notes

- Matches outside the evening window are reported on the first poll inside the window.
- Scheduled runs may start several minutes late during high GitHub load.
- Outside 21:00–02:00 GMT+7 you will still see **Scheduled** runs in Actions; logs will say `Outside active window` (expected).
- Ensure the workflow is **enabled**: Actions → Dota 2 Match Monitor → **Enable workflow** (disabled workflows do not schedule).
- Do not commit your Discord webhook URL to the repository.

## Sponsor

If you find this work useful, consider [sponsoring on GitHub](https://github.com/sponsors/cteerakit).

## License

This project is licensed under the [MIT License](LICENSE).
