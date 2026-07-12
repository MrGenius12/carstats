"""
CarStats.ie — простой мониторинг доступности сайта с алертом в Telegram.

Логика:
  - Проверяет URL (по умолчанию https://carstats.ie)
  - Сравнивает текущий статус (up/down) с предыдущим (хранится в status.json)
  - Шлёт в Telegram сообщение ТОЛЬКО при смене статуса (down->up или up->down),
    чтобы не спамить одним и тем же алертом каждые 5 минут

Переменные окружения (задаются как GitHub Secrets):
  TELEGRAM_TOKEN   — токен бота
  TELEGRAM_CHAT_ID — chat_id, куда слать алерты
  SITE_URL         — необязательно, по умолчанию https://carstats.ie
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

SITE_URL         = os.environ.get("SITE_URL", "https://carstats.ie")
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATUS_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")

TIMEOUT_SECONDS  = 15


def tg_send(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
    except Exception as e:
        print(f"  ⚠ Telegram send error: {e}")


def check_site(url: str):
    """Возвращает (is_up: bool, detail: str)."""
    try:
        start = time.time()
        r = requests.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        elapsed_ms = int((time.time() - start) * 1000)
        if 200 <= r.status_code < 400:
            return True, f"HTTP {r.status_code}, {elapsed_ms}ms"
        return False, f"HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return False, f"Timeout after {TIMEOUT_SECONDS}s"
    except requests.exceptions.SSLError as e:
        return False, f"SSL error: {e}"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {e}"
    except Exception as e:
        return False, f"Unknown error: {e}"


def load_previous_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"is_up": True, "since": None}  # считаем что был "up" по умолчанию


def save_status(is_up: bool):
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "is_up": is_up,
            "since": datetime.now(timezone.utc).isoformat(),
        }, f)


def main():
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    is_up, detail = check_site(SITE_URL)
    previous = load_previous_status()
    was_up = previous.get("is_up", True)

    print(f"[{now_str}] {SITE_URL} — {'UP' if is_up else 'DOWN'} ({detail})")

    if is_up and not was_up:
        # Восстановление после падения
        down_since = previous.get("since", "неизвестно")
        tg_send(
            f"✅ <b>CarStats.ie снова доступен</b>\n"
            f"🕐 Время: {now_str}\n"
            f"📊 {detail}\n"
            f"⏱ Был недоступен с: {down_since}"
        )
        save_status(True)

    elif not is_up and was_up:
        # Сайт только что упал
        tg_send(
            f"🔴 <b>CarStats.ie недоступен!</b>\n"
            f"🕐 Время: {now_str}\n"
            f"⚠️ Причина: {detail}\n"
            f"🔗 {SITE_URL}"
        )
        save_status(False)

    else:
        # Статус не изменился — просто обновим отметку, алерт не шлём
        save_status(is_up)


if __name__ == "__main__":
    main()
