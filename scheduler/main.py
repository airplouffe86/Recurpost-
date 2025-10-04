import os
import time
import random
from datetime import datetime, timedelta, time as dtime
import requests

# Base URLs for our internal services. These should be passed in via environment variables in docker-compose.
API_BASE = os.environ.get("API_BASE", "http://api:8000")
VARIANT_BASE = os.environ.get("VARIANT_BASE", "http://variant-api:8000")
IG_PUBLISH_BASE = os.environ.get("IG_PUBLISH_BASE", "http://ig-publisher:8000")
TT_PUBLISH_BASE = os.environ.get("TT_PUBLISH_BASE", "http://tt-publisher:8000")
YT_PUBLISH_BASE = os.environ.get("YT_PUBLISH_BASE", "http://yt-publisher:8000")
POSTS_PER_DAY = int(os.environ.get("POSTS_PER_DAY", 3))
JITTER_MINUTES = int(os.environ.get("JITTER_MINUTES", 15))


def log(message: str) -> None:
    print(f"[scheduler] {datetime.utcnow().isoformat()} {message}")


def fetch_json(url: str) -> list:
    """Helper to fetch JSON and handle errors."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log(f"Error fetching {url}: {e}")
        return []


def pick_random_caption(captions: list[dict], platform: str) -> str | None:
    filtered = [c for c in captions if c.get("platform") == platform]
    if not filtered:
        return None
    return random.choice(filtered)["body"]


def schedule_for_account(account: dict) -> None:
    acc_id = account["id"]
    acc_network = account.get("network")
    acc_token = account.get("access_token")
    if not acc_token:
        log(f"Account {acc_id} missing access token, skipping.")
        return
    # Fetch schedule times for this account
    schedules = fetch_json(f"{API_BASE}/schedules/{acc_id}")
    if not schedules:
        log(f"No schedules found for account {acc_id}")
        return
    # Flatten all times; pick up to POSTS_PER_DAY times
    times_strs: list[str] = []
    for sched in schedules:
        times_strs.extend(sched.get("post_times", []))
    times_strs = times_strs[:POSTS_PER_DAY]
    # Fetch libraries and items
    libs = fetch_json(f"{API_BASE}/libraries")
    if not libs:
        log("No libraries defined")
        return
    # For now pick the first library
    library = libs[0]
    items = fetch_json(f"{API_BASE}/libraries/{library['id']}/items")
    if not items:
        log("No items in library")
        return
    for tstr in times_strs:
        # parse HH:MM format
        try:
            hour, minute = map(int, tstr.split(":"))
        except Exception:
            log(f"Invalid time format {tstr} for schedule")
            continue
        # Compute scheduled datetime today
        scheduled_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        # If the time has already passed today, schedule for tomorrow
        if scheduled_time < datetime.now():
            scheduled_time = scheduled_time + timedelta(days=1)
        # Add jitter
        jitter = random.randint(-JITTER_MINUTES, JITTER_MINUTES)
        scheduled_time = scheduled_time + timedelta(minutes=jitter)
        # Determine sleep duration
        delta = (scheduled_time - datetime.now()).total_seconds()
        if delta > 0:
            log(f"Sleeping for {delta/60:.2f} minutes until next post for account {acc_id}")
            time.sleep(delta)
        # Pick random library item
        item = random.choice(items)
        captions = fetch_json(f"{API_BASE}/captions/{item['id']}")
        caption = pick_random_caption(captions, acc_network)
        if caption is None:
            caption = ""  # Fallback to empty caption
        # Generate variant for this platform
        variant_req = {"file_url": item["master_url"], "platform": acc_network}
        try:
            vr = requests.post(f"{VARIANT_BASE}/variant", json=variant_req, timeout=300)
            vr.raise_for_status()
            variant_url = vr.json().get("cdn_url")
        except Exception as e:
            log(f"Variant generation failed for account {acc_id}: {e}")
            continue
        # Publish according to network
        if acc_network == "instagram":
            payload = {
                "ig_user_id": account["external_user_id"],
                "video_url": variant_url,
                "caption": caption,
                "access_token": acc_token,
            }
            pub_url = f"{IG_PUBLISH_BASE}/publish"
        elif acc_network == "tiktok":
            payload = {
                "user_access_token": acc_token,
                "video_url": variant_url,
                "title": caption or item.get("title", ""),
            }
            pub_url = f"{TT_PUBLISH_BASE}/publish"
        elif acc_network == "youtube":
            payload = {
                "oauth_access_token": acc_token,
                "file_url": variant_url,
                "title": caption or item.get("title", ""),
                "description": caption or item.get("title", ""),
                "privacy": "public",
            }
            pub_url = f"{YT_PUBLISH_BASE}/publish"
        else:
            log(f"Unsupported network {acc_network} for account {acc_id}")
            continue
        try:
            pr = requests.post(pub_url, json=payload, timeout=300)
            # Do not raise on status; just log response
            log(f"Published for account {acc_id}: status {pr.status_code}, body {pr.text}")
        except Exception as e:
            log(f"Publish failed for account {acc_id}: {e}")


def main_loop():
    log("Scheduler starting main loop")
    while True:
        accounts = fetch_json(f"{API_BASE}/accounts")
        if not accounts:
            log("No accounts defined; sleeping 10 minutes")
            time.sleep(600)
            continue
        # For each account, schedule posts sequentially; this naive approach sleeps within the function.
        for acc in accounts:
            try:
                schedule_for_account(acc)
            except Exception as e:
                log(f"Error scheduling for account {acc['id']}: {e}")
        # After one full pass, sleep a bit before re-checking
        log("Completed schedule pass; sleeping 10 minutes before next pass")
        time.sleep(600)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        log("Scheduler exiting due to keyboard interrupt")
