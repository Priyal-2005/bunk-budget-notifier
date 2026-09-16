#!/usr/bin/env python3
"""
Bunk Budget notifier.

Spawns the real @newtonschool/newton-mcp server over stdio (the same
official tool used inside Claude), pulls attendance data, computes
lecture+lab combined attendance per subject, and pushes a summary to
an ntfy.sh topic. Runs headless in CI, no Claude/laptop required.
"""

import json
import os
import subprocess
import sys
import threading
import urllib.request
import itertools

THRESHOLD = 75.0
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

_id_counter = itertools.count(1)


class MCPClient:
    def __init__(self, cmd):
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._pending = {}
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg_id = msg.get("id")
            if msg_id is not None:
                with self._lock:
                    self._pending[msg_id] = msg

    def _send(self, payload):
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _wait(self, msg_id, timeout=30):
        import time
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if msg_id in self._pending:
                    return self._pending.pop(msg_id)
            time.sleep(0.05)
        raise TimeoutError(f"MCP server did not respond to request {msg_id} in time")

    def request(self, method, params=None):
        msg_id = next(_id_counter)
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
        resp = self._wait(msg_id)
        if "error" in resp:
            raise RuntimeError(f"MCP error on {method}: {resp['error']}")
        return resp.get("result")

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def call_tool(self, name, arguments=None):
        result = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            raise RuntimeError(f"Tool {name} failed: {result}")
        content = result.get("content", [])
        text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.terminate()


def pair_subjects(subjects):
    """Pair lecture subjects with their lab counterparts by common name prefix."""
    def base_name(name):
        n = name
        for marker in [" Lab 1", " - Lab", " Lab"]:
            if marker in n:
                n = n.split(marker)[0]
                break
        for suffix in [" PM-CB2", " - CB2", " PM -CB2", " - D", " Tut 1"]:
            n = n.replace(suffix, "")
        return n.strip()

    groups = {}
    for s in subjects:
        key = base_name(s["subject_name"])
        is_lab = "lab" in s["subject_name"].lower()
        groups.setdefault(key, {"name": key, "lec": None, "lab": None})
        if is_lab:
            groups[key]["lab"] = s["subject_hash"]
        else:
            groups[key]["lec"] = s["subject_hash"]
    return list(groups.values())


def budget(attended, total, threshold_frac):
    max_miss = attended / threshold_frac - total
    if max_miss >= 0:
        return int(max_miss)
    import math
    needed = math.ceil((threshold_frac * total - attended) / (1 - threshold_frac))
    return -needed


def main():
    env = os.environ.copy()
    client = MCPClient(["npx", "-y", "@newtonschool/newton-mcp@latest"])
    try:
        client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "bunk-budget-notifier", "version": "1.0"},
        })
        client.notify("notifications/initialized")

        courses = client.call_tool("list_courses")
        primary_hash = courses.get("primary_course_hash")
        course = next(c for c in courses["courses"] if c["course_hash"] == primary_hash)

        overview = client.call_tool("get_course_overview", {"course_hash": primary_hash})
        perf = overview["performance"]
        overall_a, overall_t = perf["lectures_attended"], perf["total_lectures"]

        pairs = pair_subjects(course["subjects"])
        threshold_frac = THRESHOLD / 100

        lines = []
        worst = []
        for p in pairs:
            lec_a = lec_t = lab_a = lab_t = 0
            if p["lec"]:
                sp = client.call_tool("get_subject_progress", {"course_hash": primary_hash, "subject_hash": p["lec"]})
                lec_a, lec_t = sp["performance"]["lectures_attended"], sp["performance"]["total_lectures"]
            if p["lab"]:
                sp = client.call_tool("get_subject_progress", {"course_hash": primary_hash, "subject_hash": p["lab"]})
                lab_a, lab_t = sp["performance"]["lectures_attended"], sp["performance"]["total_lectures"]
            a, t = lec_a + lab_a, lec_t + lab_t
            if t == 0:
                continue
            pct = a / t * 100
            b = budget(a, t, threshold_frac)
            if b < 0:
                lines.append(f"{p['name']} {pct:.0f}% (attend next {-b} straight)")
                worst.append((pct, p["name"]))
            elif b == 0:
                lines.append(f"{p['name']} {pct:.0f}% (no room to skip)")
                worst.append((pct, p["name"]))

        overall_pct = overall_a / overall_t * 100 if overall_t else 0
        title = f"Bunk Budget: {overall_pct:.1f}% overall"
        if lines:
            body = " | ".join(lines[:3])
        else:
            body = "All subjects healthy, room to spare."
        message = f"{title}. {body}"[:196]

        send_ntfy(message, title="Bunk Budget")
    finally:
        client.close()


def send_ntfy(message, title=None):
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    req = urllib.request.Request(url, data=message.encode("utf-8"), method="POST")
    if title:
        req.add_header("Title", title)
    req.add_header("Tags", "bar_chart")
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # Don't send a misleading notification on failure; just fail the CI run.
        sys.exit(1)
