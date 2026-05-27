#!/usr/bin/env python3
"""Poll OpenDota for new Dota 2 matches and notify Discord via webhook."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import requests

OPENDOTA_BASE = "https://api.opendota.com/api"
DEFAULT_ACCOUNT_ID = "1088417288"
STATE_FILE = Path(os.environ.get("STATE_FILE", "last_match.json"))
# GMT+7 (no DST); fixed offset avoids tzdata on Windows runners
GMT7 = timezone(timedelta(hours=7))
WINDOW_START = time(21, 0)
WINDOW_END = time(2, 0)
STEAM_CDN = "https://cdn.cloudflare.steamstatic.com"
REQUEST_TIMEOUT = 30


def in_active_window(now: datetime | None = None) -> bool:
    """True when local time is between 21:00 and 02:00 GMT+7 (cross-midnight)."""
    now = now or datetime.now(GMT7)
    t = now.timetz().replace(tzinfo=None)
    return t >= WINDOW_START or t < WINDOW_END


def should_bypass_time_guard() -> bool:
    return os.environ.get("FORCE_RUN", "").lower() in ("1", "true", "yes")


def mark_state_changed() -> None:
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write("STATE_CHANGED=true\n")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_match_id": None, "updated_at": None}
    with STATE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_state(last_match_id: int) -> None:
    payload = {
        "last_match_id": last_match_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    mark_state_changed()


def opendota_get(path: str) -> requests.Response:
    url = f"{OPENDOTA_BASE}{path}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def fetch_recent_matches(account_id: str) -> list[dict]:
    data = opendota_get(f"/players/{account_id}/recentMatches").json()
    if not isinstance(data, list):
        raise ValueError("Unexpected recentMatches response")
    return data


def fetch_heroes() -> dict[int, dict]:
    heroes = opendota_get("/heroes").json()
    return {hero["id"]: hero for hero in heroes}


def hero_image_url(hero: dict) -> str:
    img_path = hero.get("img", "")
    if img_path.startswith("/"):
        return f"{STEAM_CDN}{img_path}"
    name = hero.get("name", "").replace("npc_dota_hero_", "")
    return f"{STEAM_CDN}/apps/dota2/images/dota_react/heroes/{name}.png"


def format_duration(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def format_kda(kills: int, deaths: int, assists: int) -> str:
    return f"**{kills} / {deaths} / {assists}** KDA"


def player_won(match: dict) -> bool:
    is_radiant = match["player_slot"] < 128
    radiant_win = bool(match["radiant_win"])
    return radiant_win if is_radiant else not radiant_win


def build_discord_payload(match: dict, hero: dict) -> dict:
    won = player_won(match)
    hero_name = hero.get("localized_name", "Unknown Hero")
    match_id = match["match_id"]
    match_url = f"https://www.opendota.com/matches/{match_id}"

    kills = match.get("kills", 0)
    deaths = match.get("deaths", 0)
    assists = match.get("assists", 0)
    duration = format_duration(match.get("duration", 0))

    result = "Victory" if won else "Defeat"
    color = 0x57F287 if won else 0xED4245

    embed: dict = {
        "title": f"{result} — {hero_name}",
        "description": format_kda(kills, deaths, assists),
        "url": match_url,
        "color": color,
        "thumbnail": {"url": hero_image_url(hero)},
        "fields": [
            {"name": "Duration", "value": duration, "inline": True},
            {"name": "Match ID", "value": f"`{match_id}`", "inline": True},
        ],
        "footer": {"text": "Dota 2 Monitor · OpenDota"},
    }

    start_time = match.get("start_time")
    if start_time:
        embed["timestamp"] = datetime.fromtimestamp(
            start_time, tz=timezone.utc
        ).isoformat()

    return {"embeds": [embed]}


def post_discord(webhook_url: str, payload: dict) -> None:
    response = requests.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code >= 400:
        print(
            f"Discord webhook failed: {response.status_code} {response.text}",
            file=sys.stderr,
        )
        response.raise_for_status()


def newest_match_id(matches: list[dict]) -> int | None:
    if not matches:
        return None
    return max(m["match_id"] for m in matches)


def main() -> int:
    if not should_bypass_time_guard() and not in_active_window():
        print("Outside active window (21:00–02:00 GMT+7). Exiting.")
        return 0

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    account_id = os.environ.get("DOTA_ACCOUNT_ID", DEFAULT_ACCOUNT_ID).strip()

    if not account_id:
        print("DOTA_ACCOUNT_ID is not set.", file=sys.stderr)
        return 1

    try:
        matches = fetch_recent_matches(account_id)
        heroes = fetch_heroes()
    except requests.RequestException as exc:
        print(f"OpenDota request failed: {exc}", file=sys.stderr)
        return 1

    latest_id = newest_match_id(matches)
    if latest_id is None:
        print("No recent matches found.")
        return 0

    state = load_state()
    last_match_id = state.get("last_match_id")

    if last_match_id is None:
        save_state(latest_id)
        print(f"Bootstrap: set last_match_id to {latest_id} (no Discord notification).")
        return 0

    new_matches = sorted(
        (m for m in matches if m["match_id"] > last_match_id),
        key=lambda m: m["match_id"],
    )

    if not new_matches:
        print(f"No new matches since {last_match_id}.")
        return 0

    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is required to notify new matches.", file=sys.stderr)
        return 1

    for match in new_matches:
        hero = heroes.get(match.get("hero_id"), {})
        payload = build_discord_payload(match, hero)
        try:
            post_discord(webhook_url, payload)
        except requests.RequestException as exc:
            print(f"Failed to notify match {match['match_id']}: {exc}", file=sys.stderr)
            return 1
        print(f"Notified match {match['match_id']}.")

    save_state(new_matches[-1]["match_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
