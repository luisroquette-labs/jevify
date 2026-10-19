"""Run the frozen, exploratory COESA Jev ranking pilot without retrying paid calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from pathlib import Path

from tools.jev_memory_pilot import apply_decisions
from tools.jev_memory_pilot_api import ENDPOINT, MODEL, call_jev, parse_answers, serialize_request
from tools.jeviphy_stress import percentile

INVENTORY_SHA256 = "8ee6f3f616480449fa5c1cd28c3dd69d3fb466a5378190c104f9e8a6dfd36681"
MAX_REQUESTS = 20
MAX_CODE_LINES = 152
MAX_COST_USD = 0.05


def _private_file(path: Path) -> None:
    if (not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o077
            or path.parent.stat().st_mode & 0o077):
        raise ValueError(f"expected private regular file and directory: {path}")


def load_inventory(path: Path) -> list[tuple[dict, dict, dict]]:
    """Bind every request to the reviewed inventory and exact payload bytes."""
    _private_file(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != INVENTORY_SHA256:
        raise ValueError("paid inventory differs from the frozen review")
    inventory = json.loads(raw)
    records = inventory.get("records")
    if (inventory.get("model") != MODEL or inventory.get("endpoint") != ENDPOINT
            or not isinstance(records, list) or len(records) != MAX_REQUESTS
            or len({item.get("id") for item in records}) != len(records)):
        raise ValueError("invalid paid inventory")
    loaded = []
    lines = total_bytes = 0
    for record in records:
        payload_path = Path(record["payload_path"])
        if payload_path.parent != path.parent or payload_path.name != f'{record["id"]}.json':
            raise ValueError("payload is outside the frozen private directory")
        _private_file(payload_path)
        body = payload_path.read_bytes()
        if len(body) != record["bytes"] or hashlib.sha256(body).hexdigest() != record["sha256"]:
            raise ValueError("paid payload differs from the frozen review")
        payload = json.loads(body)
        if serialize_request(payload) != body or payload.get("model") != MODEL:
            raise ValueError("invalid paid payload encoding or model")
        state = payload.get("state")
        nodes = state.get("nodes") if isinstance(state, dict) else None
        pairs = state.get("pairs") if isinstance(state, dict) else None
        observations = state.get("observations") if isinstance(state, dict) else None
        if (not isinstance(nodes, list) or not isinstance(pairs, list)
                or not isinstance(observations, list) or len(observations) != 1
                or len(nodes) > 10 or len(pairs) != len(nodes)
                or [node.get("id") for node in nodes] != record["candidate_ids"]):
            raise ValueError("invalid paid candidate pool")
        pair_map = {}
        for pair in pairs:
            key, node_id, obs_id = pair["key"], pair["node_id"], pair["observation_id"]
            if (key in pair_map or node_id not in record["candidate_ids"]
                    or obs_id != observations[0]["id"]):
                raise ValueError("invalid paid pair map")
            pair_map[key] = (node_id, obs_id)
        if set(payload.get("questions", {})) != set(pair_map):
            raise ValueError("paid question set differs from pair map")
        lines += len(nodes)
        total_bytes += len(body)
        loaded.append((record, payload, pair_map))
    if (lines != inventory.get("total_code_lines") or lines > MAX_CODE_LINES
            or total_bytes != inventory.get("total_bytes")):
        raise ValueError("paid content cap or inventory totals differ")
    return loaded


def _save(path: Path, journal: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    data = json.dumps(journal, separators=(",", ":"), ensure_ascii=False).encode()
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_inventory(path: Path, journal_path: Path, api_key: str, max_requests: int) -> dict:
    if not api_key.startswith("sk-or-") or not 1 <= max_requests <= MAX_REQUESTS:
        raise ValueError("dedicated OpenRouter key and request cap are required")
    loaded = load_inventory(path)
    if journal_path.parent != path.parent or journal_path.is_symlink():
        raise ValueError("journal must be in the private inventory directory")
    if journal_path.exists():
        _private_file(journal_path)
        journal = json.loads(journal_path.read_text())
        if (journal.get("inventory_sha256") != INVENTORY_SHA256
                or any(item.get("status") != "complete" for item in journal.get("attempts", []))):
            raise ValueError("uncertain prior attempt: do not retry")
    else:
        journal = {"inventory_sha256": INVENTORY_SHA256, "attempts": []}
        _save(journal_path, journal)
    attempted = {item["id"] for item in journal["attempts"]}
    if len(attempted) != len(journal["attempts"]):
        raise ValueError("duplicate paid attempt in journal")
    for record, payload, pair_map in loaded:
        if not pair_map:
            continue
        if record["id"] in attempted:
            continue
        if (len(journal["attempts"]) >= max_requests
                or sum(item.get("cost_usd", 0) for item in journal["attempts"]) >= MAX_COST_USD):
            break
        attempt = {"id": record["id"], "status": "sent"}
        journal["attempts"].append(attempt)
        _save(journal_path, journal)
        started = time.perf_counter_ns()
        try:
            response = call_jev(payload, api_key)
            answers = parse_answers(response, pair_map)
            nodes = payload["state"]["nodes"]
            candidates = [{"node_id": node["id"], "baseline_rank": rank}
                          for rank, node in enumerate(nodes, 1)]
            ordered, suggestions = apply_decisions(
                candidates, [{"id": payload["state"]["observations"][0]["id"]}],
                answers, eligible_node_ids={node["id"] for node in nodes}, threshold=.8,
            )
            attempt.update({
                "status": "complete", "model": response["model"],
                "cost_usd": float(response["usage"]["cost"]),
                "latency_ms": round((time.perf_counter_ns() - started) / 1_000_000, 2),
                "ranked_ids": [item["node_id"] for item in ordered],
                "suggested_ids": [item["node_id"] for item in suggestions],
            })
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            attempt["status"] = "failed_or_uncertain"
            _save(journal_path, journal)
            raise RuntimeError(f'{record["id"]}: Jev outcome uncertain; no retry') from error
        _save(journal_path, journal)
        print(f'{len(journal["attempts"])}/{max_requests} complete', flush=True)
    completed = {item["id"]: item for item in journal["attempts"] if item["status"] == "complete"}
    compared = [(record, completed[record["id"]]) for record, _, _ in loaded if record["id"] in completed]
    times = [item["latency_ms"] for _, item in compared]
    return {
        "requests": len(journal["attempts"]), "completed": len(compared),
        "skipped_no_excerpt": sum(not pair_map for _, _, pair_map in loaded),
        "candidate_recall": sum(bool(set(record["gold_node_ids"]) & set(record["candidate_ids"]))
                                for record, _ in compared),
        "baseline_top5_hits": sum(bool(set(record["gold_node_ids"]) & set(record["candidate_ids"][:5]))
                                  for record, _ in compared),
        "jev_top5_hits": sum(bool(set(record["gold_node_ids"]) & set(item["ranked_ids"][:5]))
                             for record, item in compared),
        "non_gold_suggestions_for_review": sum(
            node_id not in record["gold_node_ids"]
            for record, item in compared for node_id in item["suggested_ids"]
        ),
        "latency_p50_ms": round(statistics.median(times), 2) if times else None,
        "latency_p95_ms": round(percentile(times, .95), 2) if times else None,
        "actual_cost_usd": round(sum(item["cost_usd"] for _, item in compared), 8),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--approved-paid-use", action="store_true")
    parser.add_argument("--max-requests", type=int, required=True)
    args = parser.parse_args()
    if not args.approved_paid_use:
        parser.error("paid pilot requires explicit approval flag")
    key = os.environ.get("JEV_MEMORY_PILOT_API_KEY", "")
    print(json.dumps(run_inventory(args.inventory, args.journal, key, args.max_requests)))


if __name__ == "__main__":
    main()
