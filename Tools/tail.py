#!/usr/bin/env python3
"""Tail normalized signals off the local bus."""
from __future__ import annotations

import argparse
import json
import os
import sys

CATEGORIES = [
    "application", "session", "file_action", "communication",
    "network", "web", "content_match", "language", "derived",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--category", default=None)
    args = ap.parse_args()

    try:
        from confluent_kafka import Consumer
    except ImportError:
        print("confluent-kafka not installed: pip install -r adapters/python/requirements.txt")
        return 1

    topics = [f"signals.{args.category}"] if args.category else [f"signals.{c}" for c in CATEGORIES]
    consumer = Consumer({
        "bootstrap.servers": os.getenv("BUS_BOOTSTRAP", "localhost:9092"),
        "group.id": "tail",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe(topics)

    seen = 0
    try:
        while seen < args.max:
            msg = consumer.poll(2.0)
            if msg is None:
                break
            if msg.error():
                continue
            env = json.loads(msg.value())
            print(f"{env['occurred_at']}  {env['signal_type']:<32} "
                  f"subject={env['subject']['subject_id']} "
                  f"estate={env['source']['estate']} "
                  f"decision={env['authority']['decision_id']}")
            seen += 1
    finally:
        consumer.close()

    if seen == 0:
        print("no signals on the bus; run 'make demo'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
