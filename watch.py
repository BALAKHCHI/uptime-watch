"""Внешний сторож: раз в 5 минут проверяет /health сервера и пишет владельцу в Telegram, если сервер лёг.

Работает в GitHub Actions. Репозиторий публичный, поэтому адрес сервера, ключ и токен лежат только
в секретах репозитория, а в лог пишется одно слово: ok или down.
Состояние между запусками (с какого времени лежит, когда последний раз писали) — в state/status.json,
его переносит actions/cache.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

STATE = "state/status.json"
FAILS_TO_ALERT = 2        # две проверки подряд (~10 мин): одиночный сбой сети не тревожит
REPEAT_MIN = 30           # пока лежит — напоминать раз в 30 минут
ALMATY = timezone(timedelta(hours=5))


def check() -> tuple:
    """→ (жив ли сервер, причина). Две попытки с паузой, чтобы не путать сбой сети GitHub с падением сервера."""
    reason = ""
    for attempt in range(2):
        try:
            with urllib.request.urlopen(os.environ["HEALTH_URL"], timeout=20) as r:
                data = json.loads(r.read().decode())
            if "ok" in data:   # сервер жив; поломки отдельных частей сообщает сторож на самом сервере
                return True, ""
            reason = "сервер отвечает не тем"
        except Exception as e:
            reason = f"сервер не отвечает ({type(e).__name__})"
        if attempt == 0:
            time.sleep(20)
    return False, reason


def send(text: str):
    body = urllib.parse.urlencode({"chat_id": os.environ["TG_CHAT"], "text": text}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage", body, timeout=20)
    except Exception as e:
        print("telegram failed", type(e).__name__)


def hm(ts: float) -> str:
    return datetime.fromtimestamp(ts, ALMATY).strftime("%H:%M")


def main():
    if not os.environ.get("HEALTH_URL"):   # секреты ещё не заданы — не падаем каждые 5 минут
        print("not configured")
        return
    os.makedirs("state", exist_ok=True)
    try:
        st = json.load(open(STATE))
    except (FileNotFoundError, ValueError):
        st = {}
    now = time.time()
    ok, reason = check()
    print("ok" if ok else "down")
    if ok:
        if st.get("alerted"):
            mins = round((now - st["down_since"]) / 60)
            send(f"✅ Сервер Caramel снова в строю (GitHub-сторож). Простой около {mins} мин, с {hm(st['down_since'])}.")
        st = {"fails": 0}
    else:
        st["fails"] = st.get("fails", 0) + 1
        st.setdefault("down_since", now)
        if st["fails"] >= FAILS_TO_ALERT and not st.get("alerted"):
            send(f"🚨 Сервер Caramel: {reason}.\nС {hm(st['down_since'])} по Алматы · проверено GitHub-сторожем.\n"
                 "Боты в Битриксе и Telegram, скорее всего, не работают. Напишите в Claude «сервер лёг».")
            st["alerted"] = st["last_alert"] = now
        elif st.get("alerted") and now - st.get("last_alert", 0) >= REPEAT_MIN * 60:
            mins = round((now - st["down_since"]) / 60)
            send(f"🚨 Сервер Caramel всё ещё лежит: {mins} мин (с {hm(st['down_since'])}). {reason}.")
            st["last_alert"] = now
    json.dump(st, open(STATE, "w"))


if __name__ == "__main__":
    main()
