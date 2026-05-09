# 📖 BijbelAPI

<p>
  <img src="https://img.shields.io/badge/Version-v1.2-blue?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/github/license/AlexLamper/BijbelAPI?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/github/issues/AlexLamper/BijbelAPI?style=for-the-badge" alt="Issues" />
</p>

**Dé #1 Nederlandse Bijbel API voor ontwikkelaars.**  
Een REST API om Bijbelteksten en Nederlandstalige commentaargegevens op te vragen over meerdere ondersteunde vertalingen. Gebouwd voor ontwikkelaars, theologen, studenten, kerken en digitale Bijbelprojecten.

---

## ✨ Features

- 🔀 **Random verses** retrieval  
- 🔍 **Text search** across the loaded Bible text  
- 📚 **Structure overview** of books, chapters, and verses  
- 📖 **Specific verses or passages** retrieval  
- 📅 **Daily text** generation (optional with seed)
- 🧠 **Smart reference parsing** for complex Bible references  
- 📝 **Commentary endpoint** on chapters and verses (Dutch source)  
- 💳 **Stripe billing endpoints** for paid API access  

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Homepage with API information + link to docs |
| GET | `/health` | Health check endpoint |
| GET | `/api/random` | Random verse |
| GET | `/api/verse?book=...&chapter=...&verse=...` | Specific verse |
| GET | `/api/passage?book=...&chapter=...&start=...&end=...` | Multiple verses |
| GET | `/api/books` | All books |
| GET | `/api/chapters?book=...` | Chapters in book |
| GET | `/api/verses?book=...&chapter=...` | Verse numbers in chapter |
| GET | `/api/search?query=...` | Search in Bible text |
| GET | `/api/daytext?seed=...` | Daily text, optional seed |
| GET | `/api/versions` | Available translations |
| GET | `/api/chapter?book=...&chapter=...` | Entire chapter |
| GET | `/api/commentary?source=...&book=...&chapter=...` | Get commentary for an entire chapter (e.g. `matthew_henry_nl`) |
| GET | `/api/commentary?source=...&book=...&chapter=...&verse=...` | Get commentary for a specific verse (e.g. `matthew_henry_nl`) |
| **POST** | **`/api/parse/reference`** | **Parse complex Bible reference** |
| **GET** | **`/api/parse/reference/{ref}`** | **Parse reference via URL** |
| **POST** | **`/api/parse/references`** | **Parse multiple references** |
| POST | `/billing/checkout-session` | Create Stripe checkout session |
| POST | `/billing/portal-session` | Create Stripe customer portal session |
| GET | `/billing/status` | Get billing status for API key |
| POST | `/stripe/webhook` | Stripe webhook receiver |

👉 All routes are documented via:
- `/docs` – Swagger UI
- `/redoc` – ReDoc UI

---

## 🧠 Smart Reference Parsing

The parsing endpoints handle complex Bible references that traditional APIs often struggle with:

### Supported Reference Types

| Type | Example | Description |
|------|---------|-------------|
| **Discontinuous ranges** | `Psalm 104:26-36,37` | Multiple verse ranges |
| **Cross-chapter** | `John 3:16-4:1` | References spanning chapters |
| **Chapter-only** | `Philemon 1-21` | Entire chapter ranges |
| **Optional verses** | `Luke 1:39-45[46-55]` | Main + optional verses |
| **Verse suffixes** | `Habakkuk 3:2-19a` | References with letter suffixes |
| **End references** | `Jeremiah 18:5-end` | From verse to end of chapter |

### Usage Examples

```bash
# Parse a complex reference
curl "https://bijbelapi.com/api/parse/reference/Psalm%20104:26-36,37?version=nbg1951"

# Parse via POST with custom version
curl -X POST "https://bijbelapi.com/api/parse/reference" \
  -H "Content-Type: application/json" \
  -d '{"reference": "Luke 1:39-45[46-55]", "version": "nld1939"}'

# Parse multiple references
curl -X POST "https://bijbelapi.com/api/parse/references" \
  -H "Content-Type: application/json" \
  -d '{"references": ["Psalm 104:26-36,37", "Jeremiah 18:1-11"], "version": "sv"}'
```

### Response Format

```json
{
  "reference": "Psalm 104:26-36,37",
  "parsed": true,
  "book": "Psalms",
  "chapter": "104",
  "verses": [
    {"verse": "26", "text": "There the ships go to and fro..."},
    {"verse": "27", "text": "All creatures look to you..."}
  ],
  "formatted_text": "26 There the ships go to and fro... 27 All creatures look to you..."
}
```

---

## 🌍 Supported Translations

Current supported translation keys:

- `nbg1951` (Nederlandse Bijbelvertaling NBG 1951)
- `nld1939` (Nederlandse Bijbelvertaling NLD 1939)
- `sv` (Statenvertaling)
- `bb` (BasisBijbel)

## 🧩 Expansion

Planned next steps:
- Adding more Dutch and multilingual Bible datasets.
- Adding richer plan/usage controls per API key.
- Improving technical and product documentation.
- Expanding tooling around data transformation and validation.

---

## 📜 License

This API is licensed under the [MIT License](LICENSE).

---

## 📎 Contact

- GitHub: [@AlexLamper](https://github.com/AlexLamper)
- Mail: `devlamper06@gmail.com`
- BijbelAPI: [https://bijbelapi.com](https://bijbelapi.com)

---

## 📌 Version

**Current Version**: `v1.2`
