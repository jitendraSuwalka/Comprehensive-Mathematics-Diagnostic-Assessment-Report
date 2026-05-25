# ESE Performance Analytics — Maths Diagnostic (Grades 11 & 12)

Portfolio-style project showcasing **performance analytics pipeline**, **data quality controls**, **cohort segmentation**, and **KPI reporting** for maths diagnostic assessments.

## What’s inside
- **Repeatable ETL** from multi-sheet Excel exports → standardized, validated, anonymized datasets
- **Cohort analysis** (A/B/C) and **benchmark tiers** (<70, 70–79, 80–89, 90+)
- **Longitudinal tracking** (Grade 11 → Grade 12) with student-level change visuals
- **Ready-to-share outputs** for GitHub (no student PII)

## Key outputs
- Report: `reports/REPORT.md`
- Figures: `reports/figures/`
- Clean data: `data/*.csv`
- Code: `src/etl.py`, `src/analysis.py`

## Run locally
```bash
python -m pip install -r requirements.txt
python src/etl.py
python src/analysis.py
```

> Note: The repository intentionally exports **anonymized student keys** and excludes names/IDs.
