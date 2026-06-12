# Data Engineering Playbook

Chào mừng đến với **Data Engineering Playbook** — tài liệu hướng dẫn xây dựng và vận hành data pipelines.

## Tầm nhìn

Chúng tôi xây dựng nền tảng dữ liệu hướng đến:
- **Reliability**: Pipelines chạy ổn định, có monitoring rõ ràng
- **Scalability**: Xử lý được dữ liệu tăng trưởng 10x mà không cần re-architecture
- **Discoverability**: Mọi dataset đều được catalog hóa và có lineage rõ ràng
- **Data Quality**: Dữ liệu được validate trước khi dùng cho analytics/ML

## Kiến trúc tổng quan

```
                    ┌─────────────────────────────────┐
                    │         Data Sources             │
                    │  DBs │ APIs │ Events │ Files     │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │        Ingestion Layer           │
                    │   Debezium (CDC) │ Airbyte       │
                    │   Kafka │ AWS Kinesis            │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │          Data Lake (S3)          │
                    │  Bronze (raw) │ Silver (cleaned) │
                    │            Gold (serving)        │
                    └──────────────┬──────────────────┘
                                   │
               ┌───────────────────┼────────────────────┐
               │                   │                    │
  ┌────────────▼────┐  ┌───────────▼─────┐  ┌──────────▼────────┐
  │  Batch (Spark)  │  │  Stream (Flink) │  │  Transform (dbt)  │
  └─────────────────┘  └─────────────────┘  └───────────────────┘
               │                   │                    │
               └───────────────────┴────────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │         Serving Layer            │
                    │  Redshift │ ClickHouse │ Redis   │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │         Consumers                │
                    │  BI Tools │ ML Models │ APIs     │
                    └─────────────────────────────────┘
```

## Data Maturity Model

| Level | Mô tả | Dấu hiệu |
|---|---|---|
| **Level 1** | Ad-hoc | Excel, manual queries |
| **Level 2** | Repeatable | Automated reports, basic pipelines |
| **Level 3** | Defined | Data warehouse, standardized processes |
| **Level 4** | Managed | Data catalog, lineage, quality monitoring |
| **Level 5** | Optimized | ML-driven, self-service, data products |

Chúng tôi hiện ở **Level 3-4** và đang hướng đến Level 5.

## Liên hệ

- **Slack**: `#data-engineering`
- **On-call**: Xem rotation trong PagerDuty schedule `data-oncall`
- **Jira**: Project `DATA`
