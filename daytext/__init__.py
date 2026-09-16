"""
Tekst van de dag: one verse (or a short passage) per calendar day, drawn from a
hand-curated pool instead of from the whole Bible.

The old picker chose a random book, chapter and verse, so a day could land on a
genealogy, a census list or half a sentence of narrative. `pool.json` holds only
references that stand on their own (promises, comfort, wisdom, gospel core,
prayer, praise, exhortation). References use the Statenvertaling data's own
book keys and versification (e.g. Psalm superscriptions count as verses, so
"God is ons een Toevlucht" is Psalms 46:2, not 46:1).

Selection rules:
- The day is the Europe/Amsterdam calendar date, so everyone gets the same
  verse from 00:00 to 24:00 Dutch time (the server itself runs in UTC).
- Each year gets its own stable order: the pool sorted by
  sha256("<year>:<reference>"). Day N of the year takes entry N of that order,
  so with at least 366 entries nothing repeats within a calendar year.
  The hash sort does not depend on Python's `random` implementation or on the
  order of pool.json. Editing the pool mid-year shifts later days and can
  cause one repeat; prefer pool edits around the new year.
- `seed` (kept from the old endpoint): an ISO date `yyyy-mm-dd` picks that
  date's verse; any other string maps deterministically onto the pool.

Pure on purpose - no FastAPI, no globals from main.py - so tests can import it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Mapping, Optional

POOL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pool.json")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_pool(path: str = POOL_PATH) -> list[dict]:
    """The curated references, normalised to ints with `verse_end` always set."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    pool: list[dict] = []
    for item in raw:
        start = int(item["verse"])
        pool.append({
            "book": str(item["book"]),
            "chapter": int(item["chapter"]),
            "verse": start,
            "verse_end": int(item.get("verse_end", start)),
        })
    return pool


def entry_id(entry: Mapping) -> str:
    """`Book c:v` or `Book c:v-w` - stable key for ordering and duplicate checks."""
    ref = f'{entry["book"]} {entry["chapter"]}:{entry["verse"]}'
    if entry["verse_end"] != entry["verse"]:
        ref += f'-{entry["verse_end"]}'
    return ref


def _last_sunday(year: int, month: int) -> date:
    last_day = date(year, month + 1, 1) - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


def amsterdam_today(now: Optional[datetime] = None) -> date:
    """
    Today's date in Europe/Amsterdam, by the EU summer-time rule (last Sunday
    of March to last Sunday of October, switching at 01:00 UTC). Computed by
    hand so it does not depend on tzdata being installed on the host.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    dst_start = datetime.combine(_last_sunday(now.year, 3), time(1), tzinfo=timezone.utc)
    dst_end = datetime.combine(_last_sunday(now.year, 10), time(1), tzinfo=timezone.utc)
    offset = 2 if dst_start <= now < dst_end else 1
    return (now + timedelta(hours=offset)).date()


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value or not _ISO_DATE.match(value.strip()):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def year_order(pool: list[dict], year: int) -> list[dict]:
    """The pool in this year's order."""
    return sorted(
        pool,
        key=lambda e: hashlib.sha256(f"{year}:{entry_id(e)}".encode("utf-8")).hexdigest(),
    )


def selection(pool: list[dict], seed: Optional[str] = None, now: Optional[datetime] = None) -> tuple[list[dict], int]:
    """
    `(order, index)`: `order[index]` is the verse for this request; the
    entries after it are the deterministic fallbacks when one cannot be
    resolved in a translation.
    """
    if not pool:
        raise ValueError("daytext pool is empty")
    day = parse_iso_date(seed)
    if day is None and seed:
        order = year_order(pool, 0)
        return order, int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(order)
    day = day or amsterdam_today(now)
    order = year_order(pool, day.year)
    return order, (day.timetuple().tm_yday - 1) % len(order)


def entry_for(pool: list[dict], seed: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    order, index = selection(pool, seed, now)
    return order[index]


def resolve_entry(
    data: Mapping[str, Mapping[str, Mapping[str, str]]],
    entry: Mapping,
    resolve_book: Callable[[str, Mapping], Optional[str]],
) -> Optional[dict]:
    """
    The entry's text in one translation's data, or None when the book, chapter
    or any verse of the range is missing or empty. `text` joins a range with a
    single space.
    """
    book_key = resolve_book(entry["book"], data)
    if not book_key:
        return None
    chapter = data.get(book_key, {}).get(str(entry["chapter"]))
    if not chapter:
        return None
    texts: list[str] = []
    for number in range(entry["verse"], entry["verse_end"] + 1):
        text = chapter.get(str(number))
        if not isinstance(text, str) or not text.strip():
            return None
        texts.append(text.strip())
    return {
        "book": book_key,
        "chapter": str(entry["chapter"]),
        "verse": str(entry["verse"]),
        "verse_end": str(entry["verse_end"]),
        "text": " ".join(texts),
    }
