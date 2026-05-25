"""
ETL: Emirates Schools Establishment (ESE) - Maths Diagnostic Marks
- Ingest multi-sheet Excel exports (Grades 11 & 12)
- Standardize schema
- Apply validation + quality flags
- Output anonymized, analysis-ready CSVs

Author: Jitendra Suwalka (portfolio project)
"""

from __future__ import annotations
import re
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA_OUT = ROOT / "data"


def _anon_id(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:10]


def load_grade_sections(path: Path, grade_label: str) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    frames = []

    for sh in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sh, header=None)

        # Find header row containing "Diagnostic"
        header_row = None
        for i in range(min(10, len(df))):
            row = df.iloc[i].astype(str).tolist()
            if any("Diagnostic" in c for c in row):
                header_row = i
                break
        if header_row is None:
            header_row = 1

        cols = df.iloc[header_row].tolist()
        df2 = df.iloc[header_row + 1 :].copy()
        df2.columns = cols
        df2 = df2.dropna(how="all")

        # Column standardization (supports Arabic/English labels commonly seen in exports)
        rename = {}
        for c in df2.columns:
            cs = str(c).strip()
            if cs in ["م", "No", "#"]:
                rename[c] = "student_no"
            elif "رقم" in cs or "ID" in cs:
                rename[c] = "student_id"
            elif "بالانجليزية" in cs or "english" in cs.lower():
                rename[c] = "student_name_en"
            elif cs == "اسم الطالب":
                rename[c] = "student_name_ar"
            elif "Diagnostic" in cs or "marks" in cs.lower():
                rename[c] = "diagnostic_marks"

        df2 = df2.rename(columns=rename)

        keep = [k for k in ["student_no", "student_id", "student_name_en", "student_name_ar", "diagnostic_marks"] if k in df2.columns]
        df2 = df2[keep]

        df2["grade"] = grade_label
        section = re.sub(r"\s+", "", str(sh)).upper()
        df2["section"] = section
        df2["cohort"] = re.search(r"([ABC])", section).group(1) if re.search(r"([ABC])", section) else section
        df2["timepoint"] = f"Grade {grade_label}"

        frames.append(df2)

    return pd.concat(frames, ignore_index=True)


def clean_and_flag(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()

    d["diagnostic_marks"] = pd.to_numeric(d["diagnostic_marks"], errors="coerce")
    d["student_id"] = d["student_id"].astype(str).str.strip()
    d["student_no"] = pd.to_numeric(d["student_no"], errors="coerce")

    for col in ["student_name_en", "student_name_ar"]:
        if col in d.columns:
            d[col] = d[col].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})

    # Validation flags
    d["flag_missing_mark"] = d["diagnostic_marks"].isna()
    d["flag_out_of_range"] = ~d["diagnostic_marks"].between(0, 100, inclusive="both")

    # Outlier flag using IQR rule within (grade, cohort)
    def _iqr_flag(group: pd.DataFrame) -> pd.DataFrame:
        x = group["diagnostic_marks"].dropna()
        if len(x) < 4:
            group["flag_outlier_iqr"] = False
            return group
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        group["flag_outlier_iqr"] = ~group["diagnostic_marks"].between(lo, hi, inclusive="both")
        return group

    d = d.groupby(["grade", "cohort"], group_keys=False).apply(_iqr_flag)

    # Anonymize for public sharing
    d["student_key"] = d["student_id"].apply(_anon_id)

    return d


def main(
    grade11_xlsx: str = "Maths Diagnostic Test Marks Grades-11A,11B,11C Mr. Jitendra.xlsx",
    grade12_xlsx: str = "Maths Diagnostic Test Marks Grades-12A,12B,12C Mr. Jitendra.xlsx",
) -> None:
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    g11 = clean_and_flag(load_grade_sections(ROOT.parent / grade11_xlsx, "11"))
    g12 = clean_and_flag(load_grade_sections(ROOT.parent / grade12_xlsx, "12"))

    combined = pd.concat([g11, g12], ignore_index=True)

    public = combined.drop(columns=["student_id", "student_name_en", "student_name_ar", "student_no"], errors="ignore")
    public.to_csv(DATA_OUT / "maths_diagnostic_clean_anonymized.csv", index=False)

    # Student growth
    pivot = public.pivot_table(index=["student_key", "cohort"], columns="timepoint", values="diagnostic_marks", aggfunc="first").reset_index()
    if "Grade 11" in pivot.columns and "Grade 12" in pivot.columns:
        pivot["delta_12_minus_11"] = pivot["Grade 12"] - pivot["Grade 11"]
    pivot.to_csv(DATA_OUT / "student_growth_anonymized.csv", index=False)

    print("ETL completed. Outputs written to:", DATA_OUT)


if __name__ == "__main__":
    main()
