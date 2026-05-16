"""
This module is responsible for fetching weather data from the Environment Canada API, 
transforming it into a structured format, and uploading it to Azure Blob Storage as a CSV file. The main steps include:
1. Fetching weather data from the API
2. Transforming the data into a structured format
3. Uploading the transformed data to Azure Blob Storage as a CSV file


Warning:
- Ensure that the Azure Blob Storage connection string and PostgreSQL credentials are correctly set in the environment variables.
- The script assumes that the data in Azure Blob Storage is in the expected CSV format.
"""

import requests
import csv
import io
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import requests
import pandas as pd


load_dotenv()
AZURE_CONNECTION_STRING = os.getenv('AZURE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')
URL = "https://api.weather.gc.ca/collections/citypageweather-realtime/items"

DAILY_PERIODS = {"Today", "Tonight", "This afternoon"}

def en(d: dict) -> any: # get engligh version for each features
    if isinstance(d, dict):
        return d.get("en")
    return d

def parse_normals(fg: dict) -> dict: # daily normal data 
    normals = fg.get("regionalNormals", {}).get("temperature", [])
    return {
        "normal_high_c": next((t.get("value", {}).get("en") for t in normals if t.get("class", {}).get("en") == "high"), None),
        "normal_low_c":  next((t.get("value", {}).get("en") for t in normals if t.get("class", {}).get("en") == "low"),  None),
    }

# def get_target_periods(): feature next day data
#     # Always looking at tomorrow from UTC midnight perspective
#     tomorrow       = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%A")
#     tomorrow_night = f"{tomorrow} night"
#     return {tomorrow, tomorrow_night}

# DAILY_PERIODS = get_target_periods()

DAILY_PERIODS = {"Today", "Tonight"}

def parse_forecasts(forecasts: list) -> list:# daily forecat data 
    result = []
    for f in forecasts:
        period_name = f.get("period", {}).get("textForecastName", {}).get("en")

        if period_name not in DAILY_PERIODS:
            continue

        temps = f.get("temperatures", {}).get("temperature", [])
        temp_val = temps[0].get("value", {}).get("en") if temps else None
        temp_cls = temps[0].get("class", {}).get("en") if temps else None
        uv = f.get("uv", {})
        precip = f.get("precipitation", {}).get("accumulation", {})
        winds    = f.get("winds", {}).get("periods", [])
        wind     = winds[0] if winds else {}

        result.append({
            "period": period_name,
            "temp_c": temp_val,
            "temp_class": temp_cls,
            "humidity_pct": f.get("relativeHumidity", {}).get("value", {}).get("en"),
            "wind_chill": f.get("windChill", {}).get("calculated", {}).get("en"),
            "uv_index": en(uv.get("index")) if uv else None,
            "uv_category": en(uv.get("category")) if uv else None,
            "precip_mm": en(precip.get("amount", {}).get("value")) if precip else None,
            "precip_type": en(precip.get("name")) if precip else None,
            "wind_speed_kmh": wind.get("speed", {}).get("value", {}).get("en"), 
            "wind_gust_kmh": wind.get("gust",  {}).get("value", {}).get("en")
        })
    return result

def parse_feature(feature: dict) -> dict: # daily features data 
    props  = feature.get("properties", {})
    fg = props.get("forecastGroup", {})
    riseset = props.get("riseSet", {})

    return {
        "city": en(props.get("name")),
        "identifier": props.get("identifier"),
        "region": en(props.get("region")),
        "last_updated": props.get("lastUpdated"),
        "sunrise": riseset.get("sunrise", {}).get("en"),
        "sunset": riseset.get("sunset", {}).get("en"),
        "normals": parse_normals(fg),
        "forecasts": parse_forecasts(fg.get("forecasts", [])),
    }

# Fetch

def get_all_canada_weather(limit: int = 1) -> list:
    params = {
        "f":     "json",
        "lang":  "en-CA",
        "limit": limit,
    }

    print(f"Fetching {limit} cities...")
    response = requests.get(url=URL, params=params)
    response.raise_for_status()

    data = response.json()
    features = data.get("features", [])

    print(f"Total cities available : {data.get('numberMatched')}")
    print(f"Fetched this call      : {data.get('numberReturned')}")

    return [parse_feature(f) for f in features]


CSV_FIELDS = [
    # Identity
    "city", "identifier", "region", "last_updated", "sunrise", "sunset",
    # Normals
    "normal_high_c", "normal_low_c",
    # Forecast (one row per period)
    "period", "temp_c", "temp_class",
    "humidity_pct", "wind_chill",
    "uv_index", "uv_category", "precip_mm", "precip_type",
    "wind_speed_kmh", "wind_gust_kmh",
]

def flatten_to_rows(report: list) -> list[dict]:
    rows = []
    for city in report:
        base = {
            "city": city["city"],
            "identifier": city["identifier"],
            "region": city["region"],
            "last_updated": city["last_updated"],
            "sunrise": city["sunrise"],
            "sunset": city["sunset"],
            "normal_high_c": city["normals"]["normal_high_c"],
            "normal_low_c": city["normals"]["normal_low_c"],
        }
        for forecast in city["forecasts"]:
            rows.append({**base, **forecast})   

    return rows

def convert_to_csv(report: list) -> str:
    rows = flatten_to_rows(report)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)

    return buffer.getvalue()


def upload_to_blob(csv_content: str) -> None:
    blob_name = "daily_weather.csv"

    blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    blob_client  = blob_service.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    try: 
        blob_client.upload_blob(# rewrite the data if the file already exist 
            csv_content.encode("utf-8"),
            overwrite=True,
            content_settings=None
        )
        print(f"Uploaded to Azure Blob: {CONTAINER_NAME}/{blob_name}")
    except Exception as e:
        print("error occur when pushing data {e}")


def run()-> None: 
    # report  = get_all_canada_weather(limit =1) retrive for only one city, for testing

    # fetching all cities in canada
    report = get_all_canada_weather(limit=2000)
    csv_content = convert_to_csv(report)

    # preview in dataframe
    df = pd.read_csv(io.StringIO(csv_content))
    print(df.isna().sum())  

    # upload to azure blob                      
    upload_to_blob(csv_content)
