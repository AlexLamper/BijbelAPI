import json
import re
from pathlib import Path


BOOK_CODE_MAP = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers", "DEU": "Deuteronomy",
    "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth", "1SA": "1 Samuel", "2SA": "2 Samuel",
    "1KI": "1 Kings", "2KI": "2 Kings", "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra",
    "NEH": "Nehemiah", "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Songs", "ISA": "Isaiah", "JER": "Jeremiah", "LAM": "Lamentations",
    "EZK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos",
    "OBA": "Obadiah", "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk",
    "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts",
    "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians", "EPH": "Ephesians",
    "PHP": "Philippians", "COL": "Colossians", "1TH": "1 Thessalonians", "2TH": "2 Thessalonians",
    "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John", "2JN": "2 John",
    "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}


LINE_PATTERN = re.compile(r"^([1-3]?[A-Z]{2,3})\s+(\d+):(\d+)\s+(.*)$")


def parse_vpl_file(vpl_path: Path):
    verses = []
    with vpl_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            match = LINE_PATTERN.match(line)
            if not match:
                continue
            book_code, chapter, verse, text = match.groups()
            book_name = BOOK_CODE_MAP.get(book_code)
            if not book_name:
                continue
            verses.append(
                {
                    "book_name": book_name,
                    "chapter": int(chapter),
                    "verse": int(verse),
                    "text": text.strip(),
                }
            )
    return verses


def build_payload(verses, name, shortname, module, year, description):
    return {
        "metadata": {
            "name": name,
            "shortname": shortname,
            "module": module,
            "lang": "nl",
            "year": year,
            "description": description,
        },
        "verses": verses,
    }


def transform():
    root = Path(__file__).resolve().parents[1]
    source_nbg = root / "non-transformed-data" / "nbg" / "nldnbg_vpl.txt"
    source_nld = root / "non-transformed-data" / "nld" / "nldnbg_vpl.txt"
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)

    nbg_verses = parse_vpl_file(source_nbg)
    nld_verses = parse_vpl_file(source_nld)

    nbg_payload = build_payload(
        nbg_verses,
        name="NBG-vertaling 1951",
        shortname="nbg1951",
        module="nbg1951",
        year=1951,
        description="Nederlandse Bijbelvertaling NBG 1951.",
    )
    nld_payload = build_payload(
        nld_verses,
        name="NLD 1939",
        shortname="nld1939",
        module="nld1939",
        year=1939,
        description="Nederlandse Bijbelvertaling NLD 1939.",
    )

    (data_dir / "nbg1951.json").write_text(json.dumps(nbg_payload, ensure_ascii=False), encoding="utf-8")
    (data_dir / "nld1939.json").write_text(json.dumps(nld_payload, ensure_ascii=False), encoding="utf-8")
    print(f"Geschreven: {data_dir / 'nbg1951.json'} ({len(nbg_verses)} verzen)")
    print(f"Geschreven: {data_dir / 'nld1939.json'} ({len(nld_verses)} verzen)")


if __name__ == "__main__":
    transform()
