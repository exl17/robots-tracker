import os
import hashlib
import requests
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

URLS = [
    "https://yabloki.ua/robots.txt",
    "https://ya.ua/robots.txt",
    "https://ntz.com.ua/robots.txt",
]

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

CACHE_FILE = Path("tracked_hashes.json")
TZ = ZoneInfo("Europe/Kiev")


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[Telegram error] {e}")


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def fetch(url: str) -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[Fetch error] {url}: {e}")
        return None


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def diff_lines(old: str, new: str) -> str:
    old_lines = set(old.splitlines())
    new_lines = set(new.splitlines())
    added   = [f"+ {l}" for l in new_lines - old_lines if l.strip()]
    removed = [f"- {l}" for l in old_lines - new_lines if l.strip()]
    return "\n".join(removed + added)


def main():
    cache = load_cache()
    now = datetime.now(tz=TZ).strftime("%d.%m.%Y %H:%M")

    for url in URLS:
        content = fetch(url)
        if content is None:
            send_telegram(f"⚠️ <b>Не удалось загрузить</b>\n{url}\n🕐 {now}")
            continue

        new_hash = md5(content)
        entry = cache.get(url, {})
        old_hash = entry.get("hash")
        old_content = entry.get("content", "")

        if old_hash is None:
            cache[url] = {"hash": new_hash, "content": content}
            send_telegram(
                f"✅ <b>Трекинг запущен</b>\n"
                f"🔗 {url}\n"
                f"🕐 {now}"
            )
        elif new_hash != old_hash:
            changes = diff_lines(old_content, content)
            msg = (
                f"🔔 <b>Изменение обнаружено!</b>\n"
                f"🔗 {url}\n"
                f"🕐 {now}\n\n"
                f"<pre>{changes[:3000]}</pre>"
            )
            send_telegram(msg)
            cache[url] = {"hash": new_hash, "content": content}
        else:
            print(f"[OK] No changes: {url}")

    save_cache(cache)


if __name__ == "__main__":
    main()
