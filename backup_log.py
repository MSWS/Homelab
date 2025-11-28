#!/usr/bin/env python3
"""
backup_to_discord_two_messages_dest.py

Behavior:
  Expects a single command line argument: the Destination string describing where the backup is being sent.
  Reads newline-delimited JSON status lines from stdin.
  Uses DISCORD_WEBHOOK environment variable for the webhook URL.
  Posts two Discord messages:
    1) A static "Backup started" embed.
    2) An editable "in progress" embed with percent in the title, transferred, files, elapsed, ETA.
       Edited at most once every MIN_UPDATE_INTERVAL seconds.
       Finally edited to a "Backup finished" embed with duration and size delta.
  ETA is estimated from bytes_done / elapsed.
  All embeds depend only on native Discord timestamps.
"""

import sys
import os
import json
import time
import datetime
import requests
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

WEBHOOK_ENV = "DISCORD_WEBHOOK"
WEBHOOK_URL = None
USERNAME = "Backup Bot"
AVATAR_URL = None
UPDATE_HEADERS = {"Content-Type": "application/json"}
MIN_UPDATE_INTERVAL = 5.0

def now_iso_z():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def human_bytes(n):
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
    try:
        if seconds is None:
            return "unknown"
        s = int(round(seconds))
        return str(datetime.timedelta(seconds=s))
    except Exception:
        return "unknown"

def _add_wait_param(url):
    p = urlparse(url)
    qs = parse_qs(p.query)
    qs["wait"] = ["true"]
    new_q = urlencode(qs, doseq=True)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))

def post_message(url, payload, wait_for_message=False):
    used_url = _add_wait_param(url) if wait_for_message else url
    resp = requests.post(used_url, json=payload, headers=UPDATE_HEADERS, timeout=15)
    if resp.status_code in (200, 201):
        try:
            return resp.json()
        except Exception:
            return None
    if resp.status_code == 204:
        return None
    resp.raise_for_status()
    return None

def edit_message(url, message_id, payload):
    parsed = urlparse(url)
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
    e = {}
    if title is not None:
        e["title"] = title
    if description is not None:
        e["description"] = description
    e["color"] = color
    if fields:
        e["fields"] = [{"name": n, "value": v, "inline": bool(i)} for (n, v, i) in fields]
    e["timestamp"] = timestamp or now_iso_z()
    return e

def compute_eta(bytes_done, total_bytes, elapsed_seconds):
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
        return remaining / rate
    except Exception:
        return None

def usage_and_exit():
    sys.stderr.write("Usage: python3 backup_to_discord_two_messages_dest.py \"Destination\"\n")
    sys.exit(2)

def main():
    global WEBHOOK_URL

    if len(sys.argv) != 2:
        usage_and_exit()
    destination = sys.argv[1]

    WEBHOOK_URL = os.environ.get(WEBHOOK_ENV)
    if not WEBHOOK_URL:
        sys.stderr.write(f"ERROR: {WEBHOOK_ENV} must be set\n")
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

        if not started and mtype == "status":
            started = True
            start_time_epoch = time.time()

            percent = obj.get("percent_done", 0.0)
            bytes_done = obj.get("bytes_done", 0)
            total_bytes = obj.get("total_bytes")
            total_files = obj.get("total_files", "?")

            start_fields = [
                ("Destination", destination, True),
                ("Transferred", f"{human_bytes(bytes_done)}" + (f" / {human_bytes(total_bytes)}" if total_bytes else ""), True),
                ("Files total", str(total_files), True),
            ]
            start_payload = {
                "username": USERNAME,
                "avatar_url": AVATAR_URL,
                "embeds": [
                    make_embed(
                        title="Backup Started",
                        description=None,
                        fields=start_fields,
                        color=0x3498db
                    )
                ]
            }
            try:
                resp = post_message(WEBHOOK_URL, start_payload, wait_for_message=True)
                started_message_id = resp.get("id") if resp and isinstance(resp, dict) else None
            except Exception as e:
                sys.stderr.write(f"Failed to POST started message: {e}\n")

            in_title = f"Backup in progress ({percent * 100:5.2f}%)"
            in_fields = [
                ("Destination", destination, True),
                ("Transferred", f"{human_bytes(bytes_done)}" + (f" / {human_bytes(total_bytes)}" if total_bytes else ""), True),
                ("Files", str(total_files), True),
                ("Elapsed", "0:00:00", True),
                ("ETA", "calculating", True),
            ]
            in_payload = {
                "username": USERNAME,
                "avatar_url": AVATAR_URL,
                "embeds": [
                    make_embed(
                        title=in_title,
                        description=None,
                        fields=in_fields,
                        color=0xf1c40f
                    )
                ]
            }
            try:
                resp = post_message(WEBHOOK_URL, in_payload, wait_for_message=True)
                inprogress_message_id = resp.get("id") if resp and isinstance(resp, dict) else None
            except Exception as e:
                sys.stderr.write(f"Failed to create in progress message: {e}\n")

            last_update_time = time.time()
            continue

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

            elapsed_s = now - start_time_epoch if start_time_epoch else 0
            eta_s = compute_eta(bytes_done, total_bytes, elapsed_s)
            eta_str = nice_hms(eta_s) if eta_s is not None else "unknown"

            title = f"Backup in progress ({percent * 100:5.2f}%)"
            elapsed_hms = nice_hms(elapsed_s)
            fields = [
                ("Destination", destination, True),
                ("Transferred", f"{human_bytes(bytes_done)}" + (f" / {human_bytes(total_bytes)}" if total_bytes else ""), True),
                ("Files processed", f"{files_done or '?'} / {files_total}", True),
                ("Elapsed", elapsed_hms, True),
                ("ETA", eta_str, True),
            ]
            payload = {
                "embeds": [
                    make_embed(
                        title=title,
                        description=None,
                        fields=fields,
                        color=0xf1c40f,
                        timestamp=now_iso_z()
                    )
                ]
            }

            if inprogress_message_id:
                try:
                    edit_message(WEBHOOK_URL, inprogress_message_id, payload)
                except Exception as e:
                    sys.stderr.write(f"Failed to edit in progress message: {e}\n")
            else:
                try:
                    resp = post_message(WEBHOOK_URL, payload, wait_for_message=True)
                    inprogress_message_id = resp.get("id") if resp and isinstance(resp, dict) else None
                except Exception as e:
                    sys.stderr.write(f"Failed to POST in progress fallback: {e}\n")

            last_update_time = time.time()
            continue

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
            total_files_processed = obj_s.get("total_files_processed", "?")

            if isinstance(total_duration, (int, float)):
                if total_duration >= 1:
                    duration_str = nice_hms(total_duration)
                else:
                    duration_str = f"{total_duration:.3f} seconds"
            else:
                duration_str = "?"

            size_str = human_bytes(size_delta) if isinstance(size_delta, (int, float)) or str(size_delta).isdigit() else str(size_delta)

            fields = [
                ("Destination", destination, True),
                ("Duration", duration_str, True),
                ("Backup size delta", size_str, True),
                ("Files changed/new/unmodified", f"{files_changed} / {files_new} / {files_unmodified}", False),
                ("Total files processed", str(total_files_processed), True),
            ]
            payload = {
                "embeds": [
                    make_embed(
                        title="Backup Finished",
                        description=None,
                        fields=fields,
                        color=0x2ecc71,
                        timestamp=now_iso_z()
                    )
                ]
            }

            if inprogress_message_id:
                try:
                    edit_message(WEBHOOK_URL, inprogress_message_id, payload)
                except Exception as e:
                    sys.stderr.write(f"Failed to edit final message: {e}\nPosting fallback\n")
                    try:
                        post_message(WEBHOOK_URL, {"username": USERNAME, "avatar_url": AVATAR_URL, "embeds": payload["embeds"]})
                    except Exception as e2:
                        sys.stderr.write(f"Fallback failed: {e2}\n")
            else:
                try:
                    post_message(WEBHOOK_URL, {"username": USERNAME, "avatar_url": AVATAR_URL, "embeds": payload["embeds"]})
                except Exception as e:
                    sys.stderr.write(f"Posting summary failed: {e}\n")

            last_update_time = time.time()
            continue

    return

if __name__ == "__main__":
    main()

