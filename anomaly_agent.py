"""
anomaly_agent.py

An automated anomaly-detection agent for business KPI monitoring.

Pipeline:
  1. Read a business metrics Excel export
  2. Clean/validate the data
  3. Compare each metric's most recent value against a rolling baseline
  4. Flag statistically significant deviations
  5. Generate a plain-English explanation for each flagged anomaly
  6. Produce a structured report (used by report_pdf.py / email_alert.py)

This is intentionally dependency-light: detection uses a rolling mean +
standard deviation (z-score) baseline, no external ML libraries required.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime


BASELINE_WINDOW = 14     # days used to build the "normal" baseline
Z_THRESHOLD = 2.0        # how many std-devs away counts as anomalous
METRICS = ["revenue", "orders", "traffic", "conversion_rate", "cost", "refunds"]

# Metrics where an increase is bad news (context matters for the summary)
BAD_WHEN_UP = {"cost", "refunds"}
BAD_WHEN_DOWN = {"revenue", "orders", "conversion_rate"}


@dataclass
class Anomaly:
    metric: str
    date: pd.Timestamp
    value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    direction: str  # "up" or "down"
    severity: str   # "moderate" or "high"
    explanation: str = ""


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    missing = df[METRICS].isna().sum().sum()
    if missing:
        df[METRICS] = df[METRICS].ffill()

    return df


def detect_anomalies(df: pd.DataFrame, lookback_days: int = 7) -> list[Anomaly]:
    """Scan the most recent `lookback_days` rows. Each day is compared against
    a rolling baseline built from the BASELINE_WINDOW days immediately before
    it (so today's anomaly doesn't get diluted by yesterday's, and vice versa)."""
    anomalies = []
    start_idx = max(BASELINE_WINDOW, len(df) - lookback_days)

    for idx in range(start_idx, len(df)):
        row = df.iloc[idx]
        baseline_slice = df.iloc[idx - BASELINE_WINDOW: idx]

        for metric in METRICS:
            baseline = baseline_slice[metric]
            mean, std = baseline.mean(), baseline.std()
            if std == 0 or np.isnan(std):
                continue

            current_value = row[metric]
            z = (current_value - mean) / std

            if abs(z) >= Z_THRESHOLD:
                direction = "up" if z > 0 else "down"
                severity = "high" if abs(z) >= 3.0 else "moderate"
                anomalies.append(Anomaly(
                    metric=metric,
                    date=row["date"],
                    value=current_value,
                    baseline_mean=mean,
                    baseline_std=std,
                    z_score=z,
                    direction=direction,
                    severity=severity,
                ))

    return anomalies


def explain(anomaly: Anomaly) -> str:
    """Turn a raw statistical flag into a plain-English, business-friendly line."""
    pct_change = (anomaly.value - anomaly.baseline_mean) / anomaly.baseline_mean * 100
    direction_word = "risen" if anomaly.direction == "up" else "dropped"

    is_bad = (
        (anomaly.metric in BAD_WHEN_UP and anomaly.direction == "up") or
        (anomaly.metric in BAD_WHEN_DOWN and anomaly.direction == "down")
    )
    tone = "This may need attention." if is_bad else "This looks like a positive shift, worth confirming it's expected."

    label = anomaly.metric.replace("_", " ").title()
    return (
        f"{label} has {direction_word} to {anomaly.value:,.2f} "
        f"({pct_change:+.1f}% vs. the {BASELINE_WINDOW}-day average of {anomaly.baseline_mean:,.2f}). "
        f"{tone}"
    )


def cross_reference(same_day_anomalies: list[Anomaly]) -> str:
    """Look for a plausible relationship between anomalies flagged on the same
    day - this is what makes the report read like an analyst's note, not a
    log dump."""
    metrics_flagged = {a.metric for a in same_day_anomalies}

    if "traffic" in metrics_flagged and "conversion_rate" in metrics_flagged:
        return ("Traffic and conversion rate moved together — this pattern usually "
                "indicates a change in traffic quality (e.g. a campaign or referral "
                "source bringing in less qualified visitors) rather than a site issue.")
    if "refunds" in metrics_flagged and "revenue" in metrics_flagged:
        return ("Refunds and revenue both moved unfavorably — worth checking recent "
                "orders for a product, shipping, or billing issue.")
    if "revenue" in metrics_flagged and "orders" not in metrics_flagged:
        return ("Revenue moved without a matching change in order count — this points "
                "toward pricing, discounting, or average order value rather than demand.")
    return ""


def build_report(path: str, lookback_days: int = 7) -> dict:
    df = load_data(path)
    anomalies = detect_anomalies(df, lookback_days=lookback_days)
    for a in anomalies:
        a.explanation = explain(a)

    # group same-day anomalies for cross-referencing
    by_date: dict = {}
    for a in anomalies:
        by_date.setdefault(a.date, []).append(a)
    notes = {d: cross_reference(items) for d, items in by_date.items() if len(items) >= 2}

    report = {
        "generated_at": datetime.now(),
        "report_date": df["date"].iloc[-1],
        "rows_analyzed": len(df),
        "lookback_days": lookback_days,
        "anomalies": sorted(anomalies, key=lambda a: a.date),
        "cross_reference_notes": notes,
        "status": "ANOMALIES DETECTED" if anomalies else "ALL METRICS NORMAL",
    }
    return report


if __name__ == "__main__":
    report = build_report("business_metrics.xlsx")
    print(f"Report date: {report['report_date'].date()}")
    print(f"Status: {report['status']}")
    print(f"Anomalies found: {len(report['anomalies'])} (last {report['lookback_days']} days)\n")
    for a in report["anomalies"]:
        print(f"{a.date.date()} [{a.severity.upper()}] {a.explanation}")
    for d, note in report["cross_reference_notes"].items():
        print(f"\nAnalyst note ({d.date()}): {note}")
