"""Generate a synthetic post-acute-care claims dataset for the denial-audit-trail demo.

All data here is 100% synthetic. Nothing in this file reads from, writes to, or
was derived from any real UnitedHealth/Optum system or claims data.

Run:
    python data/generate_synthetic_claims.py
"""

import random
import sqlite3
import uuid
from pathlib import Path

SEED = 42
N_CLAIMS = 300

DB_PATH = Path(__file__).resolve().parent / "claims.db"

# Simplified post-acute diagnosis categories, loosely modeled on CMS post-acute
# care groupings. Not clinically exhaustive -- see README data-sources table.
CATEGORY_LOS_RANGES = {
    "Orthopedic rehabilitation": (7, 14),
    "Cardiac recovery": (5, 12),
    "Stroke recovery": (10, 21),
    "General post-surgical": (4, 10),
    "Pulmonary recovery": (6, 14),
    "Other": (5, 12),
}
CATEGORY_NAMES = list(CATEGORY_LOS_RANGES.keys())

# Distribution of (actual - predicted) LOS days. Centered slightly negative so
# most stays resolve at or under the predicted length, with enough spread to
# produce a right tail -- the source of the denial-flag rate below.
DELTA_MU = -0.3
DELTA_SIGMA = 3.0

# Calibrated so realized rates land in the target ranges (see assertions below)
# given SEED=42, N_CLAIMS=300, and the exact draw order in generate_claims().
OVERRIDE_PROB = 0.215   # of flagged claims, clinician override logged
APPEAL_PROB = 0.605     # of denied claims, appealed
OVERTURN_PROB = 0.91    # of appealed claims, overturned on appeal
# ~90% overturn-on-appeal is a disputed statistic from the Lokken v. UnitedHealth
# Group litigation (per CBS News reporting on court filings), not an audited
# industry baseline -- it is used here only to calibrate the synthetic
# distribution, and the UI must present it as such.


def generate_claims():
    random.seed(SEED)
    rows = []

    for _ in range(N_CLAIMS):
        category = random.choice(CATEGORY_NAMES)
        lo, hi = CATEGORY_LOS_RANGES[category]
        predicted_los_days = random.randint(lo, hi)
        delta = round(random.gauss(DELTA_MU, DELTA_SIGMA))
        actual_los_days = max(1, predicted_los_days + delta)

        # Documented trigger mechanic: a claim is flagged for denial review when
        # the actual length of stay exceeds the algorithm's predicted length of
        # stay (see README data-sources table).
        denial_flag = actual_los_days > predicted_los_days

        clinician_override_logged = False
        if denial_flag:
            clinician_override_logged = random.random() < OVERRIDE_PROB

        final_decision = (
            "denied" if (denial_flag and not clinician_override_logged) else "approved"
        )

        appealed = False
        if final_decision == "denied":
            appealed = random.random() < APPEAL_PROB

        appeal_overturned = False
        if appealed:
            appeal_overturned = random.random() < OVERTURN_PROB

        rows.append(
            {
                "claim_id": str(uuid.uuid4()),
                "diagnosis_category": category,
                "predicted_los_days": predicted_los_days,
                "actual_los_days": actual_los_days,
                "denial_flag": int(denial_flag),
                "clinician_override_logged": int(clinician_override_logged),
                "final_decision": final_decision,
                "appealed": int(appealed),
                "appeal_overturned": int(appeal_overturned),
            }
        )

    return rows


def write_db(rows, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS claims")
    conn.execute(
        """
        CREATE TABLE claims (
            claim_id                  TEXT PRIMARY KEY,
            diagnosis_category        TEXT NOT NULL,
            predicted_los_days        INTEGER NOT NULL,
            actual_los_days           INTEGER NOT NULL,
            denial_flag                INTEGER NOT NULL,
            clinician_override_logged  INTEGER NOT NULL,
            final_decision              TEXT NOT NULL CHECK (final_decision IN ('approved','denied')),
            appealed                    INTEGER NOT NULL,
            appeal_overturned           INTEGER NOT NULL
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO claims (
            claim_id, diagnosis_category, predicted_los_days, actual_los_days,
            denial_flag, clinician_override_logged, final_decision, appealed, appeal_overturned
        ) VALUES (
            :claim_id, :diagnosis_category, :predicted_los_days, :actual_los_days,
            :denial_flag, :clinician_override_logged, :final_decision, :appealed, :appeal_overturned
        )
        """,
        rows,
    )
    conn.commit()
    conn.close()


def self_check(rows):
    total = len(rows)
    flagged = [r for r in rows if r["denial_flag"]]
    denied = [r for r in rows if r["final_decision"] == "denied"]
    appealed = [r for r in rows if r["appealed"]]
    overturned = [r for r in rows if r["appeal_overturned"]]

    flagged_rate = len(flagged) / total
    override_rate = (
        sum(r["clinician_override_logged"] for r in flagged) / len(flagged) if flagged else 0.0
    )
    appeal_rate = len(appealed) / len(denied) if denied else 0.0
    overturn_rate = len(overturned) / len(appealed) if appealed else 0.0

    print(
        f"claims={total} flagged={flagged_rate:.1%} override={override_rate:.1%} "
        f"denied={len(denied)} appeal={appeal_rate:.1%} overturn={overturn_rate:.1%}"
    )

    assert 0.35 <= flagged_rate <= 0.45, f"flagged_rate {flagged_rate:.3f} out of range"
    assert 0.15 <= override_rate <= 0.20, f"override_rate {override_rate:.3f} out of range"
    assert 0.85 <= overturn_rate <= 0.95, f"overturn_rate {overturn_rate:.3f} out of range"


if __name__ == "__main__":
    claims = generate_claims()
    self_check(claims)
    write_db(claims)
    print(f"Wrote {len(claims)} synthetic claims to {DB_PATH}")
