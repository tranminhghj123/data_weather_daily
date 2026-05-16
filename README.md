[README.md](https://github.com/user-attachments/files/27834064/README.md)
# 🍁 Canada Daily Weather Pipeline

A fully automated data pipeline that fetches daily weather forecasts for all cities across Canada from Environment Canada's API, processes them through a medallion architecture (Bronze → Silver → Gold), and visualizes the results in a Streamlit dashboard — all orchestrated by Apache Airflow and containerized with Docker.

---

## 📐 Architecture

```
Environment Canada API
        │
        ▼
 api_request.py ──────────────────► Azure Blob Storage
        │                               (daily_weather.csv)
        │                                      │
        ▼                                      ▼
   [Airflow DAG]                         bronze.py
        │                            (bronze.weather_daily)
        │                                      │
        │                                      ▼
        │                                 silver.py
        │                            (silver.weather_daily)
        │                                      │
        │                                      ▼
        │                                  gold.py
        │                     ┌─────────────────────────────┐
        │                     │  gold.weather               │
        │                     │  gold.weather_day           │
        │                     │  gold.weather_night         │
        │                     │  gold.weather_difference    │
        │                     └─────────────────────────────┘
        │                                      │
        │                                      ▼
        └──────────────────────────── Streamlit Dashboard
```

---

## 📁 Project Structure

```
project/
├── airflow/
│   ├── dags.py                     # Airflow DAG definition
│   ├── dockerfile                  # Airflow Docker image
│   └── requirements-airflow.txt    # Airflow dependencies
├── extract/
│   ├── api_request.py              # Fetch from EC API → Azure Blob
│   └── test_api_request.py         # Local test runner
├── transform/
│   ├── bronze.py                   # Azure Blob → bronze.weather_daily
│   ├── silver.py                   # bronze → silver.weather_daily
│   └── gold.py                     # silver → gold tables
├── load/
│   ├── visualize.py                # Streamlit dashboard
│   ├── dockerfile                  # Streamlit Docker image
│   └── requirements-streamlit.txt  # Streamlit dependencies
├── logs/                           # Airflow logs (auto-generated)
├── plugins/                        # Airflow plugins (empty)
├── .env                            # Secrets (never commit this)
├── docker-compose.yml              # All services
└── init.sql                        # Creates airflow_db on startup
```

---

## 🗄️ Data Architecture

### Bronze Layer — Raw Data
```
bronze.weather_daily
    Raw data from Azure Blob CSV, minimal transformation
    One row per city per period (Today / Tonight)
```

### Silver Layer — Cleaned Data
```
silver.weather_daily
    - Dropped wind_chill column
    - Added province code from identifier
    - Added sunrise_str / sunset_str (HH:MM format)
    - UV index set to 0 for Tonight period
    - Null precip_mm filled with 0
    - Removed illogical data (normal_high < normal_low, sunrise > sunset)
```

### Gold Layer — Reporting Data
```
gold.weather            → One row per city (metadata, sunrise, sunset, normals)
gold.weather_day        → Daytime forecast per city
gold.weather_night      → Overnight forecast per city
gold.weather_difference → Absolute difference between day and night values
```

---

## ⚙️ Setup

### Prerequisites
- Docker Desktop
- Azure Storage Account with a blob container
- Environment Canada API access (public, no key needed)

### 1. Clone and configure
```bash
# Copy env template
cp .env.example .env
```

Edit `.env`:
```bash
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
AZURE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
CONTAINER_NAME=your_container_name
```

### 2. Start all services
```bash
docker compose up --build
```

### 3. Trigger the pipeline
```
http://localhost:8081
→ DAGs → canada_weather_pipeline → ▶ Trigger DAG
```

### 4. View the dashboard
```
http://localhost:8501
```

---

## 🌐 Services

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8081 | admin / admin |
| Streamlit | http://localhost:8501 | — |
| PostgreSQL | localhost:5431 | your .env values |

---

## 🔌 Connection Guide

| Tool | Host | Port |
|---|---|---|
| pgAdmin (local) | localhost | 5431 |
| DuckDB (local) | localhost | 5431 |
| Inside Docker containers | postgres | 5432 |

---

## ⏰ Schedule

The pipeline runs automatically at **05:00 UTC daily** — early enough to capture Today and Tonight forecasts for all Canadian cities across all timezones before any periods expire.

```
05:00 UTC = 01:00 EST = 22:00 PST (previous day)
```

To run manually at any time:
```
Airflow UI → ▶ Trigger DAG
```

---

## 📊 Data Source

**Environment Canada — MSC GeoMet OGC API**
```
https://api.weather.gc.ca/collections/citypageweather-realtime/items
```
- ~850 cities across Canada
- Updated every few hours by regional forecast offices
- No API key required
- Bilingual (EN/FR) — pipeline uses English values only

---

## 🛠️ Local Development

Run any script directly without Docker:

```bash
# Test API fetch
python3 extract/test_api_request.py

# Test bronze layer
python3 transform/bronze.py

# Test silver layer
python3 transform/silver.py

# Test gold layer
python3 transform/gold.py

# Run Streamlit locally
streamlit run load/visualize.py
```

Local scripts use `.env` defaults:
```
POSTGRES_HOST → localhost (default)
POSTGRES_PORT → 5431 (default)
```

---

## 🐳 Docker Commands

```bash
# Start all services
docker compose up --build

# Start in background
docker compose up -d

# Stop all services
docker compose down

# Stop and remove all data (full reset)
docker compose down -v

# Rebuild only one service
docker compose up --build streamlit
docker compose up --build airflow-webserver airflow-scheduler

# View logs
docker compose logs -f airflow-scheduler
docker compose logs -f streamlit

# Access container shell
docker exec -it data_weather_daily-airflow-scheduler-1 bash
```


