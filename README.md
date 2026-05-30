# Car Finder — Azerbaijan

Web-based car search tool for **Turbo.az** (196 makes) and **AvtoBaku** (268 makes).  
Select filters → scrape direct listing links → open individual cars.

---

## Setup

```bash
# 1. Install dependencies (Python 3.8+)
pip install -r requirements.txt

# 2. Start the backend
python app.py
# Running on http://localhost:5000

# 3. Open the frontend
#    Double-click index.html  OR  open it in your browser
```

---

## Usage

| Control | Description |
|---|---|
| **Turbo.az / AvtoBaku** tabs | Switch between sources |
| Make → Model | Cascading dropdowns with full model lists |
| Price from/to | Filter by AZN price range |
| Color, City | Optional filters (shared between sources) |
| **Scrape direct links** checkbox | ON → backend fetches every matching car link and displays them as cards. OFF → just builds the filtered search URL and opens the site directly. |
| **Search** | Runs the search |
| Prev / Next | Paginate through results |

---

## Data Coverage

**Turbo.az:** 196 makes, full model lists (e.g., BMW has 79 models, Toyota has 57)  
**AvtoBaku:** 268 makes, full model lists (e.g., BMW has 61 models, Toyota has 182)

All filter options (colors, cities) work on both sources.

---

## Architecture

```
index.html          ← standalone frontend (all lookup data embedded)
app.py              ← Flask backend, port 5000
data.json           ← lookup tables (makes, models, colors, cities)
requirements.txt
```

**Endpoints:**

- `GET /api/search?source=turbo&make=BMW&model=320&...`  
  Scrapes listings, returns `{ ok, listings: [{url, title}], count, page, search_url, total_pages }`

- `GET /api/url?source=turbo&make=BMW&...`  
  Returns constructed search URL without scraping

- `GET /api/health`  
  Sanity check

---

## Notes

- **Turbo.az** uses `cloudscraper` to bypass Cloudflare protection.  
- **AvtoBaku** uses plain requests; may return 403 from outside Azerbaijan.  
- ~20 results per page; use Prev/Next to paginate.  
- The frontend works standalone (URL-only mode) even without the backend running.
- The "/bookmarks" bug is fixed — only actual listing URLs are scraped.
