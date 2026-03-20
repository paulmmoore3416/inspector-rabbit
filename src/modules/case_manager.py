"""
Inspector Rabbit - Case Manager
Synchronous utility for managing OSINT investigation cases stored as JSON files.
"""

import json
import uuid
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


CASES_DIR = Path.home() / ".inspector_rabbit_cases"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CaseEvent:
    timestamp: str
    module: str
    target: str
    summary: str
    data: dict


@dataclass
class Case:
    case_id: str
    name: str
    target: str
    created_at: str
    updated_at: str
    tags: list[str]
    notes: str
    events: list[CaseEvent]
    status: str  # "active", "closed", "archived"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ensure_dir() -> None:
    CASES_DIR.mkdir(parents=True, exist_ok=True)


def _case_path(case_id: str) -> Path:
    return CASES_DIR / f"{case_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _case_to_dict(case: Case) -> dict:
    d = asdict(case)
    return d


def _dict_to_case(d: dict) -> Case:
    events = [
        CaseEvent(**e) if not isinstance(e, CaseEvent) else e
        for e in d.get("events", [])
    ]
    return Case(
        case_id   = d["case_id"],
        name      = d["name"],
        target    = d["target"],
        created_at= d["created_at"],
        updated_at= d["updated_at"],
        tags      = d.get("tags", []),
        notes     = d.get("notes", ""),
        events    = events,
        status    = d.get("status", "active"),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def create_case(
    name: str,
    target: str,
    tags: Optional[list[str]] = None,
) -> Case:
    """Create and persist a new case. Returns the Case object."""
    _ensure_dir()
    now = _now()
    case = Case(
        case_id    = str(uuid.uuid4()),
        name       = name,
        target     = target,
        created_at = now,
        updated_at = now,
        tags       = tags or [],
        notes      = "",
        events     = [],
        status     = "active",
    )
    save_case(case)
    return case


def load_case(case_id: str) -> Case:
    """Load a case from disk. Raises FileNotFoundError if not found."""
    path = _case_path(case_id)
    if not path.exists():
        raise FileNotFoundError(f"Case '{case_id}' not found at {path}")
    with path.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    return _dict_to_case(d)


def save_case(case: Case) -> None:
    """Persist a Case object to disk."""
    _ensure_dir()
    case.updated_at = _now()
    path = _case_path(case.case_id)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(_case_to_dict(case), fh, indent=2)


def list_cases() -> list[dict]:
    """
    Return a list of summary dicts for all cases.
    Each dict: {case_id, name, target, created_at, updated_at, status, event_count, tags}
    """
    _ensure_dir()
    summaries = []
    for path in sorted(CASES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with path.open("r", encoding="utf-8") as fh:
                d = json.load(fh)
            summaries.append({
                "case_id":     d.get("case_id", path.stem),
                "name":        d.get("name", ""),
                "target":      d.get("target", ""),
                "created_at":  d.get("created_at", ""),
                "updated_at":  d.get("updated_at", ""),
                "status":      d.get("status", "active"),
                "event_count": len(d.get("events", [])),
                "tags":        d.get("tags", []),
            })
        except Exception:
            continue
    return summaries


def delete_case(case_id: str) -> None:
    """Delete a case file. No-op if not found."""
    path = _case_path(case_id)
    if path.exists():
        path.unlink()


def add_event(
    case_id: str,
    module: str,
    target: str,
    summary: str,
    data: dict,
) -> None:
    """Append an event to an existing case and save."""
    case = load_case(case_id)
    event = CaseEvent(
        timestamp = _now(),
        module    = module,
        target    = target,
        summary   = summary,
        data      = data,
    )
    case.events.append(event)
    save_case(case)


def search_cases(query: str) -> list[dict]:
    """
    Full-text search across case name, target, tags, notes, and event summaries.
    Returns list of summary dicts (same format as list_cases).
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return list_cases()

    results = []
    for summary in list_cases():
        case_id = summary["case_id"]
        try:
            case = load_case(case_id)
        except Exception:
            continue

        searchable = " ".join([
            case.name,
            case.target,
            case.notes,
            " ".join(case.tags),
            " ".join(
                f"{e.module} {e.target} {e.summary}"
                for e in case.events
            ),
        ]).lower()

        if query_lower in searchable:
            results.append(summary)

    return results


def export_case_json(case_id: str) -> str:
    """Return the case as a formatted JSON string."""
    case = load_case(case_id)
    return json.dumps(_case_to_dict(case), indent=2)


def export_case_txt(case_id: str) -> str:
    """Return the case as a human-readable plaintext report."""
    case = load_case(case_id)
    lines = [
        "=" * 60,
        f"Inspector Rabbit — Case Report",
        "=" * 60,
        f"Case ID  : {case.case_id}",
        f"Name     : {case.name}",
        f"Target   : {case.target}",
        f"Status   : {case.status.upper()}",
        f"Created  : {case.created_at}",
        f"Updated  : {case.updated_at}",
        f"Tags     : {', '.join(case.tags) if case.tags else 'None'}",
        "",
        "── Notes " + "─" * 51,
        case.notes.strip() if case.notes.strip() else "(no notes)",
        "",
        f"── Events ({len(case.events)}) " + "─" * 44,
    ]

    for i, ev in enumerate(case.events, 1):
        lines.append(f"\n[{i}] {ev.timestamp}")
        lines.append(f"    Module  : {ev.module}")
        lines.append(f"    Target  : {ev.target}")
        lines.append(f"    Summary : {ev.summary}")
        if ev.data:
            for k, v in list(ev.data.items())[:8]:
                lines.append(f"    {k}: {str(v)[:80]}")

    lines += ["", "=" * 60, "Generated by Inspector Rabbit", "=" * 60]
    return "\n".join(lines)
