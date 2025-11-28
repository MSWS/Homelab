#!/usr/bin/env python3
"""
backup_to_discord_two_messages_full.py

- Posts two messages to a Discord webhook:
  1) A static "Backup started" embed (no initial progress field).
  2) A separate "in-progress" embed that is edited (rate-limited) and finally edited to a
     "Backup finished" embed that contains duration, size delta, and related fields.

- Progress percent appears in the in-progress embed title.
- ETA is estimated from observed throughput (bytes_done / elapsed).
- Sensible fields are inlined.
- In-progress updates are sent at most once every MIN_UPDATE_INTERVAL seconds (default 5).
- Final "Backup finished" embed contains no percent in the title and no human-written timestamp
  in the description. The embed still contains Discord's native timestamp field.

Usage:
  backup_program [args] | python3 backup_to_discord_two_messages_full.py https://discord.com/api/webhooks/ID/TOKEN
  or
  DISCORD_WEBHOOK="https://discord.com/api/webhooks/ID/TOKEN" backup_program | python3 backup_to_discord_two_messages_full.py
"""

import sys
import os
import json
import time
import datetime
import requests
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Configuration
WEBHOOK_URL = None
USERNAME = "Backup Bot"
AVATAR_URL = None
UPDATE_HEADERS = {"Content-Type": "application/json"}
MIN_UPDATE_INTERVAL = 5.0  # seconds between in-progress edits

def now_iso_z():
    """Return ISO 8601 UTC timestamp with Z for Discord embed timestamp."""
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat().replace('+00:00', 'Z')

def human_bytes(n):
    """Human-readable bytes. Accepts numeric or numeric-strings."""
    try:
        n = float(n)
    except Exception:
        return str(n)
    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if abs(n) < 1024.0:
            return f"{n:3.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} EiB"

def nice_hms(seconds):
    """Return a nice H:MM:SS for a number of seconds, or 'unknown'."""
    try:
        if seconds is None:
            return "unknown"
        s = int(round(seconds))
        return str(datetime.timedelta(seconds=s))
    except Exception:
        return "unknown"

def _add_wait_param(url):
    """Append ?wait=true to the webhook URL so Discord returns the created message object."""
    p = urlparse(url)
    qs = parse_qs(p.query)
    qs["wait"] = ["true"]
    new_q = urlencode(qs, doseq=True)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))

def post_message(webhook_url, payload, wait_for_message=False):
    """
    POST a webhook. If wait_for_message True, append ?wait=true so Discord returns the message object.
    Returns the JSON message object on success (when available), otherwise None.
    Raises on non-success status codes.
    """
    url = _add_wait_param(webhook_url) if wait_for_message else webhook_url
    resp = requests.post(url, json=payload, headers=UPDATE_HEADERS, timeout=15)
    if resp.status_code in (200, 201):
        try:
            return resp.json()
        except Exception:
            return None
    if resp.status_code == 204:
        return None
    resp.raise_for_status()
    return None

def edit_message(webhook_url, message_id, payload):
    """
    PATCH /webhooks/{id}/{token}/messages/{message_id}
    Returns the JSON message object on success when available, otherwise None.
    """
    parsed = urlparse(webhook_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path.rstrip("/")
    edit_url = f"{base}{path}/messages/{message_id}"
    resp = requests.patch(edit_url, json=payload, headers=UPDATE_HEADERS, timeout=15)
    if resp.status_code in (200, 201):
        try:
            return resp.json()
        except Exception:
            return None
    if resp.status_code == 204:
        return None
    resp.raise_for_status()
    return None

def make_embed(title=None, description=None, fields=None, color=0x00aaff, timestamp=None):
    """
    Create an embed dict.
    fields: list of tuples (name, value, inline_bool)
    timestamp: ISO 8601 string with Z, or None to use current time
    """
    e = {}
    if title is not None:
        e["title"] = title
    if description is not None:
        e["description"] = description
    e["color"] = color
    if fields:
        e["fields"] = [{"name": name, "value": value, "inline": bool(inline)} for (name, value, inline) in fields]
    e["timestamp"] = (timestamp or now_iso_z())
    return e

def compute_eta(bytes_done, total_bytes, elapsed_seconds):
    """
    Compute ETA in seconds: remaining / current_rate.
    Returns None if computation is not possible.
    """
    try:
        if total_bytes is None:
            return None
        bytes_done = float(bytes_done)
        total_bytes = float(total_bytes)
        if bytes_done <= 0 or elapsed_seconds <= 0:
            return None
        rate = bytes_done / elapsed_seconds
        if rate <= 0:
            return None
        remaining = max(0.0, total_bytes - bytes_done)
        eta = remaining / rate
        return eta
    except Exception:
        return None

def main():
    global WEBHOOK_URL
    if len(sys.argv) > 1:
        WEBHOOK_URL = sys.argv[1].strip()
    else:
        WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

    if not WEBHOOK_URL:
        print("ERROR: Discord webhook URL must be provided as first arg or DISCORD_WEBHOOK env var", file=sys.stderr)
        sys.exit(2)

    started = False
    start_time_epoch = None
    last_update_time = 0.0
    inprogress_message_id = None
    started_message_id = None

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            sys.stderr.write("Skipping non-json line\n")
            continue

        mtype = obj.get("message_type") or obj.get("type") or "status"

        # On first status: post the static "Backup started" embed and create the in-progress embed.
        if not started and mtype == "status":
            started = True
            start_time_epoch = time.time()

            percent = obj.get("percent_done", 0.0)
            bytes_done = obj.get("bytes_done", 0)
            total_bytes = obj.get("total_bytes")
            total_files = obj.get("total_files", "?")

            # Static "Backup started" embed (no initial progress field)
            start_title = "Backup started"
            start_fields = [
                ("Transferred", f"{human_bytes(bytes_done)}" + (f" / {human_bytes(total_bytes)}" if total_bytes else ""), True),
                ("Files total", str(total_files), True),
            ]
            start_payload = {
                "username": USERNAME,
                "avatar_url": AVATAR_URL,
                "embeds": [ make_embed(title=start_title, description=f"Started at {now_iso_z()}", fields=start_fields, color=0x3498db) ]
            }
            try:
                resp = post_message(WEBHOOK_URL, start_payload, wait_for_message=True)
                if resp and isinstance(resp, dict) and resp.get("id"):
                    started_message_id = resp.get("id")
                    sys.stderr.write(f"Posted started message id={started_message_id}\n")
                else:
                    sys.stderr.write("Posted started message but no id returned\n")
            except Exception as e:
                sys.stderr.write(f"Failed to POST started message: {e}\n")

            # Create the in-progress message and capture its id
            in_title = f"Backup in progress ({percent*100:5.2f}%)"
            in_fields = [
                ("Transferred", f"{human_bytes(bytes_done)}" + (f" / {human_bytes(total_bytes)}" if total_bytes else ""), True),
                ("Files", str(total_files), True),
                ("Elapsed", "0:00:00", True),
                ("ETA", "calculating", True),
            ]
            in_payload = {
                "username": USERNAME,
                "avatar_url": AVATAR_URL,
                "embeds": [ make_embed(title=in_title, description="Progress updates will follow", fields=in_fields, color=0xf1c40f) ]
            }
            try:
                resp = post_message(WEBHOOK_URL, in_payload, wait_for_message=True)
                if resp and isinstance(resp, dict) and resp.get("id"):
                    inprogress_message_id = resp.get("id")
                    sys.stderr.write(f"Created in-progress message id={inprogress_message_id}\n")
                else:
                    sys.stderr.write("Created in-progress message but no id returned\n")
            except Exception as e:
                sys.stderr.write(f"Failed to create in-progress message: {e}\n")

            last_update_time = time.time()
            continue

        # Status updates: edit the in-progress message at most once every MIN_UPDATE_INTERVAL seconds
        if mtype == "status":
            if not started:
                continue

            now = time.time()
            if now - last_update_time < MIN_UPDATE_INTERVAL:
                continue

            percent = obj.get("percent_done", 0.0)
            bytes_done = obj.get("bytes_done", 0)
            total_bytes = obj.get("total_bytes")
            files_done = obj.get("files_done")
            files_total = obj.get("total_files", "?")

            elapsed_s = now - (start_time_epoch or now)
            eta_s = compute_eta(bytes_done, total_bytes, elapsed_s)
            eta_str = nice_hms(eta_s) if eta_s is not None else "unknown"

            title = f"Backup in progress ({percent*100:5.2f}%)"
            elapsed_hms = nice_hms(elapsed_s)
            fields = [
                ("Transferred", f"{human_bytes(bytes_done)}" + (f" / {human_bytes(total_bytes)}" if total_bytes else ""), True),
                ("Files processed", f"{files_done or '?'} / {files_total}", True),
                ("Elapsed", elapsed_hms, True),
                ("ETA", eta_str, True),
            ]
            payload = {
                "embeds": [ make_embed(title=title, description=f"Updated {now_iso_z()}", fields=fields, color=0xf1c40f, timestamp=now_iso_z()) ]
            }

            if inprogress_message_id:
                try:
                    edit_message(WEBHOOK_URL, inprogress_message_id, payload)
                except Exception as e:
                    sys.stderr.write(f"Failed to edit in-progress message id={inprogress_message_id}: {e}\n")
            else:
                try:
                    resp = post_message(WEBHOOK_URL, payload, wait_for_message=True)
                    if resp and isinstance(resp, dict) and resp.get("id"):
                        inprogress_message_id = resp.get("id")
                        sys.stderr.write(f"Created in-progress message id={inprogress_message_id}\n")
                    else:
                        sys.stderr.write("Created in-progress message but no id returned\n")
                except Exception as e:
                    sys.stderr.write(f"Failed to POST in-progress message fallback: {e}\n")

            last_update_time = time.time()
            continue

        # Final summary: edit the in-progress message to finished
        if mtype == "summary":
            obj_s = obj
            total_duration = obj_s.get("total_duration")
            if total_duration is None:
                bs = obj_s.get("backup_start")
                be = obj_s.get("backup_end")
                if bs and be:
                    try:
                        t_bs = datetime.datetime.fromisoformat(bs)
                        t_be = datetime.datetime.fromisoformat(be)
                        total_duration = (t_be - t_bs).total_seconds()
                    except Exception:
                        total_duration = None
            if total_duration is None and start_time_epoch:
                total_duration = time.time() - start_time_epoch

            size_delta = obj_s.get("data_added") or obj_s.get("data_added_packed") or obj_s.get("total_bytes_processed") or 0
            files_changed = obj_s.get("files_changed", 0)
            files_new = obj_s.get("files_new", 0)
            files_unmodified = obj_s.get("files_unmodified", 0)
            total_files_processed = obj_s.get("total_files_processed", obj_s.get("total_files_processed") or "?")

            duration_str = "?"
            if isinstance(total_duration, (int, float)):
                if total_duration >= 1:
                    duration_str = nice_hms(total_duration)
                else:
                    duration_str = f"{total_duration:.3f} seconds"

            size_str = human_bytes(int(size_delta)) if isinstance(size_delta, (int, float)) or str(size_delta).isdigit() else str(size_delta)

            # No percent in the finished title, and no human-written timestamp in description
            title = "Backup finished"
            description = None

            fields = [
                ("Duration", duration_str, True),
                ("Backup size delta", size_str, True),
                ("Files changed/new/unmodified", f"{files_changed} / {files_new} / {files_unmodified}", False),
                ("Total files processed", str(total_files_processed), True),
            ]
            payload = {
                "embeds": [ make_embed(title=title, description=description, fields=fields, color=0x2ecc71, timestamp=now_iso_z()) ]
            }

            if inprogress_message_id:
                try:
                    edit_message(WEBHOOK_URL, inprogress_message_id, payload)
                except Exception as e:
                    sys.stderr.write(f"Failed to edit final in-progress message id={inprogress_message_id}: {e}\nPosting final message as fallback\n")
                    try:
                        post_message(WEBHOOK_URL, {"username": USERNAME, "avatar_url": AVATAR_URL, "embeds": payload["embeds"]}, wait_for_message=False)
                    except Exception as e2:
                        sys.stderr.write(f"Failed to POST final fallback message: {e2}\n")
            else:
                try:
                    post_message(WEBHOOK_URL, {"username": USERNAME, "avatar_url": AVATAR_URL, "embeds": payload["embeds"]}, wait_for_message=False)
                except Exception as e:
                    sys.stderr.write(f"Failed to POST final summary message: {e}\n")

            last_update_time = time.time()
            continue

    # finished reading stdin
    return

if __name__ == "__main__":
    main()

