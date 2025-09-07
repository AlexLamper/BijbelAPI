# 📖 Scriptura API

<p>
  <img src="https://img.shields.io/badge/Version-v1.0-blue?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/github/license/AlexLamper/bijbel-api?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/github/issues/AlexLamper/bijbel-api?style=for-the-badge" alt="Issues" />
</p>

**A REST API for retrieving Bible texts from multiple Bible translations.**  
Supports various languages including Dutch, English, Afrikaans, and more. Developed for developers, theologians, students, and hobby projects who want to use Biblical texts digitally.

---

## ✨ Features

- 🔀 **Random verses** retrieval  
- 🔍 **Text search** across the entire Bible  
- 📚 **Structure overview** of books, chapters, and verses  
- 📖 **Specific verses or passages** retrieval  
- 📅 **Daily texts** generation (optional with seed)
- 🧠 **Smart reference parsing** for complex Bible references  

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Homepage with API information + link to docs |
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
| **POST** | **`/api/parse/reference`** | **Parse complex Bible reference** |
| **GET** | **`/api/parse/reference/{ref}`** | **Parse reference via URL** |
| **POST** | **`/api/parse/references`** | **Parse multiple references** |

👉 All routes are documented via:
- `/docs` – Swagger UI
- `/redoc` – ReDoc UI

---

## 🧠 Smart Reference Parsing

The new parsing endpoints handle complex Bible references that traditional APIs struggle with:

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
curl "http://localhost:8081/api/parse/reference/Psalm%20104:26-36,37?version=asv"

# Parse via POST with custom version
curl -X POST "http://localhost:8081/api/parse/reference" \
  -H "Content-Type: application/json" \
  -d '{"reference": "Luke 1:39-45[46-55]", "version": "asv"}'

# Parse multiple references
curl -X POST "http://localhost:8081/api/parse/references" \
  -H "Content-Type: application/json" \
  -d '{"references": ["Psalm 104:26-36,37", "Jeremiah 18:1-11"], "version": "asv"}'
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
    {"verse": "27", "text": "All creatures look to you..."},
    // ... more verses
  ],
  "formatted_text": "26 There the ships go to and fro... 27 All creatures look to you..."
}
```

---

## 🧩 Expansion

I plan to expand this API further, for example by:
- Adding more Bible translations in various languages.
- Adding additional API endpoints that can be useful.
- Writing better documentation.

---

## 📜 License

This API is licensed under the [MIT License](LICENSE).

---

## 📎 Contact

- GitHub: [@AlexLamper](https://github.com/AlexLamper)
- Mail: `devlamper06@gmail.com`
- Website: [https://www.scriptura-edu.com](https://www.scriptura-edu.com)

---

## 📌 Version

**Current Version**: `v1.0`
