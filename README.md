# Dota 2 Match Monitor

Lightweight, free-tier match notifier for Dota 2. Polls [OpenDota](https://www.opendota.com/) on a schedule, posts rich match summaries to Discord, and tracks state in `last_match.json` via GitHub Actions.

**Monitored player:** [OpenDota profile 1088417288](https://www.opendota.com/players/1088417288)

## How it works

```text
GitHub Actions (cron, GMT+7 evening window)
    → monitor.py polls OpenDota recentMatches
    → New match? POST Discord webhook embed
    → Update last_match.json and commit [skip ci]
```

Active hours: **21:00–02:00 GMT+7**. The workflow cron runs every **5 minutes** during the equivalent UTC window (14:00–18:55 UTC)—GitHub’s minimum supported schedule interval. The script enforces the window; manual runs can bypass it.

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
- Scheduled runs may start several minutes late during high GitHub load (even with a 5-minute cron).
- Do not commit your Discord webhook URL to the repository.
