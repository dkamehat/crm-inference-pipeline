"""
Add Customer Health data to B2B SaaS domain:
  - Subscriptions.csv: ARR, plan, start_date, status, renewal_date
  - UsageMetrics.csv: monthly active users, feature adoption rate, sessions
  - HealthScores.csv: composite health score, churn risk band, NPS proxy

This supports Dashboard 4: Customer Health (Notion CSM positioning).
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(43)  # different seed to avoid correlation with existing files

DATA_DIR = Path("/home/claude/tableau-portfolio/data/01_b2b_saas")

# Load existing accounts to extend
with open(DATA_DIR / "Accounts.csv", encoding="utf-8") as f:
    accounts = list(csv.DictReader(f))
with open(DATA_DIR / "Opportunities.csv", encoding="utf-8") as f:
    opps = list(csv.DictReader(f))

# Find accounts that have at least one Closed Won opp - these are customers
won_account_ids = {o["AccountId"] for o in opps if o["Stage"] == "06 - Closed Won"}
customers = [a for a in accounts if a["AccountId"] in won_account_ids]
print(f"Customers (have Closed Won opp): {len(customers)}")

PLANS = [
    ("Starter", 5000, 25000),
    ("Growth", 25000, 120000),
    ("Business", 120000, 400000),
    ("Enterprise", 400000, 1500000),
]
SEGMENT_TO_PLAN = {
    "SMB": ["Starter", "Growth"],
    "Mid-Market": ["Growth", "Business"],
    "Enterprise": ["Business", "Enterprise"],
}

STATUS_WEIGHTS = [("Active", 0.78), ("At Risk", 0.12), ("Churned", 0.10)]

def weighted(choices):
    options, weights = zip(*choices)
    return random.choices(options, weights=weights)[0]

# ===== Subscriptions =====
subs = []
sub_id = 0
for acc in customers:
    plan = random.choice(SEGMENT_TO_PLAN[acc["Segment"]])
    plan_lo, plan_hi = next((lo, hi) for name, lo, hi in PLANS if name == plan)
    arr = round(random.uniform(plan_lo, plan_hi), -2)
    start = date.fromisoformat(acc["CreatedDate"]) + timedelta(days=random.randint(10, 90))
    status = weighted(STATUS_WEIGHTS)
    if status == "Churned":
        churn_date = start + timedelta(days=random.randint(180, 700))
        renewal = churn_date  # last renewal attempt
    else:
        renewal = start + timedelta(days=365 * random.choice([1, 1, 1, 2]))
    sub_id += 1
    subs.append({
        "SubscriptionId": f"SUB{sub_id:05d}",
        "AccountId": acc["AccountId"],
        "Plan": plan,
        "ARR": arr,
        "StartDate": start.isoformat(),
        "RenewalDate": renewal.isoformat(),
        "Status": status,
        "Seats": random.choice([5, 10, 20, 50, 100, 250, 500]),
    })

with open(DATA_DIR / "Subscriptions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["SubscriptionId", "AccountId", "Plan", "ARR",
                                       "StartDate", "RenewalDate", "Status", "Seats"])
    w.writeheader()
    w.writerows(subs)

# ===== Monthly Usage Metrics (last 12 months) =====
usage = []
uid = 0
end_month = date(2026, 5, 1)
for s in subs:
    if s["Status"] == "Churned":
        # generate up to churn date
        last_month = date.fromisoformat(s["RenewalDate"])
    else:
        last_month = end_month

    start_month = max(date.fromisoformat(s["StartDate"]).replace(day=1),
                      date(2025, 6, 1))

    # decay or growth profile
    profile = random.choices(
        ["growing", "stable", "declining", "spiky"],
        weights=[0.40, 0.30, 0.20, 0.10]
    )[0]

    cur = start_month
    seats = s["Seats"]
    base_mau_ratio = random.uniform(0.30, 0.85)  # baseline % of seats active
    months_elapsed = 0
    while cur <= last_month:
        # MAU drift
        if profile == "growing":
            ratio = base_mau_ratio + months_elapsed * 0.015
        elif profile == "declining":
            ratio = base_mau_ratio - months_elapsed * 0.025
        elif profile == "spiky":
            ratio = base_mau_ratio + random.uniform(-0.20, 0.20)
        else:
            ratio = base_mau_ratio + random.uniform(-0.05, 0.05)
        ratio = max(0.05, min(0.98, ratio))

        mau = int(seats * ratio)
        sessions = int(mau * random.uniform(8, 35))
        feature_adoption = round(random.uniform(0.20, 0.90), 2)
        uid += 1
        usage.append({
            "UsageId": f"U{uid:07d}",
            "AccountId": s["AccountId"],
            "SubscriptionId": s["SubscriptionId"],
            "Month": cur.isoformat(),
            "Seats": seats,
            "MAU": mau,
            "MAURatio": round(ratio, 3),
            "Sessions": sessions,
            "FeatureAdoptionRate": feature_adoption,
        })
        # increment month
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
        months_elapsed += 1

with open(DATA_DIR / "UsageMetrics.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["UsageId", "AccountId", "SubscriptionId", "Month",
                                       "Seats", "MAU", "MAURatio", "Sessions",
                                       "FeatureAdoptionRate"])
    w.writeheader()
    w.writerows(usage)

# ===== Current Health Scores (1 row per active subscription) =====
healths = []
for s in subs:
    if s["Status"] == "Churned":
        score = random.randint(15, 45)
        band = "Red"
    elif s["Status"] == "At Risk":
        score = random.randint(40, 65)
        band = "Yellow"
    else:
        score = random.randint(60, 95)
        band = "Green" if score >= 75 else "Yellow"
    nps = random.randint(-30, 80) if s["Status"] != "Churned" else random.randint(-50, 20)
    healths.append({
        "AccountId": s["AccountId"],
        "SubscriptionId": s["SubscriptionId"],
        "HealthScore": score,
        "HealthBand": band,
        "NPS": nps,
        "LastQBR": (date(2026, 5, 1) - timedelta(days=random.randint(15, 180))).isoformat(),
        "CSMOwner": random.choice([f"CSM-{i:02d}" for i in range(1, 9)]),
    })

with open(DATA_DIR / "HealthScores.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["AccountId", "SubscriptionId", "HealthScore",
                                       "HealthBand", "NPS", "LastQBR", "CSMOwner"])
    w.writeheader()
    w.writerows(healths)

print(f"Subscriptions: {len(subs)}")
print(f"Usage rows: {len(usage)}")
print(f"Health scores: {len(healths)}")

# Distribution check
from collections import Counter
print("\nStatus distribution:", Counter(s["Status"] for s in subs))
print("Plan distribution:", Counter(s["Plan"] for s in subs))
print("Health band:", Counter(h["HealthBand"] for h in healths))
