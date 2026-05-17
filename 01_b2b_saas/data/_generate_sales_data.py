"""
Generate synthetic Salesforce SFA-style datasets for 3 domains:
  1. B2B SaaS (annual contracts, multi-region pipeline)
  2. Food Delivery (merchant acquisition for a delivery platform)
  3. EC Marketplace (seller acquisition)

Schema mirrors Salesforce standard objects:
  - Accounts.csv: AccountId, AccountName, Industry, Region, Segment, AccountOwner, CreatedDate
  - Opportunities.csv: OppId, AccountId, OppName, Stage, Amount, Probability, CreatedDate, CloseDate, OwnerId, LossReason
  - Activities.csv: ActivityId, OppId, ActivityType, ActivityDate, OwnerId, DurationMin
  - Users.csv: OwnerId, OwnerName, Role, Region

Output: /home/claude/tableau-portfolio/data/<domain>/
"""

import csv
import os
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT_ROOT = Path("/home/claude/tableau-portfolio/data")

# ----- Common config -----
STAGES = [
    ("01 - Prospecting", 0.10),
    ("02 - Qualification", 0.25),
    ("03 - Needs Analysis", 0.40),
    ("04 - Proposal", 0.60),
    ("05 - Negotiation", 0.80),
    ("06 - Closed Won", 1.00),
    ("07 - Closed Lost", 0.00),
]
LOSS_REASONS = ["Price", "Competitor", "No Decision", "Timing", "Product Fit"]

# Anonymized rep names
REP_FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Avery", "Quinn",
             "Sam", "Dakota", "Reese", "Sky"]
REP_LAST = ["Chen", "Patel", "Kim", "Garcia", "Smith", "Tanaka", "Müller", "Silva",
            "Okafor", "Rossi", "Singh", "Park"]

def make_users(n_reps, regions, role_label="Account Executive"):
    users = []
    for i in range(n_reps):
        users.append({
            "OwnerId": f"U{i+1:03d}",
            "OwnerName": f"{REP_FIRST[i % len(REP_FIRST)]} {REP_LAST[(i*3) % len(REP_LAST)]}",
            "Role": role_label,
            "Region": regions[i % len(regions)],
        })
    return users

def daterange(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

# ===========================
# Domain 1: B2B SaaS
# ===========================
def generate_saas():
    domain = "01_b2b_saas"
    regions = ["NA-East", "NA-West", "EMEA", "APAC", "LATAM"]
    industries = ["FinTech", "HealthTech", "E-commerce", "Media", "Manufacturing",
                  "Logistics", "Education", "Gaming"]
    segments = ["SMB", "Mid-Market", "Enterprise"]
    segment_weights = [0.55, 0.30, 0.15]
    segment_acv = {"SMB": (5000, 25000), "Mid-Market": (25000, 120000),
                   "Enterprise": (120000, 800000)}

    users = make_users(12, regions, "Account Executive")
    write_csv(OUT_ROOT / domain / "Users.csv", users,
              ["OwnerId", "OwnerName", "Role", "Region"])

    # Accounts
    accounts = []
    start_d = date(2023, 1, 1)
    end_d = date(2025, 12, 31)
    for i in range(800):
        seg = random.choices(segments, segment_weights)[0]
        accounts.append({
            "AccountId": f"A{i+1:05d}",
            "AccountName": f"Account-{i+1:05d}",
            "Industry": random.choice(industries),
            "Region": random.choice(regions),
            "Segment": seg,
            "AccountOwner": random.choice(users)["OwnerId"],
            "CreatedDate": daterange(start_d, end_d).isoformat(),
        })
    write_csv(OUT_ROOT / domain / "Accounts.csv", accounts,
              ["AccountId", "AccountName", "Industry", "Region", "Segment",
               "AccountOwner", "CreatedDate"])

    # Opportunities (multiple per account)
    opps = []
    opp_id = 0
    for acc in accounts:
        n_opps = random.choices([1, 2, 3, 4], [0.5, 0.3, 0.15, 0.05])[0]
        for _ in range(n_opps):
            opp_id += 1
            created = daterange(date(2023, 1, 1), date(2026, 4, 30))
            # Add seasonality: Q4 spike, summer dip
            month = created.month
            if month in (11, 12, 3): created = created  # keep
            stage = random.choices(
                [s[0] for s in STAGES],
                weights=[0.05, 0.10, 0.10, 0.15, 0.10, 0.30, 0.20]
            )[0]
            amount_lo, amount_hi = segment_acv[acc["Segment"]]
            amount = round(random.uniform(amount_lo, amount_hi), -2)
            prob = next(s[1] for s in STAGES if s[0] == stage)
            close_offset = random.randint(20, 180)
            close = created + timedelta(days=close_offset)
            opps.append({
                "OppId": f"O{opp_id:06d}",
                "AccountId": acc["AccountId"],
                "OppName": f"{acc['AccountName']} - {random.choice(['Annual', 'Multi-Year', 'Expansion', 'New Logo', 'Renewal'])}",
                "Stage": stage,
                "Amount": amount,
                "Probability": prob,
                "CreatedDate": created.isoformat(),
                "CloseDate": close.isoformat(),
                "OwnerId": acc["AccountOwner"],
                "LossReason": random.choice(LOSS_REASONS) if stage == "07 - Closed Lost" else "",
            })
    write_csv(OUT_ROOT / domain / "Opportunities.csv", opps,
              ["OppId", "AccountId", "OppName", "Stage", "Amount", "Probability",
               "CreatedDate", "CloseDate", "OwnerId", "LossReason"])

    # Activities
    activities = []
    act_types = ["Call", "Email", "Meeting", "Demo", "Proposal Sent"]
    aid = 0
    for opp in opps:
        n_acts = random.randint(3, 15)
        opp_created = date.fromisoformat(opp["CreatedDate"])
        opp_close = date.fromisoformat(opp["CloseDate"])
        for _ in range(n_acts):
            aid += 1
            activities.append({
                "ActivityId": f"AC{aid:07d}",
                "OppId": opp["OppId"],
                "ActivityType": random.choice(act_types),
                "ActivityDate": daterange(opp_created, opp_close).isoformat(),
                "OwnerId": opp["OwnerId"],
                "DurationMin": random.choice([15, 30, 45, 60]),
            })
    write_csv(OUT_ROOT / domain / "Activities.csv", activities,
              ["ActivityId", "OppId", "ActivityType", "ActivityDate", "OwnerId", "DurationMin"])

    return len(accounts), len(opps), len(activities)


# ===========================
# Domain 2: Food Delivery
# ===========================
def generate_food_delivery():
    domain = "02_food_delivery"
    regions = ["Tokyo-23", "Kanto-Other", "Kansai", "Chubu", "Kyushu", "Hokkaido-Tohoku"]
    industries = ["Ramen", "Sushi", "Yakitori", "Pizza", "Burger", "Cafe", "Izakaya",
                  "Bento", "Curry", "Italian", "Chinese", "Korean"]
    segments = ["Independent", "Small Chain", "National Chain", "Enterprise"]
    segment_weights = [0.55, 0.25, 0.15, 0.05]
    # Revenue here = expected monthly commission revenue from the merchant
    segment_acv = {
        "Independent": (50000, 200000),
        "Small Chain": (200000, 800000),
        "National Chain": (800000, 4000000),
        "Enterprise": (4000000, 15000000),
    }

    users = make_users(12, regions, "Merchant Acquisition Manager")
    write_csv(OUT_ROOT / domain / "Users.csv", users,
              ["OwnerId", "OwnerName", "Role", "Region"])

    accounts = []
    for i in range(800):
        seg = random.choices(segments, segment_weights)[0]
        accounts.append({
            "AccountId": f"M{i+1:05d}",
            "AccountName": f"Merchant-{i+1:05d}",
            "Industry": random.choice(industries),
            "Region": random.choice(regions),
            "Segment": seg,
            "AccountOwner": random.choice(users)["OwnerId"],
            "CreatedDate": daterange(date(2023, 1, 1), date(2025, 12, 31)).isoformat(),
        })
    write_csv(OUT_ROOT / domain / "Accounts.csv", accounts,
              ["AccountId", "AccountName", "Industry", "Region", "Segment",
               "AccountOwner", "CreatedDate"])

    opps = []
    opp_id = 0
    for acc in accounts:
        n_opps = random.choices([1, 2, 3], [0.65, 0.25, 0.10])[0]
        for _ in range(n_opps):
            opp_id += 1
            created = daterange(date(2023, 1, 1), date(2026, 4, 30))
            stage = random.choices(
                [s[0] for s in STAGES],
                weights=[0.08, 0.12, 0.12, 0.15, 0.08, 0.25, 0.20]
            )[0]
            amount_lo, amount_hi = segment_acv[acc["Segment"]]
            amount = round(random.uniform(amount_lo, amount_hi), -3)
            prob = next(s[1] for s in STAGES if s[0] == stage)
            close = created + timedelta(days=random.randint(14, 120))
            opps.append({
                "OppId": f"DO{opp_id:06d}",
                "AccountId": acc["AccountId"],
                "OppName": f"{acc['AccountName']} - {random.choice(['New Onboarding', 'Plan Upgrade', 'Multi-Store Rollout', 'Promotion Add-on', 'Renewal'])}",
                "Stage": stage,
                "Amount": amount,
                "Probability": prob,
                "CreatedDate": created.isoformat(),
                "CloseDate": close.isoformat(),
                "OwnerId": acc["AccountOwner"],
                "LossReason": random.choice(LOSS_REASONS) if stage == "07 - Closed Lost" else "",
            })
    write_csv(OUT_ROOT / domain / "Opportunities.csv", opps,
              ["OppId", "AccountId", "OppName", "Stage", "Amount", "Probability",
               "CreatedDate", "CloseDate", "OwnerId", "LossReason"])

    activities = []
    act_types = ["Store Visit", "Phone Call", "Email", "Demo", "Contract Sent"]
    aid = 0
    for opp in opps:
        n_acts = random.randint(2, 10)
        opp_created = date.fromisoformat(opp["CreatedDate"])
        opp_close = date.fromisoformat(opp["CloseDate"])
        for _ in range(n_acts):
            aid += 1
            activities.append({
                "ActivityId": f"DAC{aid:07d}",
                "OppId": opp["OppId"],
                "ActivityType": random.choice(act_types),
                "ActivityDate": daterange(opp_created, opp_close).isoformat(),
                "OwnerId": opp["OwnerId"],
                "DurationMin": random.choice([15, 30, 45, 60]),
            })
    write_csv(OUT_ROOT / domain / "Activities.csv", activities,
              ["ActivityId", "OppId", "ActivityType", "ActivityDate", "OwnerId", "DurationMin"])

    return len(accounts), len(opps), len(activities)


# ===========================
# Domain 3: EC Marketplace (Seller Acquisition)
# ===========================
def generate_ec_marketplace():
    domain = "03_ec_marketplace"
    regions = ["NA", "EU", "JP", "APAC-Other", "LATAM"]
    industries = ["Apparel", "Electronics", "Home & Kitchen", "Beauty", "Sports",
                  "Toys", "Books", "Grocery", "Auto Parts", "Pet Supplies"]
    segments = ["Individual Seller", "SMB Seller", "Brand Seller", "Strategic Brand"]
    segment_weights = [0.40, 0.35, 0.20, 0.05]
    # Revenue = expected annual referral fee + ads spend
    segment_acv = {
        "Individual Seller": (1000, 8000),
        "SMB Seller": (8000, 50000),
        "Brand Seller": (50000, 300000),
        "Strategic Brand": (300000, 2000000),
    }

    users = make_users(12, regions, "Seller Acquisition Manager")
    write_csv(OUT_ROOT / domain / "Users.csv", users,
              ["OwnerId", "OwnerName", "Role", "Region"])

    accounts = []
    for i in range(800):
        seg = random.choices(segments, segment_weights)[0]
        accounts.append({
            "AccountId": f"S{i+1:05d}",
            "AccountName": f"Seller-{i+1:05d}",
            "Industry": random.choice(industries),
            "Region": random.choice(regions),
            "Segment": seg,
            "AccountOwner": random.choice(users)["OwnerId"],
            "CreatedDate": daterange(date(2023, 1, 1), date(2025, 12, 31)).isoformat(),
        })
    write_csv(OUT_ROOT / domain / "Accounts.csv", accounts,
              ["AccountId", "AccountName", "Industry", "Region", "Segment",
               "AccountOwner", "CreatedDate"])

    opps = []
    opp_id = 0
    for acc in accounts:
        n_opps = random.choices([1, 2, 3], [0.6, 0.30, 0.10])[0]
        for _ in range(n_opps):
            opp_id += 1
            created = daterange(date(2023, 1, 1), date(2026, 4, 30))
            stage = random.choices(
                [s[0] for s in STAGES],
                weights=[0.10, 0.15, 0.10, 0.12, 0.08, 0.25, 0.20]
            )[0]
            amount_lo, amount_hi = segment_acv[acc["Segment"]]
            amount = round(random.uniform(amount_lo, amount_hi), -2)
            prob = next(s[1] for s in STAGES if s[0] == stage)
            close = created + timedelta(days=random.randint(7, 90))
            opps.append({
                "OppId": f"EO{opp_id:06d}",
                "AccountId": acc["AccountId"],
                "OppName": f"{acc['AccountName']} - {random.choice(['Marketplace Onboarding', 'FBA Activation', 'Ads Upsell', 'Brand Registry', 'Renewal'])}",
                "Stage": stage,
                "Amount": amount,
                "Probability": prob,
                "CreatedDate": created.isoformat(),
                "CloseDate": close.isoformat(),
                "OwnerId": acc["AccountOwner"],
                "LossReason": random.choice(LOSS_REASONS) if stage == "07 - Closed Lost" else "",
            })
    write_csv(OUT_ROOT / domain / "Opportunities.csv", opps,
              ["OppId", "AccountId", "OppName", "Stage", "Amount", "Probability",
               "CreatedDate", "CloseDate", "OwnerId", "LossReason"])

    activities = []
    act_types = ["Outreach Email", "Phone Call", "Video Meeting", "Onboarding Workshop", "Contract Sent"]
    aid = 0
    for opp in opps:
        n_acts = random.randint(2, 8)
        opp_created = date.fromisoformat(opp["CreatedDate"])
        opp_close = date.fromisoformat(opp["CloseDate"])
        for _ in range(n_acts):
            aid += 1
            activities.append({
                "ActivityId": f"EAC{aid:07d}",
                "OppId": opp["OppId"],
                "ActivityType": random.choice(act_types),
                "ActivityDate": daterange(opp_created, opp_close).isoformat(),
                "OwnerId": opp["OwnerId"],
                "DurationMin": random.choice([15, 30, 45, 60]),
            })
    write_csv(OUT_ROOT / domain / "Activities.csv", activities,
              ["ActivityId", "OppId", "ActivityType", "ActivityDate", "OwnerId", "DurationMin"])

    return len(accounts), len(opps), len(activities)


if __name__ == "__main__":
    print("Generating B2B SaaS...")
    print("  Accounts: {}, Opps: {}, Activities: {}".format(*generate_saas()))
    print("Generating Food Delivery...")
    print("  Accounts: {}, Opps: {}, Activities: {}".format(*generate_food_delivery()))
    print("Generating EC Marketplace...")
    print("  Accounts: {}, Opps: {}, Activities: {}".format(*generate_ec_marketplace()))
    print("\nAll datasets generated under:", OUT_ROOT)
