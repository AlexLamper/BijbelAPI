import argparse
import json
import re
from pathlib import Path


OLB_ABBR_TO_BOOK = {
    "Ge": "Genesis",
    "Ex": "Exodus",
    "Le": "Leviticus",
    "Nu": "Numbers",
    "De": "Deuteronomy",
    "Jos": "Joshua",
    "Jud": "Judges",
    "Ru": "Ruth",
    "1Sa": "1 Samuel",
    "2Sa": "2 Samuel",
    "1Ki": "1 Kings",
    "2Ki": "2 Kings",
    "1Ch": "1 Chronicles",
    "2Ch": "2 Chronicles",
    "Ezr": "Ezra",
    "Ne": "Nehemiah",
    "Es": "Esther",
    "Job": "Job",
    "Ps": "Psalms",
    "Pr": "Proverbs",
    "Ec": "Ecclesiastes",
    "So": "Song of Songs",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "La": "Lamentations",
    "Eze": "Ezekiel",
    "Da": "Daniel",
    "Ho": "Hosea",
    "Joe": "Joel",
    "Am": "Amos",
    "Ob": "Obadiah",
    "Jon": "Jonah",
    "Mic": "Micah",
    "Na": "Nahum",
    "Hab": "Habakkuk",
    "Zep": "Zephaniah",
    "Hag": "Haggai",
    "Zec": "Zechariah",
    "Mal": "Malachi",
    "Mt": "Matthew",
    "Mr": "Mark",
    "Lu": "Luke",
    "Joh": "John",
    "Ac": "Acts",
    "Ro": "Romans",
    "1Co": "1 Corinthians",
    "2Co": "2 Corinthians",
    "Ga": "Galatians",
    "Eph": "Ephesians",
    "Php": "Philippians",
    "Col": "Colossians",
    "1Th": "1 Thessalonians",
    "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy",
    "2Ti": "2 Timothy",
    "Tit": "Titus",
    "Phm": "Philemon",
    "Heb": "Hebrews",
    "Jas": "James",
    "1Pe": "1 Peter",
    "2Pe": "2 Peter",
    "1Jo": "1 John",
    "2Jo": "2 John",
    "3Jo": "3 John",
    "Jude": "Jude",
    "Re": "Revelation",
}

EXP_REF_RE = re.compile(r"^\$\$\$\s+([0-9A-Za-z]+)\s+(\d+):(\d+)\s*$")
LINE_REF_RE = re.compile(r"^([0-9A-Za-z]+)\s+(\d+):(\d+)\s+(.+)$")
RTF_BOOK_CHAPTER_RE = re.compile(r"^([0-9A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]+)\s+(\d+)$")
RTF_VERSE_RE = re.compile(r"^(\d+)\s+(.+)$")


def clean_olb_text(text: str) -> str:
    # Remove legacy OnLineBible formatting markers.
    cleaned = text.replace("\x03", "")
    cleaned = cleaned.replace("\\!", "")
    cleaned = cleaned.replace("\\$", "")
    cleaned = cleaned.replace("\\&", " ")
    cleaned = cleaned.replace("\\@", "")
    cleaned = cleaned.replace("\\%", "")
    cleaned = cleaned.replace("\\\\", "")
    cleaned = cleaned.replace("¶", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def read_version_ext(version_ext_path: Path) -> dict:
    lines = version_ext_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    module = lines[1].strip() if len(lines) > 1 else "basisbijbel"
    name = lines[2].strip() if len(lines) > 2 else "BasisBijbel"
    publisher = lines[3].strip() if len(lines) > 3 else "Stichting BasisBijbel"
    return {"module": module.lower(), "name": name, "publisher": publisher}


def resolve_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (root / candidate)


def suggest_input_files(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    names = []
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in {".exp", ".txt", ".rtf"}:
            names.append(p.name)
    return sorted(names)


def normalize_book_name(name: str) -> str:
    mapping = {
        "Prediker": "Ecclesiastes",
        "Hooglied": "Song of Songs",
        "Klaagliederen": "Lamentations",
        "Ezechiël": "Ezekiel",
        "Daniël": "Daniel",
        "Joël": "Joel",
        "Obadja": "Obadiah",
        "Maleachi": "Malachi",
        "Mattheüs": "Matthew",
        "Markus": "Mark",
        "Lukas": "Luke",
        "Handelingen": "Acts",
        "Romeinen": "Romans",
        "Galaten": "Galatians",
        "Efeziërs": "Ephesians",
        "Filippenzen": "Philippians",
        "Colossenzen": "Colossians",
        "1Thessalonicen": "1 Thessalonians",
        "2Thessalonicen": "2 Thessalonians",
        "1Timotheüs": "1 Timothy",
        "2Timotheüs": "2 Timothy",
        "Filemon": "Philemon",
        "Hebreeën": "Hebrews",
        "Jakobus": "James",
        "Openbaring": "Revelation",
        "1Korinthiërs": "1 Corinthians",
        "2Korinthiërs": "2 Corinthians",
        "1Kronieken": "1 Chronicles",
        "2Kronieken": "2 Chronicles",
        "1Koningen": "1 Kings",
        "2Koningen": "2 Kings",
        "1Samuël": "1 Samuel",
        "2Samuël": "2 Samuel",
    }
    return mapping.get(name.strip(), name.strip())


def rtf_to_plain_text(raw: str) -> str:
    text = raw
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\\par[d]?\b", "\n", text)
    text = re.sub(r"\\tab\b", " ", text)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)

    def unicode_repl(match: re.Match) -> str:
        value = int(match.group(1))
        if value < 0:
            value += 65536
        try:
            return chr(value)
        except ValueError:
            return " "

    text = re.sub(r"\\u(-?\d+)\??", unicode_repl, text)
    text = re.sub(r"\\[a-zA-Z]+\-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("\\", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def parse_rtf_bible(raw: str) -> list[dict]:
    plain = rtf_to_plain_text(raw)
    lines = [line.strip() for line in plain.splitlines() if line.strip()]

    verses: list[dict] = []
    current_book = None
    current_chapter = None
    current_verse = None

    def flush_current() -> None:
        nonlocal current_verse
        if current_verse:
            current_verse["text"] = clean_olb_text(current_verse["text"])
            verses.append(current_verse)
            current_verse = None

    for line in lines:
        # Skip obvious non-content lines from RTF header remnants.
        if line.lower().startswith(("ansi", "fonttbl", "colortbl")):
            continue

        chapter_match = RTF_BOOK_CHAPTER_RE.match(line)
        if chapter_match:
            maybe_book, maybe_chapter = chapter_match.groups()
            if maybe_book and len(maybe_book) >= 2:
                flush_current()
                current_book = normalize_book_name(maybe_book)
                current_chapter = int(maybe_chapter)
                continue

        verse_match = RTF_VERSE_RE.match(line)
        if verse_match and current_book and current_chapter is not None:
            flush_current()
            verse_num, verse_text = verse_match.groups()
            current_verse = {
                "book_name": current_book,
                "chapter": int(current_chapter),
                "verse": int(verse_num),
                "text": verse_text.strip(),
            }
            continue

        if current_verse:
            current_verse["text"] = f"{current_verse['text']} {line}".strip()

    flush_current()
    return verses


def parse_exp_pairs(lines: list[str]) -> list[dict]:
    verses = []
    i = 0
    while i < len(lines):
        match = EXP_REF_RE.match(lines[i].strip())
        if not match:
            i += 1
            continue
        abbr, chapter, verse = match.groups()
        book_name = OLB_ABBR_TO_BOOK.get(abbr)
        if not book_name:
            i += 1
            continue
        text = lines[i + 1] if i + 1 < len(lines) else ""
        verses.append(
            {
                "book_name": book_name,
                "chapter": int(chapter),
                "verse": int(verse),
                "text": clean_olb_text(text),
            }
        )
        i += 2
    return verses


def parse_line_based(lines: list[str]) -> list[dict]:
    verses = []
    for line in lines:
        match = LINE_REF_RE.match(line.strip())
        if not match:
            continue
        abbr, chapter, verse, text = match.groups()
        book_name = OLB_ABBR_TO_BOOK.get(abbr)
        if not book_name:
            continue
        verses.append(
            {
                "book_name": book_name,
                "chapter": int(chapter),
                "verse": int(verse),
                "text": clean_olb_text(text),
            }
        )
    return verses


def transform_basisbijbel(source_text_path: Path, version_ext_path: Path, output_path: Path) -> None:
    if not source_text_path.exists():
        suggestions = suggest_input_files(source_text_path.parent)
        suggestion_text = ", ".join(suggestions) if suggestions else "no .exp/.txt/.rtf files found there"
        raise FileNotFoundError(
            f"Input file not found: {source_text_path}\n"
            f"Checked folder: {source_text_path.parent}\n"
            f"Found candidates: {suggestion_text}"
        )

    raw = source_text_path.read_text(encoding="utf-8", errors="replace")
    lines = [line.rstrip("\n\r") for line in raw.splitlines() if line.strip()]

    verses = parse_exp_pairs(lines)
    source_format = "OnLineBible .exp"
    if not verses:
        verses = parse_line_based(lines)
        source_format = "OnLineBible copied verse lines"
    if not verses and source_text_path.suffix.lower() == ".rtf":
        verses = parse_rtf_bible(raw)
        source_format = "OnLineBible RTF export"

    if not verses:
        raise ValueError(
            "No verses parsed. Expected .exp style lines ($$$ Ge 1:1), line-based refs (Ge 1:1 ...), or RTF export."
        )

    version = read_version_ext(version_ext_path)
    payload = {
        "metadata": {
            "name": version["name"],
            "shortname": "basisbijbel",
            "module": version["module"] or "basisbijbel",
            "lang": "nl",
            "year": 2025,
            "description": f"BasisBijbel export ({source_format}) ({version['publisher']}).",
            "source_format": source_format,
            "parse_mode": "strict",
        },
        "stats": {
            "exported_verse_count": len(verses),
        },
        "verses": verses,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote: {output_path}")
    print(f"Exported verses: {len(verses)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform BasisBijbel verse export (.exp or line-based text) to API JSON."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input file from OnLineBible export (.exp/.txt/.rtf).",
    )
    parser.add_argument(
        "--version-ext",
        default="non-transformed-data/BasisBijbel/Version.Ext",
        help="Path to Version.Ext for metadata.",
    )
    parser.add_argument(
        "--output",
        default="data/basisbijbel.json",
        help="Output JSON path.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    transform_basisbijbel(
        source_text_path=resolve_path(root, args.input),
        version_ext_path=resolve_path(root, args.version_ext),
        output_path=resolve_path(root, args.output),
    )


if __name__ == "__main__":
    main()
