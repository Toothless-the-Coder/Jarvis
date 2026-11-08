#!/usr/bin/env python3
"""Lightweight Jarvis companion for Raspberry Pi Zero 2 W.

Uses a remote OpenAI-compatible chat-completions endpoint for general requests.
Local SQLite reminders and basic commands continue to work without Wi-Fi.

Configure the cloud endpoint with environment variables:
    JARVIS_CLOUD_URL       Base URL, for example http://192.168.1.20:20128/v1
    JARVIS_CLOUD_API_KEY   Optional bearer token

The model is locked to the free OmniRoute route. The Pi does not download or run
an LLM locally. Optional speech output uses the system's espeak-ng/espeak binary.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

MODEL = "auto/coding:free"
REQUEST_TIMEOUT_SECONDS = 20
REMINDER_POLL_SECONDS = 2
SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running on a Raspberry Pi Zero 2 W. "
    "Use the cloud model for general questions. Be concise and natural for speech. "
    "Do not claim to control hardware or access live weather, traffic, email, or files "
    "unless a connected tool explicitly provides that data. Local reminders are handled "
    "by the device. If the cloud is unavailable, state that clearly."
)


def data_directory() -> Path:
    root = os.environ.get("XDG_DATA_HOME")
    return (Path(root).expanduser() if root else Path.home() / ".local" / "share") / "jarvis-pi"


def parse_reminder_request(text: str, now: Optional[datetime] = None) -> Optional[tuple[datetime, str]]:
    """Recognize common reminder phrases without needing the cloud."""
    now = now or datetime.now().astimezone()
    relative = re.search(
        r"\bremind\s+me\s+in\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?)\s+(?:to\s+)?(.+)$",
        text.strip(),
        re.IGNORECASE,
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2).lower()
        if amount <= 0 or amount > 365 * 24 * 60:
            return None
        if unit.startswith(("sec",)):
            delta = timedelta(seconds=amount)
        elif unit.startswith(("min",)):
            delta = timedelta(minutes=amount)
        elif unit.startswith(("hour", "hr")):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)
        return now + delta, relative.group(3).strip()

    at_time = re.search(r"\bremind\s+me\s+at\s+(\d{1,2}):(\d{2})\s+(?:to\s+)?(.+)$", text.strip(), re.IGNORECASE)
    if at_time:
        hour, minute = int(at_time.group(1)), int(at_time.group(2))
        if hour > 23 or minute > 59:
            return None
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due <= now:
            due += timedelta(days=1)
        return due, at_time.group(3).strip()
    return None


class ReminderStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else data_directory() / "reminders.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS reminders ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, "
                    "due_at REAL NOT NULL, notified INTEGER NOT NULL DEFAULT 0, "
                    "created_at REAL NOT NULL)"
                )

    def _connect(self):
        return sqlite3.connect(str(self.path), timeout=10)

    def add(self, due: datetime, text: str) -> int:
        if not text.strip():
            raise ValueError("Reminder text cannot be empty")
        due_epoch = due.timestamp()
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO reminders(text, due_at, created_at) VALUES (?, ?, ?)",
                    (text.strip(), due_epoch, time.time()),
                )
                return int(cursor.lastrowid)

    def list_pending(self, limit: int = 20) -> list[tuple[int, str, float]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, text, due_at FROM reminders WHERE notified=0 ORDER BY due_at LIMIT ?",
                (limit,),
            ).fetchall()
        return [(int(row[0]), str(row[1]), float(row[2])) for row in rows]

    def mark_due_notified(self, now_epoch: Optional[float] = None) -> list[tuple[int, str, float]]:
        now_epoch = now_epoch if now_epoch is not None else time.time()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    "SELECT id, text, due_at FROM reminders WHERE notified=0 AND due_at<=? ORDER BY due_at",
                    (now_epoch,),
                ).fetchall()
                if rows:
                    connection.executemany(
                        "UPDATE reminders SET notified=1 WHERE id=?",
                        [(row[0],) for row in rows],
                    )
        return [(int(row[0]), str(row[1]), float(row[2])) for row in rows]

    def dismiss(self, reminder_id: int) -> bool:
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "UPDATE reminders SET notified=1 WHERE id=? AND notified=0",
                    (int(reminder_id),),
                )
                return cursor.rowcount > 0


class SpeechOutput:
    def __init__(self):
        self.executable = shutil.which("espeak-ng") or shutil.which("espeak")
        self._lock = threading.Lock()

    def speak(self, text: str) -> bool:
        if not self.executable or not text.strip():
            return False
        try:
            with self._lock:
                subprocess.run(
                    [self.executable, text],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=45,
                )
            return True
        except (OSError, subprocess.SubprocessError):
            return False


class CloudClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url if base_url is not None else os.environ.get("JARVIS_CLOUD_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("JARVIS_CLOUD_API_KEY", "")
        self.history: list[dict[str, str]] = []

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def reply(self, text: str) -> str:
        if not self.enabled:
            raise RuntimeError("Cloud endpoint is not configured")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history[-10:])
        messages.append({"role": "user", "content": text})
        payload = json.dumps({
            "model": MODEL,
            "messages": messages,
            "temperature": 0.6,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self._endpoint(), data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Cloud endpoint returned no choices")
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Cloud endpoint returned an empty response")
        self.history.extend([
            {"role": "user", "content": text},
            {"role": "assistant", "content": content},
        ])
        return content.strip()


class JarvisPi:
    def __init__(self, cloud: Optional[CloudClient] = None, reminders: Optional[ReminderStore] = None, speech: Optional[SpeechOutput] = None):
        self.cloud = cloud or CloudClient()
        self.reminders = reminders or ReminderStore()
        self.speech = speech or SpeechOutput()

    def offline_reply(self, text: str) -> str:
        normalized = text.strip().lower()
        if normalized in {"help", "/help"}:
            return "I can still manage local reminders offline. Try: remind me in 10 minutes to check the oven, list reminders, or dismiss reminder 2."
        if normalized in {"status", "/status"}:
            cloud_status = "connected" if self.cloud.enabled else "not configured"
            return f"Cloud assistant is {cloud_status}. Local reminders are available on this Pi."
        if normalized in {"list reminders", "/reminders", "show reminders"}:
            pending = self.reminders.list_pending()
            if not pending:
                return "You have no pending reminders."
            lines = [
                f"Reminder {item_id}, due {datetime.fromtimestamp(due).astimezone().strftime('%a %I:%M %p')}: {body}"
                for item_id, body, due in pending
            ]
            return "Pending reminders: " + "; ".join(lines)
        dismiss = re.fullmatch(r"(?:dismiss|cancel|done)\s+(?:reminder\s+)?(\d+)", normalized)
        if dismiss:
            return "Reminder dismissed." if self.reminders.dismiss(int(dismiss.group(1))) else "I couldn't find that pending reminder."
        parsed = parse_reminder_request(text)
        if parsed:
            due, reminder_text = parsed
            if not reminder_text:
                return "What should I remind you about?"
            reminder_id = self.reminders.add(due, reminder_text)
            due_label = due.astimezone().strftime("%A at %I:%M %p")
            return f"Reminder {reminder_id} set for {due_label}: {reminder_text}."
        return "I can't reach the cloud assistant right now. I can still manage local reminders; say help to hear the offline commands."

    def respond(self, text: str) -> str:
        parsed = parse_reminder_request(text)
        if parsed:
            due, reminder_text = parsed
            if not reminder_text:
                return "What should I remind you about?"
            reminder_id = self.reminders.add(due, reminder_text)
            return f"Reminder {reminder_id} set for {due.astimezone().strftime('%A at %I:%M %p')}: {reminder_text}."
        if text.strip().lower() in {"help", "/help", "status", "/status", "list reminders", "/reminders", "show reminders"} or re.fullmatch(r"(?:dismiss|cancel|done)\s+(?:reminder\s+)?\d+", text.strip(), re.IGNORECASE):
            return self.offline_reply(text)
        if self.cloud.enabled:
            try:
                return self.cloud.reply(text)
            except (OSError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as error:
                print(f"Cloud request unavailable: {type(error).__name__}")
        return self.offline_reply(text)


def reminder_watcher(reminders: ReminderStore, speech: SpeechOutput, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        for reminder_id, text, due_at in reminders.mark_due_notified():
            due = datetime.fromtimestamp(due_at).astimezone().strftime("%I:%M %p")
            notice = f"Reminder {reminder_id}. It is time to {text}."
            print(f"\nJarvis: {notice}", flush=True)
            speech.speak(notice)
        stop_event.wait(REMINDER_POLL_SECONDS)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Cloud-first Jarvis companion for Raspberry Pi Zero 2 W")
    parser.add_argument("--db", type=Path, default=None, help="Override local reminder database location")
    args = parser.parse_args(argv)

    assistant = JarvisPi(reminders=ReminderStore(args.db))
    stop_event = threading.Event()
    watcher = threading.Thread(target=reminder_watcher, args=(assistant.reminders, assistant.speech, stop_event), daemon=True)
    watcher.start()
    print("Jarvis Pi ready. Cloud-first chat; local reminders remain available offline. Type help or quit.")
    if not assistant.cloud.enabled:
        print("Cloud is not configured. Set JARVIS_CLOUD_URL to a reachable OpenAI-compatible endpoint.")
    if not assistant.speech.executable:
        print("Speech output unavailable: install espeak-ng or espeak for spoken replies.")

    try:
        while True:
            try:
                text = input("You: ").strip()
            except EOFError:
                break
            if not text:
                continue
            if text.lower() in {"quit", "exit", "/quit"}:
                break
            reply = assistant.respond(text)
            print(f"Jarvis: {reply}", flush=True)
            assistant.speech.speak(reply)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        watcher.join(timeout=3)
        print("Jarvis Pi stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
