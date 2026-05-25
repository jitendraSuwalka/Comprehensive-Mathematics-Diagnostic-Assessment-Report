"""
Analysis + Visualization:
- KPI summaries
- Cohort segmentation
- Longitudinal change (Grade 11 -> Grade 12)
- Figures exported to reports/figures

Author: Jitendra Suwalka (portfolio project)
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "reports" / "figures"


TIER_ORDER = ["<70", "70-79", "80-89", "90+"]


def tier(x: float) -> str:
    if np.isnan(x):
        return np.nan
    if x < 70:
        return "<70"
    if x < 80:
        return "70-79"
    if x < 90:
        return "80-89"
    return "90+"


def savefig(name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIG / name, bbox_inches="tight")
    plt.close()


def main() -> None:
    df = pd.read_csv(DATA / "maths_diagnostic_clean_anonymized.csv")
    df["diagnostic_marks"] = pd.to_numeric(df["diagnostic_marks"], errors="coerce")

    # KPI tables
    overall = df.groupby("timepoint").agg(
        n=("diagnostic_marks", "count"),
        mean=("diagnostic_marks", "mean"),
        median=("diagnostic_marks", "median"),
        std=("diagnostic_marks", "std"),
        pct_ge80=("diagnostic_marks", lambda x: (x >= 80).mean() * 100),
        pct_ge90=("diagnostic_marks", lambda x: (x >= 90).mean() * 100),
        pct_lt70=("diagnostic_marks", lambda x: (x < 70).mean() * 100),
    ).reset_index()
    overall.to_csv(DATA / "kpi_overall.csv", index=False)

    by_cohort = df.groupby(["timepoint", "cohort"]).agg(
        n=("diagnostic_marks", "count"),
        mean=("diagnostic_marks", "mean"),
        median=("diagnostic_marks", "median"),
        std=("diagnostic_marks", "std"),
        p25=("diagnostic_marks", lambda x: x.quantile(0.25)),
        p75=("diagnostic_marks", lambda x: x.quantile(0.75)),
        min=("diagnostic_marks", "min"),
        max=("diagnostic_marks", "max"),
        pct_ge80=("diagnostic_marks", lambda x: (x >= 80).mean() * 100),
        pct_ge90=("diagnostic_marks", lambda x: (x >= 90).mean() * 100),
    ).reset_index()
    by_cohort.to_csv(DATA / "kpi_by_cohort_timepoint.csv", index=False)

    # Histograms
    for tp in ["Grade 11", "Grade 12"]:
        plt.figure(figsize=(6, 4))
        x = df.loc[df["timepoint"] == tp, "diagnostic_marks"].dropna()
        plt.hist(x, bins=10, edgecolor="black")
        plt.title(f"Distribution of Maths Diagnostic Marks ({tp})")
        plt.xlabel("Marks")
        plt.ylabel("Number of students")
        savefig(f"hist_{tp.replace(' ', '_').lower()}.png")

    # Boxplot by cohort & grade
    plt.figure(figsize=(7, 4))
    order = ["A", "B", "C"]
    positions, labels, data = [], [], []
    pos = 1
    for tp in ["Grade 11", "Grade 12"]:
        for coh in order:
            data.append(df[(df.timepoint == tp) & (df.cohort == coh)]["diagnostic_marks"].dropna().values)
            positions.append(pos)
            labels.append(f"{coh}\n{tp[-2:]}")
            pos += 1
        pos += 1

    plt.boxplot(data, positions=positions, widths=0.6, patch_artist=False)
    plt.xticks(positions, labels)
    plt.ylabel("Marks")
    plt.title("Marks by Cohort (A/B/C) Across Grade 11 → Grade 12")
    savefig("boxplot_cohort_grade.png")

    # Tier stacked bars
    for tp in ["Grade 11", "Grade 12"]:
        tmp = df[df.timepoint == tp].copy()
        tmp["tier"] = tmp["diagnostic_marks"].apply(tier)
        counts = (
            tmp.groupby(["cohort", "tier"])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=TIER_ORDER, fill_value=0)
            .reindex(order)
        )

        plt.figure(figsize=(6, 4))
        bottom = np.zeros(len(counts))
        x = np.arange(len(counts.index))
        for t in TIER_ORDER:
            plt.bar(x, counts[t].values, bottom=bottom, edgecolor="black")
            bottom += counts[t].values
        plt.xticks(x, counts.index)
        plt.ylabel("Number of students")
        plt.title(f"Tier Distribution by Cohort ({tp})")
        plt.legend(TIER_ORDER, title="Tier", bbox_to_anchor=(1.02, 1), loc="upper left")
        savefig(f"tier_stacked_{tp.replace(' ', '_').lower()}.png")

    # Longitudinal pivot + scatter
    piv = df.pivot_table(index=["student_key", "cohort"], columns="timepoint", values="diagnostic_marks", aggfunc="first").reset_index()
    if "Grade 11" in piv.columns and "Grade 12" in piv.columns:
        piv["delta_12_minus_11"] = piv["Grade 12"] - piv["Grade 11"]

        plt.figure(figsize=(5.5, 5))
        x, y = piv["Grade 11"], piv["Grade 12"]
        plt.scatter(x, y, edgecolors="black")
        mn, mx = float(min(x.min(), y.min())), float(max(x.max(), y.max()))
        plt.plot([mn, mx], [mn, mx], linestyle="--", color="black")
        plt.xlabel("Grade 11 marks")
        plt.ylabel("Grade 12 marks")
        plt.title("Student-level Change: Grade 11 vs Grade 12")
        savefig("scatter_g11_vs_g12.png")

        plt.figure(figsize=(6, 4))
        plt.hist(piv["delta_12_minus_11"], bins=12, edgecolor="black")
        plt.xlabel("Change in marks (Grade 12 - Grade 11)")
        plt.ylabel("Number of students")
        plt.title("Distribution of Year-on-Year Change")
        savefig("delta_hist.png")

        # Cohort mean trend
        plt.figure(figsize=(6, 4))
        means = df.groupby(["timepoint", "cohort"])["diagnostic_marks"].mean().unstack().reindex(["Grade 11", "Grade 12"])
        for coh in order:
            plt.plot(means.index, means[coh].values, marker="o", label=f"Cohort {coh}")
        plt.ylabel("Mean marks")
        plt.title("Cohort Mean Trend (Grade 11 → Grade 12)")
        plt.legend()
        savefig("cohort_mean_trend.png")

        # Basic paired test (informational)
        t, p = stats.ttest_rel(piv["Grade 12"], piv["Grade 11"])
        print(f"Paired t-test: t={t:.3f}, p={p:.3f}")

    print("Analysis completed. Figures written to:", FIG)


if __name__ == "__main__":
    main()
