"""
Tekst van de dag: curated pool invariants, selection rules and - when the Bible
data is present locally (DATA_DIR / data / private-data) - that every entry
resolves to real text.

Run from the repo root:  python -m unittest tests.test_daytext -v
"""

import collections
import os
import re
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import daytext  # noqa: E402

NEW_TESTAMENT = {
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
}

# Acrostic stanza labels the Statenvertaling data prefixes to some verses
# ("Nun. Uw woord is een lamp..."): noise on a verse-of-the-day card.
ACROSTIC_LABEL = re.compile(
    r"^(Aleph|Beth|Gimel|Daleth|He|Vau|Zain|Cheth|Teth|Jod|Caph|Lamed|Mem|Nun|Samech|Ain|Pe|Tsade|Koph|Resch|Schin|Thau)\.",
)

POOL = daytext.load_pool()


class PoolInvariants(unittest.TestCase):
    def test_covers_a_leap_year(self):
        self.assertGreaterEqual(len(POOL), 366)

    def test_no_duplicates_or_overlaps(self):
        ids = [daytext.entry_id(e) for e in POOL]
        dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
        self.assertEqual(dupes, [])
        by_chapter = collections.defaultdict(list)
        for e in POOL:
            by_chapter[(e["book"], e["chapter"])].append(e)
        for entries in by_chapter.values():
            entries.sort(key=lambda e: e["verse"])
            for a, b in zip(entries, entries[1:]):
                self.assertLess(a["verse_end"], b["verse"], f"overlap: {daytext.entry_id(a)} / {daytext.entry_id(b)}")

    def test_passages_stay_short(self):
        for e in POOL:
            self.assertGreaterEqual(e["chapter"], 1)
            self.assertGreaterEqual(e["verse"], 1)
            self.assertGreaterEqual(e["verse_end"], e["verse"], daytext.entry_id(e))
            self.assertLessEqual(e["verse_end"] - e["verse"], 2, daytext.entry_id(e))

    def test_balanced_across_the_bible(self):
        counts = collections.Counter(e["book"] for e in POOL)
        self.assertLessEqual(counts["Psalms"] / len(POOL), 0.20)
        for book, n in counts.items():
            if book != "Psalms":
                self.assertLessEqual(n / len(POOL), 0.10, book)
        nt = sum(n for book, n in counts.items() if book in NEW_TESTAMENT)
        self.assertGreaterEqual(nt / len(POOL), 0.30)
        self.assertGreaterEqual((len(POOL) - nt) / len(POOL), 0.30)
        self.assertGreaterEqual(len(counts), 40)


class Selection(unittest.TestCase):
    def test_no_repeats_within_a_year(self):
        for year in (2024, 2026, 2027, 2028):
            day = date(year, 1, 1)
            seen = []
            while day.year == year:
                seen.append(daytext.entry_id(daytext.entry_for(POOL, day.isoformat())))
                day += timedelta(days=1)
            self.assertEqual(len(seen), len(set(seen)), year)

    def test_deterministic_and_order_independent(self):
        self.assertEqual(daytext.entry_for(POOL, "2026-09-16"), daytext.entry_for(POOL, "2026-09-16"))
        self.assertEqual(daytext.entry_for(list(reversed(POOL)), "2026-09-16"), daytext.entry_for(POOL, "2026-09-16"))
        self.assertEqual(daytext.entry_for(POOL, "hello"), daytext.entry_for(POOL, "hello"))

    def test_consecutive_years_differ(self):
        a = [daytext.entry_id(e) for e in daytext.year_order(POOL, 2026)]
        b = [daytext.entry_id(e) for e in daytext.year_order(POOL, 2027)]
        self.assertNotEqual(a, b)

    def test_amsterdam_calendar_day(self):
        utc = timezone.utc
        cases = [
            (datetime(2026, 9, 15, 21, 59, tzinfo=utc), date(2026, 9, 15)),  # 23:59 CEST
            (datetime(2026, 9, 15, 22, 0, tzinfo=utc), date(2026, 9, 16)),   # 00:00 CEST
            (datetime(2026, 1, 15, 22, 30, tzinfo=utc), date(2026, 1, 15)),  # 23:30 CET
            (datetime(2026, 1, 15, 23, 0, tzinfo=utc), date(2026, 1, 16)),   # 00:00 CET
            (datetime(2026, 3, 28, 23, 0, tzinfo=utc), date(2026, 3, 29)),   # DST starts that night
            (datetime(2026, 10, 24, 22, 0, tzinfo=utc), date(2026, 10, 25)), # DST ends that night
            (datetime(2026, 12, 31, 23, 0, tzinfo=utc), date(2027, 1, 1)),
        ]
        for now, expected in cases:
            self.assertEqual(daytext.amsterdam_today(now), expected, now)

    def test_no_seed_means_amsterdam_today(self):
        now = datetime(2026, 9, 15, 22, 30, tzinfo=timezone.utc)
        self.assertEqual(daytext.entry_for(POOL, None, now), daytext.entry_for(POOL, "2026-09-16"))

    def test_invalid_date_seed_is_just_a_seed(self):
        self.assertIsNone(daytext.parse_iso_date("2026-02-30"))
        self.assertIn(daytext.entry_for(POOL, "2026-02-30"), POOL)


def _load_main():
    os.environ.setdefault("SKIP_PRIVATE_DATA_SYNC", "1")
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        import main  # noqa: WPS433 - loads the Bible data exactly as the API does
    finally:
        os.chdir(cwd)
    return main


class AgainstBibleData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = _load_main()
        if "sv" not in cls.main.all_versions:
            raise unittest.SkipTest("Statenvertaling data not present locally (set DATA_DIR)")

    def _unresolved(self, key):
        data = self.main.all_versions[key]["data"]
        return [
            daytext.entry_id(e)
            for e in POOL
            if not daytext.resolve_entry(data, e, self.main.resolve_book_name_for_data)
        ]

    def test_every_entry_exists_in_the_statenvertaling(self):
        self.assertEqual(self._unresolved("sv"), [])

    def test_every_entry_exists_in_the_other_translations(self):
        # The Canisius data only has "Daniël (Grieks)", which is deliberately
        # not mapped to Daniel; that entry is served from the Statenvertaling.
        known_gaps = {"hs1917": set(), "canisius": {"Daniel 9:9"}}
        for key, allowed in known_gaps.items():
            if key not in self.main.all_versions:
                continue
            with self.subTest(key=key):
                self.assertEqual(set(self._unresolved(key)) - allowed, set())

    def test_no_acrostic_labels_in_the_text(self):
        data = self.main.all_versions["sv"]["data"]
        noisy = [
            daytext.entry_id(e)
            for e in POOL
            if ACROSTIC_LABEL.match(daytext.resolve_entry(data, e, self.main.resolve_book_name_for_data)["text"])
        ]
        self.assertEqual(noisy, [])

    def test_response_shape(self):
        result = self.main.build_daytext("2026-09-16", "sv")
        self.assertEqual(set(result), {"version", "book", "chapter", "verse", "verse_end", "text"})
        self.assertEqual(result["version"], "sv")
        for field in ("book", "chapter", "verse", "verse_end", "text"):
            self.assertIsInstance(result[field], str)
            self.assertTrue(result[field])
        self.assertEqual(result, self.main.build_daytext("2026-09-16", "sv"))

    def test_passage_joins_its_verses(self):
        data = self.main.all_versions["sv"]["data"]
        entry = {"book": "Philippians", "chapter": 4, "verse": 6, "verse_end": 7}
        found = daytext.resolve_entry(data, entry, self.main.resolve_book_name_for_data)
        self.assertEqual(found["text"], f'{data["Philippians"]["4"]["6"].strip()} {data["Philippians"]["4"]["7"].strip()}')
        self.assertEqual((found["verse"], found["verse_end"]), ("6", "7"))

    def test_missing_reference_falls_back_to_default_translation(self):
        entry = {"book": "Psalms", "chapter": 23, "verse": 1, "verse_end": 1}
        self.assertIsNone(daytext.resolve_entry({}, entry, self.main.resolve_book_name_for_data))
        if "hs1917" in self.main.all_versions:
            result = self.main.build_daytext("2026-09-16", "hs1917")
            self.assertIn(result["version"], {"hs1917", "sv"})


if __name__ == "__main__":
    unittest.main()
