#!/usr/bin/env python3
"""Verify robust ingestion across all configured games."""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:5000"
GAMES = [
    "take5", "pick3", "powerball", "megamillions",
    "pick10", "cash4life", "quickdraw", "nylotto",
]


def request(method, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


def main():
    print("=== INGESTION ROBUSTNESS TEST ===")
    failures = 0

    _, init = request("POST", "/api/startup_init", {})
    print(f"startup_init: status={init.get('status')} msg={init.get('message', '')[:100]}")
    time.sleep(2)
    _, startup = request("GET", "/api/startup_status")
    completed = sum(
        1 for value in startup.get("games", {}).values()
        if value.get("status") == "completed"
    )
    print(
        f"startup_status: {startup.get('status')} "
        f"progress={startup.get('progress')}/{startup.get('total')} "
        f"completed_games={completed}/{len(GAMES)}"
    )
    if startup.get("status") not in ("completed", "ready", "ingesting"):
        failures += 1

    print("--- manual ingest (force=false) ---")
    passed = 0
    for game in GAMES:
        started = time.time()
        _, data = request("POST", "/api/ingest", {"game": game, "force": False})
        elapsed = time.time() - started
        status = data.get("status")
        draws = data.get("total_rows") or data.get("rows_fetched") or 0
        ok = status == "completed" and draws > 0
        mark = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failures += 1
        print(f"[{mark}] {game}: status={status} draws={draws} time={elapsed:.2f}s")

    _, summaries = request("GET", "/api/games/summaries", timeout=90)
    summary_map = summaries.get("summaries", {})
    zero_games = [g for g in GAMES if summary_map.get(g, {}).get("draw_count", 0) <= 0]
    if zero_games:
        print(f"[FAIL] games with zero draws after ingest: {zero_games}")
        failures += 1
    else:
        print("[PASS] all games have draw counts in summaries")

    print("--- ingest_stream spot check (pick3) ---")
    req = urllib.request.Request(f"{BASE}/api/ingest_stream?game=pick3")
    with urllib.request.urlopen(req, timeout=15) as resp:
        chunk = resp.read(300).decode()
        if resp.status == 200 and "completed" in chunk:
            print("[PASS] ingest_stream returns completed SSE for pick3")
        else:
            print(f"[FAIL] ingest_stream unexpected: {resp.status} {chunk[:120]}")
            failures += 1

    print("=" * 50)
    print(f"MANUAL INGEST: {passed}/{len(GAMES)} fast-completed")
    print(f"OVERALL: {'PASS' if failures == 0 else 'FAIL'} ({failures} failures)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())