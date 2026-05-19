# Steam-Game-Price-Monitor

```markdown
# Steam Game Price Monitor
> A lightweight, self-hosted web application engineered to track, log, and monitor video game pricing and discounts across the Steam ecosystem.

[![Live Project](https://img.shields.io/badge/Hugging_Face-Live_Demo-FFD21E?logo=huggingface&logoColor=black&style=for-the-badge)](https://huggingface.co/spaces/themehmi/Steam-Game-Price-Monitor)
[![Docker Support](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white&style=for-the-badge)](https://www.docker.com/)

---

## 🔗 Live Instance / Demo
A live version of this project is publically hosted and accessible via Hugging Face Spaces. You can test its interface, add tracking IDs, and check functionality directly from your browser:

👉 **[Launch Steam Game Price Monitor Live Demo](https://huggingface.co/spaces/themehmi/Steam-Game-Price-Monitor)**

---

## 📋 Table of Contents
1. [Project Architecture](#-project-architecture)
2. [Core Functional Blueprint](#-core-functional-blueprint)
3. [Technology Stack](#-technology-stack)
4. [Installation & Deployment](#-installation--deployment)
    - [Method A: Containerized Deployment via Docker (Recommended)](#method-a-containerized-deployment-via-docker-recommended)
    - [Method B: Native Python Environment Setup](#method-b-native-python-environment-setup)
5. [Database Schema Context](#-database-schema-context)

---

## 🏗️ Project Architecture

The repository layout follows a traditional monolithic MVC web design pattern tailored for low-overhead, self-hosted execution:

```text
Steam-Game-Price-Monitor/
├── templates/               # Frontend user interface assets (HTML layout engines)
├── Dockerfile               # Blueprint for containerization and automated deployments
├── README.md                # System documentation
├── app.py                   # Central Python application logic (Routing, API, Scheduler)
├── requirements.txt         # Declared dependencies for Python packages
└── steam_tracker.db         # Persistent SQLite transactional database file

```

### File Responsibilities:

* **`app.py`**: The programmatic core of the system. It handles internal web routing, regularly triggers connection loops with the Steam API, orchestrates CRUD operations with the database, and exposes the HTTP endpoints.
* **`templates/`**: Holds the frontend visual templates (comprising roughly **58.6%** of the codebase). These pages map and format data payloads sent from the backend to deliver an intuitive user dashboard.
* **`steam_tracker.db`**: An isolated, file-based relational database that eliminates the configuration overhead of standalone database servers.
* **`Dockerfile`**: Outlines steps to build a cross-platform image, freezing dependencies to guarantee reproducible execution behavior anywhere.

---

## ⚙️ Core Functional Blueprint

The micro-application implements a clean, automated extraction loop:

```
[ User Input: App ID / URL ] ──> [ app.py App Logic ] ──> [ Queries Steam Store API ]
                                        │                           │
                                        ▼                           ▼
[ HTML Dashboard Display ] <─── [ updates local DB ] <─────── [ JSON Response ]

```

1. **Registration**: Users provide a unique Steam **App ID** (e.g., `1091500` for *Cyberpunk 2077*) or paste a store link into the browser UI.
2. **API Consumption**: The backend periodically issues structured programmatic queries to the unauthenticated public Steam Big Picture storefront API:
```http
GET [https://store.steampowered.com/api/appdetails?appids=](https://store.steampowered.com/api/appdetails?appids=){APP_ID}

```


3. **Parsing & Serialization**: The backend extracts elements from the incoming JSON payload, including:
* `initial_price` (Base price prior to discounts)
* `final_price` (Current purchase price)
* `discount_percent` (Active markdown percentage)
* `currency` (Locational currency string)


4. **State Management**: Data variations are pushed to `steam_tracker.db`, maintaining historical records to flag drops or active historical lows.

---

## 💻 Technology Stack

* **Backend Runtime:** Python 3 (built with web frameworks like *Flask* or *FastAPI*)
* **Frontend Templating:** Semantic HTML / Jinja2 Template Engine
* **Database Engine:** SQLite (Persistent Engine)
* **Virtualization / Hosting:** Docker Engine & Hugging Face Spaces

---

## 🚀 Installation & Deployment

### Method A: Containerized Deployment via Docker (Recommended)

This approach completely isolates application states and prevents conflicting local global Python library version paths.

1. **Clone the target repository:**
```bash
git clone [https://github.com/themehmi/Steam-Game-Price-Monitor.git](https://github.com/themehmi/Steam-Game-Price-Monitor.git)
cd Steam-Game-Price-Monitor

```


2. **Compile the Docker Image blueprint:**
```bash
docker build -t steam-game-monitor:latest .

```


3. **Instantiate and execute the isolated container:**
```bash
docker run -d \
  -p 5000:5000 \
  --name steam-monitor-service \
  --restart unless-stopped \
  steam-game-monitor:latest

```


*(Note: If port `5000` is consumed by another system resource, modify the binding left parameter, e.g., `-p 8080:5000`)*.
4. **Access the application UI:**
Open an active browser instance and target: `http://localhost:5000`

---

### Method B: Native Python Environment Setup

Ideal for development environments or platforms with limited resource allocations.

1. **Clone the target repository:**
```bash
git clone [https://github.com/themehmi/Steam-Game-Price-Monitor.git](https://github.com/themehmi/Steam-Game-Price-Monitor.git)
cd Steam-Game-Price-Monitor

```


2. **Provision an isolated Virtual Environment Layer:**
```bash
# Create the environment
python3 -m venv venv

# Activate via Unix Shells (Linux/macOS)
source venv/bin/activate

# Activate via Windows PowerShell
.\venv\Scripts\Activate.ps1

```


3. **Install system-level script prerequisites:**
```bash
pip install --upgrade pip
pip install -r requirements.txt

```


4. **Execute the runtime main thread loop:**
```bash
python app.py

```


5. **Access the application UI:**
Navigate your web browser to the standard host loopback block: `http://127.0.0.1:5000`

---

## 🗃️ Database Schema Context

The underlying `steam_tracker.db` maintains relational properties tracking historical changes. The system automatically provisions tables on startup if they do not exist. Data structures map key variables like:

* `app_id` (INTEGER, Primary Key) — Unique item identifier matching Steam's records.
* `game_name` (TEXT) — Title descriptive string cache.
* `current_price` (INTEGER/REAL) — Active localized transactional value.
* `lowest_recorded_price` (INTEGER/REAL) — Global benchmark tracking for deal discovery thresholds.
* `last_updated` (TIMESTAMP) — Chronological tracking reference for API synchronization scripts.

```

```
