"""make_charts.py - renders trend charts (with anomalies marked) for the PDF report."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from anomaly_agent import load_data, build_report


def render_charts(data_path="business_metrics.xlsx", out_prefix="chart"):
    df = load_data(data_path)
    report = build_report(data_path)
    anomaly_dates_by_metric = {}
    for a in report["anomalies"]:
        anomaly_dates_by_metric.setdefault(a.metric, []).append(a.date)

    metrics_to_plot = ["revenue", "traffic", "conversion_rate", "refunds"]
    paths = []

    for metric in metrics_to_plot:
        fig, ax = plt.subplots(figsize=(6.2, 2.6), dpi=150)
        ax.plot(df["date"], df[metric], color="#2563eb", linewidth=1.6)

        flagged = anomaly_dates_by_metric.get(metric, [])
        if flagged:
            flagged_df = df[df["date"].isin(flagged)]
            ax.scatter(flagged_df["date"], flagged_df[metric], color="#dc2626",
                       zorder=5, s=45, label="Anomaly")
            ax.legend(loc="upper left", fontsize=8, frameon=False)

        ax.set_title(metric.replace("_", " ").title(), fontsize=11, loc="left", fontweight="bold")
        ax.tick_params(axis="both", labelsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()

        path = f"{out_prefix}_{metric}.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)

    return paths


if __name__ == "__main__":
    paths = render_charts()
    print("Charts saved:", paths)
