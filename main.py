# main.py
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi import Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import os
import gzip
import random
import hashlib
from datetime import date, datetime, timezone
from xml.sax.saxutils import escape as xml_escape
from typing import Optional
from models import APIKey, Base, BillingSubscription, StripeWebhookEvent
from dotenv import load_dotenv
import stripe
import uuid

# SlowAPI imports voor rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import logging

# Configure logging for analytics
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Define Base Directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_DIR = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)

app = FastAPI(
    title="BijbelAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# SlowAPI limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# API key headers must be defined before route declarations
api_key_header = APIKeyHeader(name="x-api-key")
optional_api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

# Custom error handler for better error messages
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logging.warning(f"HTTPException: {exc.status_code} {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.status_code, "message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.warning(f"ValidationError: {exc.errors()} - {request.url}")
    return JSONResponse(
        status_code=422,
        content={"error": 422, "message": "Validatiefout", "details": exc.errors()},
    )

# Load environment variables from .env file
load_dotenv()
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PRO_MONTHLY = os.getenv("STRIPE_PRICE_ID_PRO_MONTHLY", "")
STRIPE_PRICE_ID_PRO_YEARLY = os.getenv("STRIPE_PRICE_ID_PRO_YEARLY", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8081")
BILLING_ENFORCED = os.getenv("BILLING_ENFORCED", "false").lower() == "true"
DEBUG_BILLING = os.getenv("DEBUG_BILLING", "false").lower() == "true"


def public_base_url() -> str:
    """Canonical origin for sitemap, robots, OG URLs (override with CANONICAL_PUBLIC_URL)."""
    return (os.getenv("CANONICAL_PUBLIC_URL") or os.getenv("APP_BASE_URL") or "https://bijbelapi.com").rstrip("/")


# (path, priority 0..1, changefreq) — keep tight; no infinite API query URLs
_SITEMAP_ENTRIES = (
    ("/", "1.0", "weekly"),
    ("/docs", "0.85", "weekly"),
    ("/privacy.html", "0.35", "yearly"),
    ("/bron.html", "0.45", "yearly"),
)


def _inject_canonical_html(relative_path: str) -> HTMLResponse:
    path = os.path.join(BASE_DIR, "site", relative_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Pagina niet gevonden")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{CANONICAL_ORIGIN}}", public_base_url())
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
FREE_TIER_DAILY_LIMIT = int(os.getenv("FREE_TIER_DAILY_LIMIT", "5000"))
stripe.api_key = STRIPE_SECRET_KEY
FREE_TIER_USAGE = {}

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from /site
app.mount("/site", __import__("fastapi.staticfiles", fromlist=["StaticFiles"]).StaticFiles(directory=os.path.join(BASE_DIR, "site")), name="site")
app.mount("/public", __import__("fastapi.staticfiles", fromlist=["StaticFiles"]).StaticFiles(directory=os.path.join(BASE_DIR, "public")), name="public")

# Simple analytics middleware (log endpoint and IP)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    ip = request.client.host
    path = request.url.path
    logging.info(f"Request: {ip} {path}")
    response = await call_next(request)
    return response

# --- Multi-version support for Bible texts ---
DEFAULT_TRANSLATION = "nbg1951"
SUPPORTED_TRANSLATIONS = {"nbg1951", "bb", "sv", "nld1939"}
LEGACY_TRANSLATIONS = {"asv", "kjv"}
ENGLISH_COMMENTARY_KEYS = {"matthew-henry"}
TRANSLATION_ALIASES = {
    "statenvertaling": "sv",
    "stve": "sv",
    "nbg": "nbg1951",
    "nbg51": "nbg1951",
    "basisbijbel": "bb",
    "nlb": "bb",
}
COMMENTARY_SOURCE_ALIASES = {
    "matthew-henry-nl": "matthew_henry_nl",
}

def load_all_versions():
    versions_dir = DATA_DIR if os.path.isdir(DATA_DIR) else DEFAULT_DATA_DIR
    if versions_dir != DATA_DIR:
        logging.warning(f"DATA_DIR '{DATA_DIR}' niet gevonden, fallback naar '{DEFAULT_DATA_DIR}'.")
    versions = {}
    if not os.path.isdir(versions_dir):
        logging.warning(f"Versions dir '{versions_dir}' not found.")
        return versions
    for filename in os.listdir(versions_dir):
        if filename.endswith(".json"):
            version_name = filename.replace(".json", "")
            path = os.path.join(versions_dir, filename)
            try:
                with open(path, encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load version file {path}: {e}")
                continue
            structured_data = {}
            for verse in raw_data.get("verses", []):
                book = verse.get("book_name")
                chapter = str(verse.get("chapter"))
                verse_number = str(verse.get("verse"))
                text = verse.get("text")
                if book not in structured_data:
                    structured_data[book] = {}
                if chapter not in structured_data[book]:
                    structured_data[book][chapter] = {}
                structured_data[book][chapter][verse_number] = text
            normalized_name = version_name.lower()
            canonical_name = TRANSLATION_ALIASES.get(normalized_name, normalized_name)
            if normalized_name in LEGACY_TRANSLATIONS:
                logging.info(f"Sla legacy vertaling over: {version_name}")
                continue
            if canonical_name not in SUPPORTED_TRANSLATIONS:
                logging.info(f"Sla niet-ondersteunde vertaling over: {version_name}")
                continue
            versions[canonical_name] = {
                "meta": raw_data.get("metadata", {}),
                "data": structured_data
            }
    missing_translations = [
        code for code in sorted(SUPPORTED_TRANSLATIONS)
        if not any(key.lower() == code for key in versions.keys())
    ]
    if missing_translations:
        logging.warning(f"Ontbrekende verplichte vertalingen: {', '.join(missing_translations)}")
    return versions

all_versions = load_all_versions()

def get_version_key(version: str):
    version = version.lower()
    version = TRANSLATION_ALIASES.get(version, version)
    if version in LEGACY_TRANSLATIONS:
        return None
    for key, v in all_versions.items():
        if key.lower() not in SUPPORTED_TRANSLATIONS:
            continue
        meta = v.get("meta", {})
        if (
            key.lower() == version
            or meta.get("shortname", "").lower() == version
            or meta.get("module", "").lower() == version
            or meta.get("name", "").lower() == version
        ):
            return key
    return None

def resolve_version_key(version: str):
    """
    Resolve requested translation with safe fallbacks.
    Avoids unnecessary 404s when requested/default translation is missing.
    """
    version_key = get_version_key(version)
    if version_key:
        return version_key

    default_key = get_version_key(DEFAULT_TRANSLATION)
    if default_key:
        logging.info(f"Gevraagde vertaling '{version}' niet gevonden; fallback naar default '{default_key}'.")
        return default_key

    if all_versions:
        fallback_key = next(iter(all_versions.keys()))
        logging.warning(f"Gevraagde vertaling '{version}' niet gevonden; fallback naar beschikbare vertaling '{fallback_key}'.")
        return fallback_key

    raise HTTPException(status_code=503, detail="Geen vertalingen beschikbaar")

def normalize_book_name(version_key, book_name):
    data = all_versions.get(version_key, {}).get("data", {})
    for name in data:
        if name.lower().replace("ë", "e") == book_name.lower().replace("ë", "e"):
            return name
    return None

# --- Commentary loading (Matthew Henry, etc.) ---
COMMENTARIES_DIR = os.path.join(BASE_DIR, "commentaries")

def load_commentaries():
    commentaries = {}
    if not os.path.isdir(COMMENTARIES_DIR):
        logging.warning(f"Commentaries dir '{COMMENTARIES_DIR}' not found.")
        return commentaries
    
    # Walk through all directories to find JSON files
    for root, dirs, files in os.walk(COMMENTARIES_DIR):
        for fname in files:
            path = os.path.join(root, fname)
            raw = None
            try:
                if fname.endswith(".json"):
                    with open(path, encoding="utf-8") as f:
                        raw = json.load(f)
                elif fname.endswith(".json.gz"):
                    with gzip.open(path, "rt", encoding="utf-8") as f:
                        raw = json.load(f)
                
                if raw:
                    # identify key: meta.id or filename without ext
                    key = raw.get("meta", {}).get("id") or fname.replace(".json", "").replace(".gz", "")
                    if key in ENGLISH_COMMENTARY_KEYS or "\\en\\" in path.replace("/", "\\"):
                        logging.info(f"Sla Engelse commentary over: {key}")
                        continue
                    commentaries[key] = raw
                    logging.info(f"Loaded commentary '{key}' from {path}")
            except Exception as e:
                logging.warning(f"Failed to load commentary file {path}: {e}")
    return commentaries

all_commentaries = load_commentaries()

def normalize_commentary_book(source_key: str, book_name: str):
    """
    Try to match book_name (like 'Genesis') to an entry in the commentary file.
    Returns the stored book key (e.g. 'Genesis') or None.
    """
    src = all_commentaries.get(source_key)
    if not src:
        return None
    # First try case-insensitive name match
    for name in src.get("books", {}).keys():
        if name.lower().replace("ë","e") == book_name.lower().replace("ë","e"):
            return name
    # Then try matching by id field inside each book
    for name, info in src.get("books", {}).items():
        if info.get("id", "").lower() == book_name.lower():
            return name
    return None

# --- SEO: crawlers expect these at site root (not only under /site/)
@app.get("/robots.txt", response_class=PlainTextResponse)
@app.head("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    base = public_base_url()
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {base}/sitemap.xml",
            "",
        ]
    )
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")


@app.get("/sitemap.xml")
@app.head("/sitemap.xml")
def sitemap_xml():
    base = public_base_url()
    lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, priority, changefreq in _SITEMAP_ENTRIES:
        loc = f"{base}{path}"
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(loc)}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    xml_body = "\n".join(lines)
    return Response(content=xml_body, media_type="application/xml; charset=utf-8")


@app.get("/humans.txt", response_class=PlainTextResponse)
@app.head("/humans.txt", response_class=PlainTextResponse)
def humans_txt():
    path = os.path.join(BASE_DIR, "site", "humans.txt")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="humans.txt niet gevonden")
    with open(path, encoding="utf-8") as f:
        return PlainTextResponse(f.read(), media_type="text/plain; charset=utf-8")


@app.get("/favicon.ico")
@app.head("/favicon.ico")
def favicon():
    """
    Serve favicon from a stable root path expected by browsers.
    """
    candidate_paths = [
        os.path.join(BASE_DIR, "public", "favicon", "favicon.ico"),
        os.path.join(BASE_DIR, "favicon.ico"),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return FileResponse(path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="favicon.ico niet gevonden")


# --- Serve index.html on /
# HEAD is required for Cloudflare and many probes; GET-only returns 405.
@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
def serve_index():
    return _inject_canonical_html("index.html")


@app.get("/privacy.html", response_class=HTMLResponse)
@app.head("/privacy.html", response_class=HTMLResponse)
def privacy_page():
    return _inject_canonical_html("privacy.html")


@app.get("/bron.html", response_class=HTMLResponse)
@app.head("/bron.html", response_class=HTMLResponse)
def bron_page():
    return _inject_canonical_html("bron.html")


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}

# --- Existing Bible endpoints (unchanged) ---
@app.get("/api/random")
@limiter.limit("20/minute")
def get_random_verse(request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    book = random.choice(list(data.keys()))
    chapter = random.choice(list(data[book].keys()))
    verse = random.choice(list(data[book][chapter].keys()))
    return {
        "version": version_key,
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "text": data[book][chapter][verse],
    }

@app.get("/api/verse")
@limiter.limit("30/minute")
def get_verse(book: str, chapter: str, verse: str, request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    book_key = normalize_book_name(version_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden")
    try:
        text = data[book_key][chapter][verse]
        return {
            "version": version_key,
            "book": book_key,
            "chapter": chapter,
            "verse": verse,
            "text": text,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Vers niet gevonden")

@app.get("/api/passage")
@limiter.limit("10/minute")
def get_passage(book: str, chapter: str, start: int, end: int, request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    book_key = normalize_book_name(version_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden")
    try:
        verses = []
        for i in range(start, end + 1):
            verses.append({"verse": str(i), "text": data[book_key][str(chapter)][str(i)]})
        return {
            "version": version_key,
            "book": book_key,
            "chapter": chapter,
            "verses": verses,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Passage niet gevonden")

@app.get("/api/books")
@limiter.limit("30/minute")
def get_books(request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    return list(all_versions[version_key]["data"].keys())

@app.get("/api/chapters")
@limiter.limit("30/minute")
def get_chapters(book: str, request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    book_key = normalize_book_name(version_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden")
    return list(data[book_key].keys())

@app.get("/api/verses")
@limiter.limit("30/minute")
def get_verses(book: str, chapter: str, request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    book_key = normalize_book_name(version_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden")
    try:
        return list(data[book_key][chapter].keys())
    except KeyError:
        raise HTTPException(status_code=404, detail="Hoofdstuk niet gevonden")

@app.get("/api/search")
@limiter.limit("10/minute")
def search_verses(request: Request, query: str = Query(..., min_length=1), version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    results = []
    for book, chapters in data.items():
        for chapter, verses in chapters.items():
            for verse_number, text in verses.items():
                if query.lower() in text.lower():
                    results.append({
                        "book": book,
                        "chapter": chapter,
                        "verse": verse_number,
                        "text": text,
                    })
    return results

@app.get("/api/daytext")
@limiter.limit("5/minute")
def get_daytext(request: Request, seed: str = None, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    books = list(data.keys())
    base = seed if seed else date.today().isoformat()
    hash_val = int(hashlib.sha256(base.encode()).hexdigest(), 16)
    random.seed(hash_val)
    book = random.choice(books)
    chapter = random.choice(list(data[book].keys()))
    verse = random.choice(list(data[book][chapter].keys()))
    return {
        "version": version_key,
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "text": data[book][chapter][verse],
    }

@app.get("/api/versions")
@limiter.limit("10/minute")
def get_versions(request: Request):
    # Return metadata for all versions
    return [
        {
            "key": k,
            "name": v.get("meta", {}).get("name", k),
            "shortname": v.get("meta", {}).get("shortname"),
            "module": v.get("meta", {}).get("module"),
            "lang": v.get("meta", {}).get("lang"),
            "year": v.get("meta", {}).get("year"),
            "description": v.get("meta", {}).get("description"),
        }
        for k, v in all_versions.items()
    ]

@app.get("/api/chapter")
@limiter.limit("20/minute")
def get_chapter(book: str, chapter: str, request: Request, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    version_key = resolve_version_key(version)
    data = all_versions[version_key]["data"]
    book_key = normalize_book_name(version_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden")
    try:
        return {
            "version": version_key,
            "book": book_key,
            "chapter": chapter,
            "verses": data[book_key][chapter],
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Hoofdstuk niet gevonden")

# --- COMMENTARY ENDPOINT ---
@app.get("/api/commentary")
@limiter.limit("20/minute")
def get_commentary(request: Request, source: str, book: str, chapter: str, verse: str = None, x_api_key: Optional[str] = Security(optional_api_key_header)):
    ensure_paid_access(request, x_api_key)
    """
    Returns commentary for a chapter or specific verse.

    Example:
    /api/commentary?source=matthew-henry&book=Genesis&chapter=5
    -> { "1": "...", "2": "...", ... }

    /api/commentary?source=matthew-henry&book=Genesis&chapter=5&verse=3
    -> { "3": "..." }
    """
    source_key = COMMENTARY_SOURCE_ALIASES.get(source, source)
    src = all_commentaries.get(source_key)
    if not src:
        raise HTTPException(status_code=404, detail="Broncommentaar niet gevonden")
    book_key = normalize_commentary_book(source_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden in commentaar")
    chapters = src.get("books", {}).get(book_key, {}).get("chapters", {})
    if chapter not in chapters:
        raise HTTPException(status_code=404, detail="Hoofdstuk niet gevonden in commentaar")
    verses = chapters[chapter]  # dict of verse -> text
    if verse:
        if verse not in verses:
            raise HTTPException(status_code=404, detail="Vers niet gevonden in commentaar")
        return {verse: verses[verse]}
    return verses

# --- API-key authenticatie ---
# Database setup (SQLite)
db_path = os.path.join(BASE_DIR, "test.db")
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def is_valid_key_in_db(key: str):
    session = SessionLocal()
    api_key = session.query(APIKey).filter_by(api_key=key, active=True).first()
    session.close()
    return api_key is not None

def verify_api_key(key: str = Security(api_key_header)):
    if not is_valid_key_in_db(key):
        raise HTTPException(status_code=403, detail="Ongeldige of verlopen sleutel")


def _request_client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return "unknown"


def _enforce_free_tier_limit(request: Request) -> None:
    today = date.today().isoformat()
    ip = _request_client_ip(request)
    usage_key = (ip, today)
    count = FREE_TIER_USAGE.get(usage_key, 0) + 1
    FREE_TIER_USAGE[usage_key] = count
    if count > FREE_TIER_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                "Free tier limiet bereikt voor vandaag. "
                "Maak een betaald abonnement aan voor hogere limieten."
            ),
        )


def ensure_paid_access(request: Request, key: Optional[str]) -> None:
    """
    Enforce billing entitlement when BILLING_ENFORCED=true.
    """
    if not BILLING_ENFORCED:
        return
    if not key:
        _enforce_free_tier_limit(request)
        return

    session = SessionLocal()
    try:
        api_key = session.query(APIKey).filter_by(api_key=key, active=True).first()
        if not api_key:
            raise HTTPException(status_code=403, detail="Ongeldige of verlopen sleutel")
        subscription = (
            session.query(BillingSubscription)
            .filter_by(api_key_id=api_key.id)
            .order_by(BillingSubscription.updated_at.desc())
            .first()
        )
        if not subscription or subscription.status not in {"active", "trialing"}:
            raise HTTPException(status_code=402, detail="Geen actief abonnement")
    finally:
        session.close()

@app.get("/secure-data")
@limiter.limit("10/minute")
def secure_data(request: Request, _: str = Depends(verify_api_key)):
    return {"message": "Je bent geauthenticeerd!"}
# --- einde authenticatie ---

# Import parsing modules
from parsing.reference_parser import ReferenceParser
from pydantic import BaseModel

# Pydantic models for parsing requests
class ParseRequest(BaseModel):
    reference: str
    version: str = DEFAULT_TRANSLATION

class ParseMultipleRequest(BaseModel):
    references: list[str]
    version: str = DEFAULT_TRANSLATION


class CheckoutSessionRequest(BaseModel):
    email: str
    plan: str = "pro_monthly"


class PortalSessionRequest(BaseModel):
    email: str

# Parsing endpoints
@app.post("/api/parse/reference")
@limiter.limit("20/minute")
def parse_reference(request: Request, parse_req: ParseRequest, x_api_key: Optional[str] = Security(optional_api_key_header)):
    """Parse a single Bible reference with complex parsing support."""
    try:
        ensure_paid_access(request, x_api_key)
        version_key = resolve_version_key(parse_req.version)
        parser = ReferenceParser(all_versions=all_versions, version=version_key)
        result = parser.parse(parse_req.reference, version_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/parse/reference/{reference}")
@limiter.limit("20/minute")
def parse_single_reference(request: Request, reference: str, version: str = DEFAULT_TRANSLATION, x_api_key: Optional[str] = Security(optional_api_key_header)):
    """Parse a single Bible reference via GET request."""
    try:
        ensure_paid_access(request, x_api_key)
        version_key = resolve_version_key(version)
        parser = ReferenceParser(all_versions=all_versions, version=version_key)
        result = parser.parse(reference, version_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/parse/references")
@limiter.limit("10/minute")
def parse_multiple_references(request: Request, parse_req: ParseMultipleRequest, x_api_key: Optional[str] = Security(optional_api_key_header)):
    """Parse multiple Bible references with complex parsing support."""
    try:
        ensure_paid_access(request, x_api_key)
        version_key = resolve_version_key(parse_req.version)
        parser = ReferenceParser(all_versions=all_versions, version=version_key)
        results = []
        for reference in parse_req.references:
            result = parser.parse(reference, version_key)
            results.append(result)
        return {"references": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_price_id_for_plan(plan: str) -> str:
    plan_map = {
        "pro_monthly": STRIPE_PRICE_ID_PRO_MONTHLY,
        "pro_yearly": STRIPE_PRICE_ID_PRO_YEARLY,
    }
    price_id = plan_map.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Onbekend of niet geconfigureerd prijsplan")
    return price_id


def _mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def _ensure_local_billing_debug_access(request: Request) -> None:
    if not DEBUG_BILLING:
        raise HTTPException(status_code=404, detail="Niet gevonden")
    host = _request_client_ip(request)
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Alleen lokaal beschikbaar")


def record_processed_event(session, event_id: str, event_type: str) -> bool:
    """
    Returns True when event is already processed, False when newly recorded.
    """
    existing = session.query(StripeWebhookEvent).filter_by(stripe_event_id=event_id).first()
    if existing:
        return True
    session.add(StripeWebhookEvent(stripe_event_id=event_id, event_type=event_type))
    session.commit()
    return False


@app.post("/billing/checkout-session")
@limiter.limit("10/minute")
def create_checkout_session(request: Request, payload: CheckoutSessionRequest):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is niet geconfigureerd")
    price_id = get_price_id_for_plan(payload.plan)
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=payload.email,
            success_url=f"{APP_BASE_URL}/?checkout=success",
            cancel_url=f"{APP_BASE_URL}/?checkout=cancelled",
        )
        logging.info(f"Stripe checkout session created: id={session.id} email={payload.email} plan={payload.plan}")
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as exc:
        logging.exception(f"Stripe checkout failed for email={payload.email} plan={payload.plan}")
        raise HTTPException(status_code=400, detail=f"Stripe checkout mislukt: {exc}")


@app.post("/billing/portal-session")
@limiter.limit("10/minute")
def create_portal_session(request: Request, payload: PortalSessionRequest):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is niet geconfigureerd")
    try:
        customers = stripe.Customer.list(email=payload.email, limit=1)
        if not customers.data:
            raise HTTPException(status_code=404, detail="Geen Stripe-klant gevonden voor dit e-mailadres")
        portal = stripe.billing_portal.Session.create(
            customer=customers.data[0].id,
            return_url=APP_BASE_URL,
        )
        logging.info(f"Stripe portal session created for email={payload.email}")
        return {"portal_url": portal.url}
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception(f"Stripe portal failed for email={payload.email}")
        raise HTTPException(status_code=400, detail=f"Stripe portal mislukt: {exc}")


@app.get("/billing/status")
@limiter.limit("30/minute")
def billing_status(request: Request, key: str = Security(api_key_header)):
    session = SessionLocal()
    try:
        api_key = session.query(APIKey).filter_by(api_key=key).first()
        if not api_key:
            raise HTTPException(status_code=404, detail="API-sleutel niet gevonden")
        subscription = (
            session.query(BillingSubscription)
            .filter_by(api_key_id=api_key.id)
            .order_by(BillingSubscription.updated_at.desc())
            .first()
        )
        if not subscription:
            return {"active": False, "plan": "free", "status": "inactive"}
        return {
            "active": subscription.status in {"active", "trialing"},
            "plan": subscription.plan_name,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        }
    finally:
        session.close()


@app.get("/billing/plans")
@limiter.limit("30/minute")
def billing_plans(request: Request):
    return {
        "currency": "eur",
        "free": {
            "price_monthly": 0,
            "daily_request_limit": FREE_TIER_DAILY_LIMIT,
            "requires_api_key": False,
            "description": "Generous free tier met daglimiet per IP.",
        },
        "pro_monthly": {
            "price_id": STRIPE_PRICE_ID_PRO_MONTHLY or "configure_in_env",
            "daily_request_limit": "hoog / op planbasis",
            "requires_api_key": True,
        },
        "pro_yearly": {
            "price_id": STRIPE_PRICE_ID_PRO_YEARLY or "configure_in_env",
            "daily_request_limit": "hoog / op planbasis",
            "requires_api_key": True,
        },
        "billing_enforced": BILLING_ENFORCED,
    }

@app.post("/stripe/webhook")
@limiter.limit("5/minute")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET ontbreekt")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logging.warning(f"Stripe webhook signature verify failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    session = SessionLocal()
    try:
        event_id = event.get("id")
        event_type = event.get("type")
        if not event_id or not event_type:
            raise HTTPException(status_code=400, detail="Ongeldig Stripe event")
        logging.info(f"Stripe webhook received: id={event_id} type={event_type}")
        if record_processed_event(session, event_id, event_type):
            return {"status": "al_verwerkt"}

        data = event.get("data", {}).get("object", {})
        email = data.get("customer_email")
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("subscription") or data.get("id")
        plan_name = "pro"
        stripe_price_id = None
        items = data.get("items", {}).get("data", [])
        if items and items[0].get("price"):
            stripe_price_id = items[0]["price"].get("id")
            if stripe_price_id == STRIPE_PRICE_ID_PRO_YEARLY:
                plan_name = "pro_yearly"
            else:
                plan_name = "pro_monthly"

        if event_type == "checkout.session.completed" and email:
            api_key_obj = session.query(APIKey).filter_by(user_email=email).first()
            if not api_key_obj:
                api_key_obj = APIKey(user_email=email, api_key=str(uuid.uuid4()), active=True)
                session.add(api_key_obj)
                session.commit()
                session.refresh(api_key_obj)
            else:
                api_key_obj.active = True
                session.commit()

            subscription = (
                session.query(BillingSubscription)
                .filter_by(api_key_id=api_key_obj.id)
                .order_by(BillingSubscription.updated_at.desc())
                .first()
            )
            if not subscription:
                subscription = BillingSubscription(
                    api_key_id=api_key_obj.id,
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                    stripe_price_id=stripe_price_id,
                    plan_name=plan_name,
                    status="active",
                )
                session.add(subscription)
            else:
                subscription.stripe_customer_id = stripe_customer_id or subscription.stripe_customer_id
                subscription.stripe_subscription_id = stripe_subscription_id or subscription.stripe_subscription_id
                subscription.stripe_price_id = stripe_price_id or subscription.stripe_price_id
                subscription.plan_name = plan_name
                subscription.status = "active"
                subscription.updated_at = datetime.utcnow()
            session.commit()

        elif event_type in {"customer.subscription.updated", "invoice.paid"}:
            if stripe_subscription_id:
                subscription = session.query(BillingSubscription).filter_by(stripe_subscription_id=stripe_subscription_id).first()
                if subscription:
                    subscription.status = "active"
                    subscription.updated_at = datetime.utcnow()
                    session.commit()

        elif event_type in {"invoice.payment_failed", "customer.subscription.deleted"}:
            if stripe_subscription_id:
                subscription = session.query(BillingSubscription).filter_by(stripe_subscription_id=stripe_subscription_id).first()
                if subscription:
                    subscription.status = "past_due" if event_type == "invoice.payment_failed" else "canceled"
                    subscription.updated_at = datetime.utcnow()
                    session.commit()
                    api_key_obj = session.query(APIKey).filter_by(id=subscription.api_key_id).first()
                    if api_key_obj:
                        api_key_obj.active = event_type != "customer.subscription.deleted"
                        session.commit()
        return {"status": "succes"}
    finally:
        session.close()


@app.get("/billing/debug/config")
@limiter.limit("30/minute")
def billing_debug_config(request: Request):
    """
    Local debug endpoint for Stripe configuration checks.
    Enabled only when DEBUG_BILLING=true and localhost access.
    """
    _ensure_local_billing_debug_access(request)
    return {
        "billing_enforced": BILLING_ENFORCED,
        "debug_billing": DEBUG_BILLING,
        "app_base_url": APP_BASE_URL,
        "stripe_secret_key_set": bool(STRIPE_SECRET_KEY),
        "stripe_secret_key_masked": _mask_secret(STRIPE_SECRET_KEY),
        "stripe_webhook_secret_set": bool(STRIPE_WEBHOOK_SECRET),
        "stripe_webhook_secret_masked": _mask_secret(STRIPE_WEBHOOK_SECRET),
        "stripe_price_id_pro_monthly_set": bool(STRIPE_PRICE_ID_PRO_MONTHLY),
        "stripe_price_id_pro_monthly": STRIPE_PRICE_ID_PRO_MONTHLY or "",
        "stripe_price_id_pro_yearly_set": bool(STRIPE_PRICE_ID_PRO_YEARLY),
        "stripe_price_id_pro_yearly": STRIPE_PRICE_ID_PRO_YEARLY or "",
    }


@app.get("/billing/debug/ping")
@limiter.limit("60/minute")
def billing_debug_ping(request: Request):
    """
    Lightweight local debug ping for frontend diagnostics.
    Enabled only when DEBUG_BILLING=true and localhost access.
    """
    _ensure_local_billing_debug_access(request)
    return {
        "ok": True,
        "debug_billing": DEBUG_BILLING,
        "billing_enforced": BILLING_ENFORCED,
        "app_base_url": APP_BASE_URL,
    }


@app.get("/billing/debug/email-status")
@limiter.limit("30/minute")
def billing_debug_email_status(request: Request, email: str):
    """
    Local debug endpoint: inspect API key/subscription state for email.
    Enabled only when DEBUG_BILLING=true and localhost access.
    """
    _ensure_local_billing_debug_access(request)
    session = SessionLocal()
    try:
        api_key = session.query(APIKey).filter_by(user_email=email).first()
        if not api_key:
            return {"email": email, "exists": False}
        subscription = (
            session.query(BillingSubscription)
            .filter_by(api_key_id=api_key.id)
            .order_by(BillingSubscription.updated_at.desc())
            .first()
        )
        return {
            "email": email,
            "exists": True,
            "api_key_active": bool(api_key.active),
            "api_key_masked": _mask_secret(api_key.api_key, visible=6),
            "subscription": None if not subscription else {
                "plan_name": subscription.plan_name,
                "status": subscription.status,
                "stripe_customer_id": subscription.stripe_customer_id,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "stripe_price_id": subscription.stripe_price_id,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            },
        }
    finally:
        session.close()
