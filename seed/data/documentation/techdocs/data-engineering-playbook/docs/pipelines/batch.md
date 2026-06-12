# Batch Processing với Apache Spark

## Khi nào dùng Batch Processing?

Batch phù hợp khi:
- Dữ liệu cần xử lý theo chu kỳ (hourly, daily)
- Latency chấp nhận được (phút đến giờ)
- Volume lớn (> 1GB)
- Logic transformation phức tạp

## Cấu trúc Spark Job chuẩn

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *
import logging

logger = logging.getLogger(__name__)


def create_spark_session(app_name: str) -> SparkSession:
    """Tạo Spark session với cấu hình chuẩn."""
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .getOrCreate()
    )


def read_source(spark: SparkSession, date: str) -> "DataFrame":
    """Đọc dữ liệu nguồn từ Data Lake."""
    return spark.read.parquet(
        f"s3://data-lake/bronze/orders/date={date}/"
    )


def transform(df: "DataFrame") -> "DataFrame":
    """Áp dụng business logic."""
    return (
        df
        .filter(F.col("status") != "CANCELLED")
        .withColumn("revenue", F.col("amount") * F.col("quantity"))
        .withColumn("processing_date", F.current_date())
        .groupBy("customer_id", "product_category")
        .agg(
            F.sum("revenue").alias("total_revenue"),
            F.count("*").alias("order_count"),
            F.avg("amount").alias("avg_order_value"),
        )
    )


def write_output(df: "DataFrame", date: str) -> None:
    """Ghi kết quả ra Data Lake."""
    (
        df.write
        .mode("overwrite")
        .partitionBy("processing_date")
        .parquet(f"s3://data-lake/gold/customer-revenue/date={date}/")
    )
    logger.info(f"Written {df.count()} records for date={date}")


def main(date: str) -> None:
    spark = create_spark_session("customer-revenue-aggregation")
    try:
        df = read_source(spark, date)
        result = transform(df)
        write_output(result, date)
        logger.info("Job completed successfully")
    except Exception as e:
        logger.error(f"Job failed: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    import sys
    main(date=sys.argv[1])
```

## Airflow DAG

```python
from airflow import DAG
from airflow.providers.amazon.aws.operators.emr import EmrServerlessStartJobRunOperator
from datetime import datetime, timedelta

with DAG(
    dag_id="customer_revenue_daily",
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 * * *",  # 6am UTC daily
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": True,
        "email": ["data-alerts@example.com"],
    },
    catchup=False,
    tags=["revenue", "customer", "daily"],
) as dag:

    run_spark_job = EmrServerlessStartJobRunOperator(
        task_id="run_customer_revenue",
        application_id="{{ var.value.emr_serverless_app_id }}",
        execution_role_arn="{{ var.value.emr_execution_role }}",
        job_driver={
            "sparkSubmit": {
                "entryPoint": "s3://scripts/customer_revenue.py",
                "entryPointArguments": ["{{ ds }}"],  # YYYY-MM-DD
                "sparkSubmitParameters": "--conf spark.executor.cores=4",
            }
        },
    )
```

## Best Practices

### Performance

1. **Partition pruning**: Luôn filter trên partition columns (`date`, `year`, `month`)
2. **Broadcast join**: Join với small tables (< 100MB) dùng `F.broadcast()`
3. **Adaptive Query Execution (AQE)**: Luôn bật
4. **Avoid UDFs khi có thể**: Dùng built-in Spark functions thay vì Python UDFs
5. **Repartition trước khi write**: `df.repartition(n_partitions)` để tránh small files

### Data Quality

```python
from great_expectations.dataset import SparkDFDataset

def validate_output(df: "DataFrame") -> None:
    ge_df = SparkDFDataset(df)

    result = ge_df.expect_column_values_to_not_be_null("customer_id")
    assert result.success, "customer_id must not be null"

    result = ge_df.expect_column_values_to_be_between(
        "total_revenue", min_value=0
    )
    assert result.success, "total_revenue must be non-negative"
```
