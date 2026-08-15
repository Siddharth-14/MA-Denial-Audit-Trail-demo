"""Aggregation and per-claim decision-trace logic for the denial-audit-trail demo."""

import sqlite3

import pandas as pd

from app import db


def denial_flag_rate_by_category(conn: sqlite3.Connection) -> pd.DataFrame:
    claims = db.get_all_claims(conn)
    grouped = (
        claims.groupby("diagnosis_category")
        .agg(total_claims=("claim_id", "count"), flagged_claims=("denial_flag", "sum"))
        .reset_index()
    )
    grouped["flag_rate"] = grouped["flagged_claims"] / grouped["total_claims"]
    return grouped


def override_rate_by_category(conn: sqlite3.Connection) -> pd.DataFrame:
    claims = db.get_all_claims(conn)
    flagged = claims[claims["denial_flag"] == 1]
    grouped = (
        flagged.groupby("diagnosis_category")
        .agg(
            flagged_claims=("claim_id", "count"),
            overridden_claims=("clinician_override_logged", "sum"),
        )
        .reset_index()
    )
    grouped["override_rate"] = grouped["overridden_claims"] / grouped["flagged_claims"]

    # Ensure every category appears even if it has zero flagged claims.
    all_categories = pd.DataFrame({"diagnosis_category": claims["diagnosis_category"].unique()})
    grouped = all_categories.merge(grouped, on="diagnosis_category", how="left").fillna(0)
    grouped[["flagged_claims", "overridden_claims"]] = grouped[
        ["flagged_claims", "overridden_claims"]
    ].astype(int)
    return grouped


def overturn_rate_overall(conn: sqlite3.Connection) -> float:
    claims = db.get_all_claims(conn)
    appealed = claims[claims["appealed"] == 1]
    if appealed.empty:
        return 0.0
    return float(appealed["appeal_overturned"].mean())


def claim_decision_trace(conn: sqlite3.Connection, claim_id: str) -> dict:
    claim = db.get_claim_by_id(conn, claim_id)
    if claim is None:
        return {}

    predicted = claim["predicted_los_days"]
    actual = claim["actual_los_days"]
    delta = actual - predicted
    flagged = bool(claim["denial_flag"])
    override = bool(claim["clinician_override_logged"])
    denied = claim["final_decision"] == "denied"
    appealed = bool(claim["appealed"])
    overturned = bool(claim["appeal_overturned"])

    if flagged:
        flag_explanation = (
            f"Flagged because the actual stay ({actual} days) exceeded the predicted "
            f"stay ({predicted} days) by {delta} day{'s' if delta != 1 else ''}."
        )
    else:
        flag_explanation = (
            f"Not flagged: the actual stay ({actual} days) did not exceed the "
            f"predicted stay ({predicted} days)."
        )

    if not flagged:
        override_explanation = "No override needed; the claim was never flagged."
    elif override:
        override_explanation = "A clinician override was logged, so the flag did not result in a denial."
    else:
        override_explanation = "No clinician override was logged for this flagged claim."

    if not denied:
        appeal_explanation = "This claim was approved, so no appeal was necessary."
    elif not appealed:
        appeal_explanation = "This claim was denied and was not appealed."
    elif overturned:
        appeal_explanation = "This claim was denied, appealed, and the denial was overturned."
    else:
        appeal_explanation = "This claim was denied, appealed, and the denial was upheld."

    narrative = " ".join([flag_explanation, override_explanation, appeal_explanation])

    return {
        "claim_id": claim["claim_id"],
        "diagnosis_category": claim["diagnosis_category"],
        "predicted_los_days": predicted,
        "actual_los_days": actual,
        "los_delta": delta,
        "denial_flag": flagged,
        "clinician_override_logged": override,
        "final_decision": claim["final_decision"],
        "appealed": appealed,
        "appeal_overturned": overturned,
        "flag_explanation": flag_explanation,
        "override_explanation": override_explanation,
        "appeal_explanation": appeal_explanation,
        "narrative": narrative,
    }
