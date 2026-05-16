"""
This code defines the bronze layer of the data pipeline, 
responsible for ingesting raw weather data from Azure Blob Storage and storing it in a PostgreSQL database using DuckDB as an intermediary. 
The script includes functions to connect to PostgreSQL, read data from Azure Blob Storage, create the necessary table in the bronze schema, 
and insert the data into that table. The main function orchestrates these steps, ensuring that the bronze layer is built successfully.


Warning: 
- Ensure that the Azure Blob Storage connection string and PostgreSQL credentials are correctly set in the environment variables.
- The script assumes that the data in Azure Blob Storage is in the expected CSV format.
- This code will force to overwrite the existing data in the bronze schema. 
"""




import os
from dotenv import load_dotenv
import duckdb
import pandas as pd
import io
from azure.storage.blob import BlobServiceClient
from datetime import datetime

load_dotenv(override=False)

connect_string    = os.getenv('AZURE_CONNECTION_STRING')
container         = os.getenv('CONTAINER_NAME')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_USER     = os.getenv('POSTGRES_USER')

def get_con():
    con = duckdb.connect()
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute(f"""
        ATTACH 'host=postgres port=5432 dbname=weather_db
                user={POSTGRES_USER} password={POSTGRES_PASSWORD}'
        AS pg_db (TYPE POSTGRES)
    """)
    print("✓ Connected to PostgreSQL")
    return con

def read_from_blob() -> pd.DataFrame:
    try:
        blob_service = BlobServiceClient.from_connection_string(connect_string)
        blob_client  = blob_service.get_blob_client(container=container, blob="daily_weather.csv")
        data         = blob_client.download_blob().readall()
        df           = pd.read_csv(io.BytesIO(data))
        print(f"✓ Read {len(df)} rows from Azure Blob")
        return df
    except Exception as e:
        print(f"✗ Failed to read from Azure Blob: {e}")
        return pd.DataFrame()

def create_bronze_table(con) -> None:
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS pg_db.bronze")
        con.execute("""
            CREATE TABLE IF NOT EXISTS pg_db.bronze.weather_daily (
                city            VARCHAR,
                identifier      VARCHAR,
                region          VARCHAR,
                last_updated    TIMESTAMP,
                sunrise         TIMESTAMP,
                sunset          TIMESTAMP,
                normal_high_c   FLOAT,
                normal_low_c    FLOAT,
                period          VARCHAR,
                temp_c          FLOAT,
                temp_class      VARCHAR,
                humidity_pct    FLOAT,
                wind_chill      FLOAT,
                uv_index        FLOAT,
                uv_category     VARCHAR,
                precip_mm       FLOAT,
                precip_type     VARCHAR,
                wind_speed_kmh  FLOAT,
                wind_gust_kmh   FLOAT,
                time_create     TIMESTAMP
            )
        """)
        print("✓ Bronze table ready")
    except Exception as e:
        print(f"✗ Failed to create bronze schema/table: {e}")

def insert_data(con, df) -> None:
    try:
        con.register("weather_df", df)
        con.execute("TRUNCATE pg_db.bronze.weather_daily")
        con.execute("""
            INSERT INTO pg_db.bronze.weather_daily
            SELECT
                city, identifier, region,
                last_updated::TIMESTAMP,
                sunrise::TIMESTAMP,
                sunset::TIMESTAMP,
                normal_high_c::FLOAT,
                normal_low_c::FLOAT,
                period, temp_c::FLOAT, temp_class,
                humidity_pct::FLOAT,
                wind_chill::FLOAT,
                uv_index::FLOAT,
                uv_category,
                precip_mm::FLOAT,
                precip_type,
                wind_speed_kmh::FLOAT,
                wind_gust_kmh::FLOAT,
                time_create::TIMESTAMP
            FROM weather_df
        """)
        print(f"✓ Inserted {len(df)} rows into bronze.weather_daily")
    except Exception as e:
        print(f"✗ Failed to insert data: {e}")

def build_bronze() -> None:
    con = None
    try:
        con = get_con()

        df = read_from_blob()
        if df.empty:
            print("✗ No data from blob — aborting")
            return

        df['time_create'] = datetime.now().replace(microsecond=0, second=0)

        create_bronze_table(con)
        insert_data(con, df)

        print("✓ Bronze layer built successfully")
    except Exception as e:
        print(f"✗ Failed to build bronze layer: {e}")
    finally:
        if con:
            con.close()

