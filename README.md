# 🏙️ End-to-End European Airbnb Data Warehouse & Analytics Platform

An enterprise-grade BI solution transforming fragmented European Airbnb market data into actionable revenue and investment intelligence. Built with an end-to-end Medallion pipeline (Bronze → Silver → Gold), a Kimball-modeled SQL Server Data Warehouse, and an executive Power BI dashboard.

---

## 📌 Architecture & Tech Stack
- **Ingestion & ETL (Bronze → Silver):** Python (`pandas`, `Selenium`) for multi-city ingestion and feature enrichment.
- **Data Warehouse (Silver → Gold):** Microsoft SQL Server (`Airbnb_DWH`), SSMS, T-SQL.
- **Dimensional Modeling:** Kimball Star Schema with Surrogate Keys (`_sk`) and Natural Business Keys (`_bk`).
- **Analytics & BI:** Power BI Desktop, DAX, Custom Airbnb Theme (#FF385C).

---

## 🧱 Data Warehouse Design (Star Schema)
The Gold Layer is structured for high-performance analytical aggregations[cite: 2]:
- **`dim_city`**: Geographic attributes covering 10 major European destinations[cite: 2].
- **`dim_property`**: Combinations of property types, room configurations, and guest capacity[cite: 2].
- **`dim_amenities`**: Amenity bundles (Air Conditioning, WiFi, Kitchen)[cite: 2].
- **`fact_listings`**: Grain at listing level with financial measures, review scores, and coordinates[cite: 2].

---

## 📂 Repository Structure
```text
├── data/
│   ├── bronze/bronze_raw_listings.xlsx
│   ├── intermediate/intermediate_enriched_listings.xlsx
│   └── silver/silver_cleaned_listings.xlsx
├── pipeline/
│   ├── 01_scrape_raw_data.py
│   ├── 02_enrich_amenities.py
│   └── 03_load_star_schema_dwh.py
├── tests/
│   ├── test_pagination_scraper.py
│   └── test_single_listing_parser.py
├── sql/Airbnb_DWH_Backup.sql
├── dashboard/
│   ├── Airbnb_Market_Dashboard.pbix
│   └── Airbnb_Dashboard_Report.pdf
├── .gitignore
├── requirements.txt
└── README.md
