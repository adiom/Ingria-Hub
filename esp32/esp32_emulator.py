#!/usr/bin/env python3

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


FILE_FIELDS = {
    "image": "image_file",
    "audio": "audio_file",
    "video": "video_file",
}


@dataclass
class DeviceConfig:
    base_url: str
    endpoint: str
    user_id: int
    username: str
    timeout: float
    retries: int
    retry_delay: float


class Esp32HttpEmulator:
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.request_url = config.base_url.rstrip("/") + config.endpoint
        self.sequence_number = 0

    def boot(self):
        print("[ESP32] Питание включено")
        print(f"[ESP32] WiFi подключен (эмуляция): {self.config.base_url}")
        print(f"[ESP32] Сервер: {self.request_url}")

    def status(self):
        print(f"[ESP32] user_id={self.config.user_id}")
        print(f"[ESP32] username={self.config.username}")
        print(f"[ESP32] server={self.request_url}")
        print(f"[ESP32] sequence={self.sequence_number}")

    def send_text(self, prompt: str):
        return self._request(prompt=prompt)

    def send_file(self, kind: str, path: Path, prompt: Optional[str] = None):
        if kind not in FILE_FIELDS:
            raise ValueError(f"Неизвестный тип файла: {kind}")
        if not path.is_file():
            raise FileNotFoundError(f"Файл не найден: {path}")
        return self._request(prompt=prompt, kind=kind, path=path)

    def _request(
        self,
        prompt: Optional[str] = None,
        kind: Optional[str] = None,
        path: Optional[Path] = None,
    ):
        self.sequence_number += 1
        print(
            f"[ESP32] Запрос #{self.sequence_number}: "
            f"prompt={bool(prompt)}, file={kind or 'нет'}"
        )

        body, content_type = self._build_multipart_body(prompt, kind, path)
        last_error = None

        for attempt in range(1, self.config.retries + 1):
            started_at = time.monotonic()
            request = urllib.request.Request(
                self.request_url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": content_type,
                    "User-Agent": "Ingria-ESP32-Emulator/1.0",
                    "X-ESP32-Sequence": str(self.sequence_number),
                    "X-ESP32-Attempt": str(attempt),
                },
            )

            try:
                with urllib.request.urlopen(
                    request, timeout=self.config.timeout
                ) as response:
                    raw_response = response.read().decode("utf-8")
                    elapsed = time.monotonic() - started_at
                    print(f"[ESP32] HTTP {response.status}, {elapsed:.2f} с")
                    self._print_response(raw_response)
                    return True
            except urllib.error.HTTPError as error:
                raw_response = error.read().decode("utf-8", errors="replace")
                elapsed = time.monotonic() - started_at
                print(f"[ESP32] HTTP {error.code}, {elapsed:.2f} с")
                self._print_response(raw_response)
                last_error = error
                if 400 <= error.code < 500 and error.code not in (408, 429):
                    return False
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_error = error
                print(f"[ESP32] Ошибка сети: {error}")

            if attempt < self.config.retries:
                delay = self.config.retry_delay * (2 ** (attempt - 1))
                print(
                    f"[ESP32] Повтор через {delay:.1f} с "
                    f"({attempt}/{self.config.retries})"
                )
                time.sleep(delay)

        print(f"[ESP32] Запрос #{self.sequence_number} не выполнен: {last_error}")
        return False

    def _build_multipart_body(
        self,
        prompt: Optional[str],
        kind: Optional[str],
        path: Optional[Path],
    ):
        boundary = "----IngriaESP32" + uuid.uuid4().hex
        chunks = []

        for name, value in (
            ("prompt", prompt),
            ("user_id", str(self.config.user_id)),
            ("username", self.config.username),
        ):
            if value is None:
                continue
            chunks.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
            )

        if kind and path:
            content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            header = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{FILE_FIELDS[kind]}"; '
                f'filename="{path.name}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
            chunks.extend((header, path.read_bytes(), b"\r\n"))

        chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    @staticmethod
    def _print_response(raw_response: str):
        try:
            parsed = json.loads(raw_response)
            response_text = parsed.get("response")
            if response_text is not None:
                print(f"[Ингрия] {response_text}")
                return
            print(f"[Ингрия] {json.dumps(parsed, ensure_ascii=False, indent=2)}")
            return
        except json.JSONDecodeError:
            pass
        print(f"[Ингрия] {raw_response}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Эмуляция HTTP-клиента ESP32 для проверки POST /ask_ingria"
    )
    parser.add_argument("--url", default="http://localhost:31337")
    parser.add_argument("--endpoint", default="/ask_ingria")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--username", default="esp32-emulator")
    parser.add_argument("--timeout", type=float, default=70.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=1.0)
    parser.add_argument("--message", help="Отправить текст и выйти")
    parser.add_argument("--file", type=Path, help="Файл для отправки")
    parser.add_argument(
        "--kind", choices=sorted(FILE_FIELDS), help="Тип файла"
    )
    parser.add_argument(
        "--script",
        type=Path,
        help="Файл сценариев: text/image/audio/video/wait/exit по одной команде в строке",
    )
    return parser.parse_args()


def run_command(emulator: Esp32HttpEmulator, command: str) -> bool:
    parts = command.strip().split(maxsplit=1)
    if not parts:
        return True
    action = parts[0].lower()
    arguments = parts[1] if len(parts) == 2 else ""

    if action in ("exit", "quit"):
        return False
    if action == "help":
        print(
            "[ESP32] Команды: text <сообщение>, image/audio/video <файл> [prompt], "
            "wait <сек>, user <id>, name <имя>, status, reconnect, exit"
        )
        return True
    if action == "status":
        emulator.status()
        return True
    if action == "reconnect":
        print(f"[ESP32] Повторное подключение к {emulator.config.base_url}")
        return True
    if action == "user":
        try:
            emulator.config.user_id = int(arguments)
        except ValueError:
            print("[ESP32] Использование: user <id>")
        return True
    if action == "name":
        if not arguments:
            print("[ESP32] Использование: name <имя>")
        else:
            emulator.config.username = arguments
        return True
    if action == "wait":
        try:
            delay = float(arguments)
        except ValueError:
            print("[ESP32] Использование: wait <секунды>")
            return True
        print(f"[ESP32] Ожидание {delay:.1f} с")
        time.sleep(delay)
        return True
    if action in FILE_FIELDS:
        file_parts = arguments.split(maxsplit=1)
        if not file_parts:
            print(f"[ESP32] Использование: {action} <путь> [prompt]")
            return True
        file_path = Path(file_parts[0]).expanduser()
        prompt = file_parts[1] if len(file_parts) == 2 else None
        try:
            emulator.send_file(action, file_path, prompt)
        except (FileNotFoundError, ValueError) as error:
            print(f"[ESP32] {error}")
        return True
    if action == "text":
        if not arguments:
            print("[ESP32] Использование: text <сообщение>")
            return True
        emulator.send_text(arguments)
        return True
    print(f"[ESP32] Неизвестная команда: {action}")
    return True


def main():
    args = parse_args()
    emulator = Esp32HttpEmulator(
        DeviceConfig(
            base_url=args.url,
            endpoint=args.endpoint,
            user_id=args.user_id,
            username=args.username,
            timeout=args.timeout,
            retries=args.retries,
            retry_delay=args.retry_delay,
        )
    )

    if args.file and not args.kind:
        raise SystemExit("Для --file нужно указать --kind image/audio/video")
    if args.kind and not args.file:
        raise SystemExit("Для --kind нужно указать --file")
    if args.message and args.file:
        raise SystemExit("--message и --file нельзя использовать одновременно")

    emulator.boot()

    if args.message:
        ok = emulator.send_text(args.message)
        raise SystemExit(0 if ok else 1)
    if args.file and args.kind:
        ok = emulator.send_file(args.kind, args.file)
        raise SystemExit(0 if ok else 1)
    if args.script:
        lines = args.script.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not run_command(emulator, line):
                break
        return

    print(
        "[ESP32] Команды: text <сообщение>, image/audio/video <файл> [prompt], "
        "wait <сек>, user <id>, name <имя>, status, exit"
    )
    while True:
        try:
            command = input("esp32> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not run_command(emulator, command):
            break


if __name__ == "__main__":
    main()
