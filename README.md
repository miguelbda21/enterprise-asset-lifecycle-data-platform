# Enterprise Asset Lifecycle Data Platform (Synthetic)

A portfolio-grade, end-to-end **data engineering pipeline** that models an **enterprise IT asset lifecycle** (procurement → inventory → deployment → incidents/changes → lifecycle/end-of-life) using **synthetic data** and production-style patterns.

This project is designed to demonstrate how I build **reliable, testable, maintainable** data pipelines using **Python + SQL**, with a structure that maps directly to real enterprise environments (e.g., ServiceNow CMDB / asset management).

---

## What This Project Demonstrates

- **Data engineering pipeline design** (ingestion → staging → warehouse → analytics)
- **SQL-first modeling** (DDL, transformations, analytics-ready views)
- **Data quality & validation** patterns (row counts, PK/FK checks, null checks, duplicate checks)
- **Incremental loads** and watermark patterns
- **Reproducible project structure** (clean folder layout, modular code)
- **Git discipline** (tracked structure, ignored secrets/artifacts)

---

## Architecture (High Level)

**Sources (synthetic)**
- Assets, models, locations, users
- Deployment events
- Incidents, changes, requests
- Lifecycle status transitions

**Pipeline layers**
1. **Raw**: landing zone for source extracts
2. **Staged**: cleaned + standardized tables (types, keys, basic rules)
3. **Warehouse**: conformed dimensions + facts (analytics-ready model)
4. **Analytics**: views / marts for dashboards and KPI reporting

---

## Repository Structure

```text
enterprise-asset-lifecycle-data-platform/
├── data/
│   ├── raw/                # Landing zone (synthetic extracts)
│   ├── staged/             # Cleaned/standardized datasets
│   └── warehouse/          # Modeled data warehouse outputs
│
├── sql/
│   ├── ddl/                # CREATE TABLE scripts (dims/facts/staging)
│   ├── transformations/    # ELT logic (staging → warehouse)
│   └── analytics/          # Views/marts for reporting/KPIs
│
├── src/
│   ├── api/                # (Optional) REST API integration examples
│   ├── ingestion/          # Extract/load patterns (files/APIs/db)
│   ├── pipelines/          # Orchestration logic (run steps end-to-end)
│   └── utils/              # Shared helpers (logging, configs, validation)
│
├── notebooks/              # Exploration & prototyping
├── tests/                  # Unit tests + data validation tests
├── .gitignore
└── README.md
