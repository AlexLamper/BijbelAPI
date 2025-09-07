from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import os
import random
import hashlib
from datetime import date
from models import APIKey, Base
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

app = FastAPI(
    title="Bijbel API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# SlowAPI limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Custom error handler for better error messages
from fastapi.responses import JSONResponse
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
        content={"error": 422, "message": "Validation error", "details": exc.errors()},
    )

# Load environment variables from .env file
load_dotenv()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from /site
app.mount("/site", StaticFiles(directory="site"), name="site")

# Simple analytics middleware (log endpoint and IP)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    ip = request.client.host
    path = request.url.path
    logging.info(f"Request: {ip} {path}")
    response = await call_next(request)
    return response

# --- Multi-version support ---
def load_all_versions():
    versions_dir = "data"
    versions = {}
    for filename in os.listdir(versions_dir):
        if filename.endswith(".json"):
            version_name = filename.replace(".json", "")
            with open(os.path.join(versions_dir, filename), encoding="utf-8") as f:
                raw_data = json.load(f)
            structured_data = {}
            for verse in raw_data["verses"]:
                book = verse["book_name"]
                chapter = str(verse["chapter"])
                verse_number = str(verse["verse"])
                text = verse["text"]
                if book not in structured_data:
                    structured_data[book] = {}
                if chapter not in structured_data[book]:
                    structured_data[book][chapter] = {}
                structured_data[book][chapter][verse_number] = text
            versions[version_name] = {
                "meta": raw_data.get("metadata", {}),
                "data": structured_data
            }
    return versions

all_versions = load_all_versions()

def get_version_key(version: str):
    version = version.lower()
    for key, v in all_versions.items():
        meta = v["meta"]
        if (
            key.lower() == version
            or meta.get("shortname", "").lower() == version
            or meta.get("module", "").lower() == version
            or meta.get("name", "").lower() == version
        ):
            return key
    return None

def normalize_book_name(version_key, book_name):
    data = all_versions[version_key]["data"]
    for name in data:
        if name.lower().replace("ë", "e") == book_name.lower().replace("ë", "e"):
            return name
    return None

# Serve index.html on /
@app.get("/", response_class=FileResponse)
def serve_index():
    index_path = os.path.join("site", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html niet gevonden")

@app.get("/api/random")
@limiter.limit("20/minute")
def get_random_verse(request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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
def get_verse(book: str, chapter: str, verse: str, request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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
def get_passage(book: str, chapter: str, start: int, end: int, request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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
def get_books(request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
    return list(all_versions[version_key]["data"].keys())

@app.get("/api/chapters")
@limiter.limit("30/minute")
def get_chapters(book: str, request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
    data = all_versions[version_key]["data"]
    book_key = normalize_book_name(version_key, book)
    if not book_key:
        raise HTTPException(status_code=404, detail="Boek niet gevonden")
    return list(data[book_key].keys())

@app.get("/api/verses")
@limiter.limit("30/minute")
def get_verses(book: str, chapter: str, request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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
def search_verses(request: Request, query: str = Query(..., min_length=1), version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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
def get_daytext(request: Request, seed: str = None, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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
            "name": v["meta"].get("name", k),
            "shortname": v["meta"].get("shortname"),
            "module": v["meta"].get("module"),
            "lang": v["meta"].get("lang"),
            "year": v["meta"].get("year"),
            "description": v["meta"].get("description"),
        }
        for k, v in all_versions.items()
    ]

@app.get("/api/chapter")
@limiter.limit("20/minute")
def get_chapter(book: str, chapter: str, request: Request, version: str = "statenvertaling"):
    version_key = get_version_key(version)
    if not version_key:
        raise HTTPException(status_code=404, detail="Vertaling niet gevonden")
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

# --- API-key authenticatie ---

# Database setup (SQLite)
engine = create_engine("sqlite:///./test.db")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

api_key_header = APIKeyHeader(name="x-api-key")

def is_valid_key_in_db(key: str):
    session = SessionLocal()
    api_key = session.query(APIKey).filter_by(api_key=key, active=True).first()
    session.close()
    return api_key is not None

def verify_api_key(key: str = Security(api_key_header)):
    if not is_valid_key_in_db(key):
        raise HTTPException(status_code=403, detail="Invalid or expired key")

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
    version: str = "asv"

class ParseMultipleRequest(BaseModel):
    references: list[str]
    version: str = "asv"

# Parsing endpoints
@app.post("/api/parse/reference")
@limiter.limit("100/minute")
def parse_reference(request: Request, parse_req: ParseRequest):
    """Parse a single Bible reference with complex parsing support."""
    try:
        parser = ReferenceParser(all_versions=all_versions, version=parse_req.version)
        result = parser.parse(parse_req.reference, parse_req.version)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/parse/reference/{reference}")
@limiter.limit("100/minute")
def parse_single_reference(request: Request, reference: str, version: str = "asv"):
    """Parse a single Bible reference via GET request."""
    try:
        parser = ReferenceParser(all_versions=all_versions, version=version)
        result = parser.parse(reference, version)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/parse/references")
@limiter.limit("50/minute")
def parse_multiple_references(request: Request, parse_req: ParseMultipleRequest):
    """Parse multiple Bible references with complex parsing support."""
    try:
        parser = ReferenceParser(all_versions=all_versions, version=parse_req.version)
        results = []
        for reference in parse_req.references:
            result = parser.parse(reference, parse_req.version)
            results.append(result)
        return {"references": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/stripe/webhook")
@limiter.limit("5/minute")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    session = SessionLocal()

    if event["type"] == "checkout.session.completed":
        email = event["data"]["object"].get("customer_email")
        if email:
            api_key = str(uuid.uuid4())
            session.add(APIKey(user_email=email, api_key=api_key, active=True))
            session.commit()
            # TODO: Stuur API-key per e-mail naar gebruiker
    elif event["type"] in ["invoice.payment_failed", "customer.subscription.deleted"]:
        email = event["data"]["object"].get("customer_email")
        if email:
            key = session.query(APIKey).filter_by(user_email=email).first()
            if key:
                key.active = False
                session.commit()
    session.close()
    return {"status": "success"}
