"""
This module is responsible for building the gold layer in the data warehouse. 
The gold layer is the final layer in the data warehouse and is used for reporting and analysis. 
It contains the cleaned and transformed data that is ready for use by end-users.

Warning: 
- Ensure that the PostgreSQL credentials are correctly set in the environment variables.
- This code will force to overwrite the existing data in the gold schema.
"""



import duckdb
import os
from dotenv import load_dotenv
from datetime import datetime

con = duckdb.connect()

def connect_postgresql()-> None:
    try:

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

def build_gold()-> None:
    try:
        # create gold schema
        con.execute(f"""create schema if not exists pg_db.gold;""")

        # create general weather table
        con.execute(f"""create table if not exists pg_db.gold.weather(
        city Varchar NOT NULL,
        identifier VARCHAR NOT NULL,
        region VARCHAR NOT NULL ,
        last_updated TIMESTAMP,
        sunrise TIMESTAMP,
        sunset TIMESTAMP ,
        normal_high_c FLOAT,
        normal_low_c FLOAT,
        province VARCHAR,
        sunrise_str VARCHAR,
        sunset_str VARCHAR,
        time_create TIMESTAMP,
        PRIMARY KEY (city, identifier));""")

        # create day weather table
        con.execute(f"""create table if not exists pg_db.gold.weather_day(
        city Varchar NOT NULL,
        identifier VARCHAR NOT NULL,
        region VARCHAR,
        temp_c FLOAT,
        temp_class VARCHAR,
        humidity_pct FLOAT,
        uv_index FLOAT,
        uv_category VARCHAR,
        precip_mm FLOAT,
        precip_type VARCHAR,
        wind_speed_kmh FLOAT,
        wind_gust_kmh FLOAT,
        province VARCHAR,
        Primary key	(city, identifier));""")

        # create night weather table 
        con.execute(f"""create table if not exists pg_db.gold.weather_night(
        city Varchar NOT NULL,
        identifier VARCHAR NOT NULL,
        region VARCHAR,
        temp_c FLOAT,
        temp_class VARCHAR,
        humidity_pct FLOAT,
        precip_mm FLOAT,
        precip_type VARCHAR,
        wind_speed_kmh FLOAT,
        wind_gust_kmh FLOAT,
        province VARCHAR,
        Primary key	(city, identifier)
        );""")

        con.execute(f"""create table if not exists pg_db.gold.weather_difference(
        city Varchar NOT NULL,
        identifier VARCHAR NOT NULL,
        region VARCHAR,
        temp_c FLOAT,
        humidity_pct FLOAT,
        precip_mm FLOAT,
        wind_speed_kmh FLOAT,
        wind_gust_kmh FLOAT,
        province VARCHAR,
        Primary key	(city, identifier)
        );""")

        print(f"Success to build gold schema")

    except Exception as e:
        print('failt to build gold {e} ')

def insert_data_weather()-> None:
    time_create = datetime.now().replace(microsecond=0, second =0)
    try:
        con.execute(f"""Truncate pg_db.gold.weather""")   
        con.execute(f"""
            INSERT INTO pg_db.gold.weather
            SELECT DISTINCT ON (identifier)
                city,
                identifier,
                region,
                last_updated,
                sunrise,
                sunset,
                normal_high_c,
                normal_low_c,
                province,
                sunrise_str,
                sunset_str,
                $1::TIMESTAMP AS time_create
            FROM pg_db.silver.weather_daily""", [time_create])
        print('Success to insert data into weather table')
    except Exception as e:
        print(f'fail to insert data into weather table ')    

def insert_data_day()-> None:
    try:
        con.execute(f"""Truncate pg_db.gold.weather_day""")
        con.execute(f"""INSERT INTO pg_db.gold.weather_day
        SELECT
            city,
            identifier,
            region,
            temp_c,
            temp_class,
            humidity_pct,
            uv_index,
            uv_category,
            precip_mm,
            precip_type,
            wind_speed_kmh,
            wind_gust_kmh,
            province
        FROM pg_db.silver.weather_daily
        WHERE lower(period) = 'today'; """)

        print("Success to insert data to day table")
    except Exception as e:
        print(f'fail to insert data into day table {e}')

def insert_data_night()-> None:
    try:
        con.execute(f"""Truncate pg_db.gold.weather_night""")
        con.execute(f"""INSERT INTO pg_db.gold.weather_night
        SELECT
            city,
            identifier,
            region,
            temp_c,
            temp_class,
            humidity_pct,
            precip_mm,
            precip_type,
            wind_speed_kmh,
            wind_gust_kmh,
            province
        FROM pg_db.silver.weather_daily
        WHERE lower(period) = 'tonight'; """)

        print("Success to insert data to night table")
    except Exception as e:
        print(f"fail to insert data into night table {e}")

def insert_data_different()-> None:
    try:
        con.execute(f"""Truncate pg_db.gold.weather_difference""")
        con.execute(f"""Insert into pg_db.gold.weather_difference(
        SELECT
            gwd.city as city,
            gwd.identifier as identifier,
            gwd.region as region,
            abs(gwd.temp_c - gwn.temp_c) as temperature,
            abs(gwd.humidity_pct - gwn.humidity_pct) as humidity,
            abs(gwd.wind_speed_kmh - gwd.wind_speed_kmh) as wind_speed,
            abs(gwd.precip_mm - gwn.precip_mm) as precip,
            abs(gwd.wind_gust_kmh - gwn.wind_gust_kmh) as wind_gust,
            gwd.province as province
        
        from pg_db.gold.weather_day as gwd
        INNER join pg_db.gold.weather_night as gwn
        on gwn.identifier = gwd.identifier)
        """)

        print("Success to insert data to difference table")
    except Exception as e:
        print(f"fail to insert data into table difference {e}")

def run_gold()->None:
    try:
        connect_postgresql()
        build_gold()
        insert_data_weather()
        insert_data_day()
        insert_data_night()
        insert_data_different()
        print("Successful build gold layer")

    except Exception as e:
        print("failt to build gold layer {e}")
        
    con.close()
