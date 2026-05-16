"""
This module is responsible for building the silver layer of the data warehouse. 
It connects to the PostgreSQL database, transforms the data from the bronze layer, and inserts the transformed data into the silver layer. 
The silver layer is designed to be more refined and structured than the bronze layer, making it easier for analysis and reporting. 
The transformations include cleaning the data, deriving new columns, and ensuring data integrity.


Warning:
- Ensure that the PostgreSQL credentials are correctly set in the environment variables.
- This code will force to overwrite the existing data in the silver schema.
"""




import os
from dotenv import load_dotenv
import duckdb
from datetime import datetime


con = duckdb.connect()
def connect_postgresql()-> None:
    try:
        load_dotenv()

        POSTGRES_USER = os.getenv('POSTGRES_USER')
        POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

        try:
            con.execute("INSTALL postgres; LOAD postgres;")
            con.execute(f"ATTACH 'host=postgres port=5432 dbname=weather_db user={POSTGRES_USER} password={POSTGRES_PASSWORD}' AS pg_db (TYPE POSTGRES)")
            print("successful connect postgressql")
        except Exception as e:
            print(f"error to connect duckdb to postgressql: {e}")
    
    except Exception as e:
        print(f"fail to load env file {e}")


def data_transform():

    try:

        bronze_df = con.execute("""Select * from pg_db.bronze.weather_daily""").df()

        silver_df = bronze_df.drop(columns= ["wind_chill"])
        # gettng province code
        silver_df['province'] = silver_df['identifier'].apply(lambda x: x.split("-")[0].strip() if "-" in x else None)

        # getting sunset and sunrise hour and minute
        silver_df['sunrise_str'] = silver_df['sunrise'].apply(lambda x: x.strftime("%H:%M")  if x else None)
        silver_df['sunset_str'] = silver_df['sunset'].apply(lambda x: x.strftime("%H:%M") if x else None)

        # Set uv_index at night =0
        silver_df.loc[(silver_df['period']=='Tonight', 'uv_index')] =0
        silver_df.loc[(silver_df['period']=="Tonight", 'uv_category')] = 'low'

        # remove null value in precip as no rain day
        silver_df['precip_mm'] = silver_df['precip_mm'].fillna(0)

        # remove unlogical data
        silver_df = silver_df[silver_df['normal_high_c'] >= silver_df['normal_low_c']]
        silver_df = silver_df[silver_df['sunrise'] <= silver_df['sunset']]

        # time insert data update
        silver_df['time_create'] = datetime.now().replace(microsecond=0, second =0)

        print("successful transform data")

        return silver_df
    except Exception as e:
        print(f"fail to transform data {e}")

def build_silver_layer()-> None: # create schema silver and weather daily table 
    try:

        con.execute("""Create schema if not exists pg_db.silver""")

        con.execute(f"""Create table if not exists pg_db.silver.weather_daily(
            city            VARCHAR         NOT NULL,
            identifier      VARCHAR         NOT NULL,
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
            uv_index        FLOAT,
            uv_category     VARCHAR,
            precip_mm       FLOAT,
            precip_type     VARCHAR,
            wind_speed_kmh  FLOAT,
            wind_gust_kmh   FLOAT,
            province        VARCHAR,
            sunrise_str     VARCHAR,
            sunset_str      VARCHAR,
            time_create     TIMESTAMP,
            PRIMARY KEY (identifier, period, last_updated))
""")
    except Exception as e:
        print(f"fail to create silver schema or silver.weather_daily table {e}")
    
def insert_data(df)-> None: 
    try:
        con.register("weather_df", df)

        con.execute(f"TRUNCATE pg_db.silver.weather_daily")# remove old data before inserting 
        con.execute(f"""Insert into pg_db.silver.weather_daily    
            Select 
                city,
                identifier,
                region,
                last_updated::TIMESTAMP,
                sunrise::TIMESTAMP,
                sunset::TIMESTAMP,
                normal_high_c::FLOAT,
                normal_low_c::FLOAT,
                period,
                temp_c::FLOAT,
                temp_class,
                humidity_pct::FLOAT,
                uv_index::FLOAT,
                uv_category,
                precip_mm::FLOAT,
                precip_type,
                wind_speed_kmh::FLOAT,
                wind_gust_kmh::FLOAT,
                province,
                sunrise_str,
                sunset_str,
                time_create::TIMESTAMP
            from weather_df
        """
        )
        print("successful insert data")
    except Exception as e:
        print("fail to insert data {e}")

def run_silver():
    try:

        connect_postgresql()
        build_silver_layer()
        silver_df = data_transform()
        insert_data(silver_df) 

        print("Success build silver layer")
    except Exception as e:
        print(f'fail to build silver layer {e}')
    con.close()


