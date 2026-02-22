"""
Seed the database with extra todo items from extra_todo_data.json via POST /todos/.
"""

import json
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8080/todos/"
DATA_FILE = Path(__file__).parent / "extra_todo_data.json"


def main() -> None:
    todos = json.loads(DATA_FILE.read_text())

    with httpx.Client() as client:
        for i, todo in enumerate(todos, start=1):
            resp = client.post(BASE_URL, json=todo)
            resp.raise_for_status()
            print(f"[{i}/{len(todos)}] Created: {todo['title']}")

    print(f"\nDone. {len(todos)} todos added.")


if __name__ == "__main__":
    main()
