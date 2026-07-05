#!/usr/bin/env python3
import json
import urllib.request

BASE = "http://127.0.0.1:5001"
GAMES = [
    "take5", "pick3", "powerball", "megamillions",
    "pick10", "cash4life", "quickdraw", "nylotto",
]


def predict(game: str) -> dict:
    body = json.dumps({"game": game, "recent_k": 10}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/predict",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    for game in GAMES:
        try:
            data = predict(game)
            numbers = data.get("predicted_numbers") or []
            print(
                f"{game:14} status={data.get('status')} "
                f"date={data.get('prediction_date')} "
                f"weekday={data.get('prediction_weekday')} "
                f"numbers={numbers} "
                f"msg={data.get('message')}"
            )
        except Exception as exc:
            print(f"{game:14} REQUEST_FAIL {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())