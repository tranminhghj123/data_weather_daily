from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys

 
sys.path.insert(0, "/opt/airflow")
 
default_args = {
    "owner": "Mike",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}
 
with DAG(
    dag_id="canada_weather_pipeline",
    default_args=default_args,
    description="EC Weather: API → Bronze → Silver → Gold",
    schedule_interval="@daily",    
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["weather", "canada"],
) as dag:
 
 
    def task_api_request():
        from extract.api_request import run
        run()
 
    def task_bronze():
        from transform.bronze import build_bronze
        build_bronze()
 
    def task_silver():
        from transform.silver import run_silver
        run_silver()
 
    def task_gold():
        from transform.gold import run_gold
        run_gold()
 
    api_request = PythonOperator(
        task_id="api_request",
        python_callable=task_api_request,
    )
 
    bronze = PythonOperator(
        task_id="bronze",
        python_callable=task_bronze,
    )
 
    silver = PythonOperator(
        task_id="silver",
        python_callable=task_silver,
    )
 
    gold = PythonOperator(
        task_id="gold",
        python_callable=task_gold,
    )
 
 
    api_request >> bronze >> silver >> gold
