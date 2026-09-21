#!/usr/bin/env python3
"""
Bunk Budget notifier (pure HTTP, no macOS/newton-mcp binary needed).

Calls Newton School's real API directly (reverse-engineered by capturing
the official @newtonschool/newton-mcp client's traffic and verifying the
responses against known-correct numbers) instead of spawning that binary,
which only ships for darwin/arm64. This runs on any OS/architecture,
so it can use GitHub's regular (large, old) Ubuntu runner pool instead
of the newer macOS pool that Newton's API has been blocking.

Course/subject hashes are hardcoded for the current semester (same
tradeoff the Claude-based fallback task already makes) — update
SUBJECT_PAIRS and COURSE_HASH each semester.
"""

import datetime
import json
import os
import sys
import urllib.request

BASE = "https://my.newtonschool.co"
COURSE_HASH = "fj2b9gt1im6q"  # S5'24 CS+AI RU — update each semester

# (display name, lecture subject_hash, lab subject_hash or None)
SUBJECT_PAIRS = [
    ("AML", "lpgzk6a22rjk", "lcxg47m902xl"),
    ("CN", "rrkmdglc28l5", "kgtl93l9r4so"),
    ("DL", "emsh59e1vvxu", "2lsff30qm19x"),
    ("MCA", "9c7mdl9t40hc", "iixgc703fkyv"),
]

NTFY_TOPIC = os.environ["NTFY_TOPIC"]


def get_token():
    with open(os.path.expanduser("~/.newton-mcp/credentials.json")) as f:
        return json.load(f)["access_token"]


def api_get(path, token):
    req = urllib.request.Request(f"{BASE}{path}")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def self_performance(hash_, token):
    data = api_get(f"/api/v2/course/h/{hash_}/self_performance/", token)
    return {
        "lectures_attended": data["total_lectures_attended"],
        "total_lectures": data["total_lectures"],
        "completed_assignment_questions": data["total_completed_assignment_questions"],
        "total_assignment_questions": data["total_assignment_questions"],
    }


def get_assignments(course_hash, token):
    items = []
    for is_contest in ("true", "false"):
        data = api_get(
            f"/api/v2/course/h/{course_hash}/assignment/all/?limit=50&offset=0&is_contest={is_contest}",
            token,
        )
        for r in data.get("results", []):
            items.append({
                "title": r["title"],
                "subject_name": r["course"]["short_display_name"],
                "end_timestamp": r["end_timestamp"],
            })
    return items


def get_deadline_reminders(course_hash, token):
    items = get_assignments(course_hash, token)
    now_ms = datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000
    window_ms = 24 * 60 * 60 * 1000
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

    due_soon = [i for i in items if 0 < (i["end_timestamp"] - now_ms) <= window_ms]
    due_soon.sort(key=lambda i: i["end_timestamp"])

    lines = []
    for item in due_soon:
        due_local = datetime.datetime.fromtimestamp(item["end_timestamp"] / 1000, tz=ist)
        title = item["title"]
        if len(title) > 50:
            title = title[:47] + "..."
        lines.append(f"{item['subject_name']}: {title} (by {due_local.strftime('%I:%M %p')})")
    return lines


def send_ntfy(message):
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    req = urllib.request.Request(url, data=message.encode("utf-8"), method="POST")
    req.add_header("Title", "Bunk Budget")
    req.add_header("Tags", "bar_chart")
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


STATE_FILE = "state.json"


def today_ist():
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(tz=ist).strftime("%Y-%m-%d")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def mark_sent(slot):
    state = load_state()
    state[slot] = today_ist()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def already_sent(slot):
    return load_state().get(slot) == today_ist()


def main():
    slot = os.environ.get("SLOT")
    if slot and already_sent(slot):
        print(f"'{slot}' notification already sent today ({today_ist()}) — skipping.")
        return

    token = get_token()

    overall = self_performance(COURSE_HASH, token)
    overall_pct = overall["lectures_attended"] / overall["total_lectures"] * 100 if overall["total_lectures"] else 0
    assign_pct = (
        overall["completed_assignment_questions"] / overall["total_assignment_questions"] * 100
        if overall["total_assignment_questions"] else 0
    )

    lines = []
    for name, lec_hash, lab_hash in SUBJECT_PAIRS:
        lec = self_performance(lec_hash, token)
        lab = self_performance(lab_hash, token) if lab_hash else {"lectures_attended": 0, "total_lectures": 0}
        a = lec["lectures_attended"] + lab["lectures_attended"]
        t = lec["total_lectures"] + lab["total_lectures"]
        if t == 0:
            continue
        pct = a / t * 100
        lines.append(f"{name}: {pct:.0f}%")

    message = f"Overall: {overall_pct:.1f}%\n" + "\n".join(lines) + f"\nAssignments: {assign_pct:.0f}%"
    if assign_pct <= 75:
        message += "\n\nYou're almost at 100% assignments, just a few more to go!"

    if os.environ.get("CHECK_DEADLINES") == "true":
        deadline_lines = get_deadline_reminders(COURSE_HASH, token)
        if deadline_lines:
            message += "\n\nDue in next 24h:\n" + "\n".join(deadline_lines)

    send_ntfy(message)
    if slot:
        mark_sent(slot)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
