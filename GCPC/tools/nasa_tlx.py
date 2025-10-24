#!/usr/bin/env python3
import json, time, sys

qs = [
    ("Mental Demand", "How mentally demanding was the task? (0-100)"),
    ("Physical Demand", "How physically demanding was the task? (0-100)"),
    ("Temporal Demand", "How hurried or rushed was the pace? (0-100)"),
    ("Performance", "How successful were you? (0-100; higher=worse)"),
    ("Effort", "How hard did you have to work? (0-100)"),
    ("Frustration", "How insecure, discouraged, irritated, stressed, annoyed? (0-100)"),
]

def ask():
    print("NASA-TLX quick rating. Enter integers 0..100.")
    ratings = {}
    for key, prompt in qs:
        while True:
            try:
                v = int(input(f"{key}: {prompt}\n> "))
                if 0 <= v <= 100:
                    ratings[key] = v
                    break
            except Exception:
                pass
    return ratings

def main():
    ratings = ask()
    out = {
        "ts": int(time.time()*1000),
        "nasa_tlx": ratings
    }
    print(json.dumps(out, indent=2))
    with open("logs/nasa_tlx.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False)+"\n")

if __name__ == "__main__":
    main()
