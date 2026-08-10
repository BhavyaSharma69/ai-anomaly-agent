"""
generate_data.py
Creates a synthetic 'business_metrics.xlsx' file that mimics daily KPI exports
(e.g. from an e-commerce or SaaS dashboard). Used as sample input for the
anomaly agent. A few realistic anomalies are deliberately injected near the
end of the series so the detector has something real to catch.
"""

import numpy as np
import pandas as pd

np.random.seed(42)

n_days = 60
dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_days, freq="D")

# Base trends with weekly seasonality + noise
day_of_week = dates.dayofweek
weekend_factor = np.where(day_of_week >= 5, 0.8, 1.0)

revenue = 12000 + np.arange(n_days) * 25 + np.random.normal(0, 400, n_days)
revenue = revenue * weekend_factor

orders = 300 + np.arange(n_days) * 0.5 + np.random.normal(0, 12, n_days)
orders = orders * weekend_factor

traffic = 9000 + np.arange(n_days) * 15 + np.random.normal(0, 250, n_days)
traffic = traffic * weekend_factor

conversion_rate = (orders / traffic) * 100
cost = 4000 + np.arange(n_days) * 8 + np.random.normal(0, 150, n_days)
refunds = 40 + np.random.normal(0, 6, n_days)

# --- Inject realistic anomalies in the last week ---
# 1) Traffic spike (e.g. campaign/viral post) without matching order growth
traffic[-4] *= 1.9
# 2) Conversion rate drop the same day (quality of traffic issue)
orders[-4] *= 1.05
# 3) Refund spike a couple days later (possible product/shipping issue)
refunds[-2] *= 3.2
# 4) Revenue dip despite steady traffic (pricing/checkout issue)
revenue[-1] *= 0.72

conversion_rate = (orders / traffic) * 100

df = pd.DataFrame({
    "date": dates,
    "revenue": revenue.round(2),
    "orders": orders.round(0).astype(int),
    "traffic": traffic.round(0).astype(int),
    "conversion_rate": conversion_rate.round(2),
    "cost": cost.round(2),
    "refunds": refunds.round(2),
})

df.to_excel("business_metrics.xlsx", index=False)
print("Created business_metrics.xlsx with", len(df), "rows")
print(df.tail(6).to_string(index=False))
