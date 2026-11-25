# AgriTwin-RAG

**A Digital Twin-Based Precision Agriculture Platform** integrating real-time weather telemetry, soil intelligence, Sentinel-2 satellite NDVI monitoring, deep-learning crop disease detection with Explainable AI (Grad-CAM), biophysical farm risk prediction, and a multilingual Retrieval-Augmented Generation (RAG) agricultural assistant.

---

## Key Features

- **Precision Farm Digital Twin:** Centralizes farm location, crop profile, live weather, soil properties, and satellite vegetation vigor into a unified state (`FarmContext`) with multi-tenant farmer isolation via SQLite.
- **Sentinel-2 Satellite Intelligence & NDVI Monitoring:**
  - Fetches real **Sentinel-2 Level-2A** multispectral imagery via Microsoft Planetary Computer STAC (with SAS token authentication and progressive search window expansion) and Element 84 Earth Search AWS STAC fallback.
  - Computes spatial-median **NDVI** from Band 8 (NIR, 842 nm) and Band 4 (Red, 665 nm) using $\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}$ and serves live true-color RGB satellite previews.
- **Live Weather & Location Services:**
  - Real-time meteorological telemetry via **OpenWeather API** and interactive farm coordinate selection/reverse geocoding via **Google Maps / Nominatim**.
- **Soil Intelligence:**
  - Rhizosphere soil profile retrieval (pH, moisture/water content, clay/sand/silt, organic carbon, nitrogen) powered by **ISRIC SoilGrids 2.0**.
- **AI Crop Disease Detection & Explainable AI (XAI):**
  - PyTorch image classification model (`models/rice_disease_model.pth`) trained to detect 5 rice leaf classes: `Bacterial Leaf Blight`, `Brown Spot`, `Leaf Blast`, `Sheath Blight`, and `Healthy`.
  - Generates **Grad-CAM** visual explanations and pairs detections with ICAR-grounded treatment advisories.
- **Multilingual RAG Agricultural Copilot:**
  - Answers farmer queries in **English, Telugu, Tamil, and Hindi** (text & voice) using **ChromaDB** vector search over `rag/documents/icar_crop_management.pdf` (`sentence-transformers` embeddings) + **Groq LLM** inference, with intelligent query routing to live farm telemetry.
- **4-Tier Farm Risk Prediction & Reporting:**
  - Evaluates Irrigation, Crop Stress, Disease, and Overall farm risk, generates prioritized agronomic recommendations, and exports farm reports.

---

## Tech Stack

- **Backend:** Python 3.11, Flask 3.0.3, SQLite (`backend/database/db.py`)
- **Frontend:** HTML5, CSS3, Bootstrap 5, Vanilla JavaScript (`frontend/`)
- **RAG & LLM:** ChromaDB, Sentence-Transformers, PyMuPDF, Groq API
- **Machine Learning & Vision:** PyTorch, Torchvision, Grad-CAM, NumPy, Pillow
- **External APIs & Data Sources:**
  - Microsoft Planetary Computer STAC & Data API + Earth Search AWS STAC (Sentinel-2 L2A)
  - OpenWeather API (Live weather)
  - ISRIC SoilGrids 2.0 (Soil properties)
  - Google Maps API (Location & geocoding)

---

## Project Structure

```text
AgriTwin-RAG/
├── backend/
│   ├── app.py                     # Main Flask application & REST API endpoints
│   ├── database/                  # SQLite schema & multi-tenant DB helpers (db.py, agritwin.db)
│   ├── services/                  # Disease inference & Grad-CAM XAI (disease_service.py)
│   ├── rag/                       # RAG pipeline, query router, LLM & farm context
│   ├── models/                    # Trained PyTorch weights & class_names.json
│   └── test_*.py                  # Backend, auth, RAG, and endpoint test suites
├── frontend/
│   ├── index.html                 # Landing entry page
│   ├── dashboard.html             # Farmer precision agriculture dashboard
│   ├── satellite.html             # Sentinel-2 imagery & NDVI monitoring page
│   ├── crop-disease.html          # Leaf disease upload & Grad-CAM diagnostics
│   ├── assistant.html             # Multilingual voice & text RAG copilot
│   ├── weather.html, soil.html, digital-twin.html, prediction.html, ...
│   ├── css/                       # Master design system & page styles
│   └── js/                        # API client, FarmState manager, charts, voice & auth
├── rag/
│   ├── documents/                 # ICAR crop management PDF knowledge base
│   ├── retriever.py               # ChromaDB vector retriever
│   ├── query_router.py            # Intent classification (telemetry vs ICAR RAG)
│   ├── llm_service.py             # Groq LLM integration & multilingual response
│   ├── direct_responder.py        # Direct live-telemetry responses
│   └── farm_context.py            # Unified farm context builder
├── models/                        # Rice disease model weights & class labels
├── scripts/                       # Verification, satellite test, and security scanner scripts
├── requirements.txt               # Python dependencies
└── .gitignore                     # Excludes .env, .venv, raw image datasets, and caches
```

---

## Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/punatiganesh/AgriTwin-RAG.git
cd AgriTwin-RAG
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root (and/or `backend/.env`) with your API keys:

```env
SECRET_KEY=your-flask-secret-key
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-20b
OPENWEATHER_API_KEY=your-openweather-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
# Optional (for higher Planetary Computer rate limits):
PLANETARY_COMPUTER_API_KEY=
```

### 4. Run the Application
```bash
cd backend
python app.py
```
Then open your browser at **http://127.0.0.1:5000**.

---

## Core API Endpoints

| Category | Endpoint | Method | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/user` | `POST` / `GET` | Farmer registration, session auth, and profile |
| **Farm Context** | `/api/farm-context`, `/api/farm/location`, `/api/farm/refresh` | `GET` / `POST` / `PUT` | Manage farm coordinates, crop details, and telemetry |
| **Satellite & NDVI** | `/api/ndvi`, `/api/satellite/ndvi`, `/api/satellite/image` | `GET` | Sentinel-2 L2A NDVI calculation & RGB visual preview |
| **Weather & Soil** | `/api/weather`, `/api/soil` | `GET` | OpenWeather telemetry & ISRIC SoilGrids profile |
| **Crop Disease** | `/api/disease/predict`, `/api/disease/status`, `/api/disease/advisory` | `POST` / `GET` | Rice disease classification, Grad-CAM, and ICAR advisory |
| **RAG Assistant** | `/api/rag/chat`, `/api/rag/health` | `POST` / `GET` | Multilingual agricultural Q&A grounded in ICAR PDF & live data |
| **Risk & Reports** | `/api/farm-risk`, `/api/recommendations`, `/api/reports/generate` | `GET` / `POST` | 4-tier risk evaluation, recommendations, and reports |

---

## Running Tests

From the `backend/` directory:
```bash
python test_auth_system.py
python -m unittest test_dynamic_location.py
```

To verify Sentinel-2 satellite retrieval & NDVI calculation from the project root:
```bash
python scripts/verify_satellite_ndvi.py
```
