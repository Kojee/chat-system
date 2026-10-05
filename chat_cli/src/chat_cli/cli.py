import argparse
import sys

import httpx
from httpx_sse import connect_sse


def _login(client: httpx.Client, user_id: int) -> None:
    r = client.post("/login", json={"user_id": user_id})
    r.raise_for_status()


def _start_or_resume(client: httpx.Client, thread_id: int | None) -> int:
    if thread_id is None:
        r = client.post("/chats")
        r.raise_for_status()
        return int(r.json()["thread_id"])
    r = client.get(f"/chats/{thread_id}/messages")
    if r.status_code == 404:
        print(f"Errore: {r.json().get('detail', 'chat non trovata')}", file=sys.stderr)
        sys.exit(1)
    r.raise_for_status()
    for m in r.json():
        prefix = "user> " if m["role"] == "user" else "agent> "
        print(f"{prefix}{m['content']}")
    return thread_id


def _send_and_stream(client: httpx.Client, thread_id: int, content: str) -> None:
    with connect_sse(
        client, "POST", f"/chats/{thread_id}/messages", json={"content": content}
    ) as event_source:
        for sse in event_source.iter_sse():
            if sse.event == "token":
                print(sse.data, end="", flush=True)
            elif sse.event == "error":
                print(f"\n[error: {sse.data}]", file=sys.stderr)
                return
            elif sse.event == "done":
                print()
                return


def main(user_id: int, thread_id: int | None, backend_url: str) -> None:
    with httpx.Client(base_url=backend_url, timeout=None) as client:
        _login(client, user_id)
        thread_id = _start_or_resume(client, thread_id)
        print(
            f"Chat avviata come utente #{user_id}. Thread ID: {thread_id}. "
            f"Riprendila con --thread-id {thread_id}."
        )
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not user_input:
                continue
            _send_and_stream(client, thread_id, user_input)


def run() -> None:
    parser = argparse.ArgumentParser(prog="chat-cli")
    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="ID dell'utente loggato (simula il login)",
    )
    parser.add_argument(
        "--thread-id",
        type=int,
        default=None,
        help="Thread ID di una chat esistente da riprendere",
    )
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8003",
        help="URL del backend (default: http://127.0.0.1:8003)",
    )
    args = parser.parse_args()
    main(args.user_id, args.thread_id, args.backend_url)
