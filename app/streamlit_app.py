"""Denial Audit Trail -- synthetic Medicare Advantage post-acute-care denial demo.

Entry point:
    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from app import aggregate, db

SYNTHETIC_BANNER = (
    "All claims on this page are SYNTHETIC -- generated to illustrate a "
    "decision-audit pattern, not real UnitedHealth/Optum data."
)


@st.cache_resource
def get_conn():
    return db.get_connection()


def render_dashboard(conn):
    claims = db.get_all_claims(conn)
    total_claims = len(claims)
    flag_rate = claims["denial_flag"].mean()
    flagged = claims[claims["denial_flag"] == 1]
    override_rate = flagged["clinician_override_logged"].mean() if not flagged.empty else 0.0
    overturn_rate = aggregate.overturn_rate_overall(conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Claims", f"{total_claims}")
    col2.metric("Denial-Flag Rate", f"{flag_rate:.1%}")
    col3.metric("Override Rate", f"{override_rate:.1%}")
    col4.metric("Overall Appeal-Overturn Rate", f"{overturn_rate:.1%}")

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Denial-Flag Rate by Diagnosis Category")
        flag_df = aggregate.denial_flag_rate_by_category(conn)
        fig1 = px.bar(
            flag_df.sort_values("flag_rate", ascending=False),
            x="diagnosis_category",
            y="flag_rate",
            labels={"diagnosis_category": "Diagnosis Category", "flag_rate": "Flag Rate"},
        )
        fig1.update_yaxes(tickformat=".0%")
        fig1.update_layout(xaxis_title=None)
        st.plotly_chart(fig1, use_container_width=True)

    with chart_col2:
        st.subheader("Override Rate by Diagnosis Category")
        override_df = aggregate.override_rate_by_category(conn)
        fig2 = px.bar(
            override_df.sort_values("override_rate", ascending=False),
            x="diagnosis_category",
            y="override_rate",
            labels={"diagnosis_category": "Diagnosis Category", "override_rate": "Override Rate"},
        )
        fig2.update_yaxes(tickformat=".0%")
        fig2.update_layout(xaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)


def render_drilldown(conn):
    claim_ids = db.get_claim_ids(conn)
    selected_id = st.selectbox("Select a claim", options=claim_ids)

    if not selected_id:
        return

    trace = aggregate.claim_decision_trace(conn, selected_id)

    st.subheader(f"Claim {trace['claim_id']}")
    st.caption(trace["diagnosis_category"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Predicted LOS (days)", trace["predicted_los_days"])
    col2.metric("Actual LOS (days)", trace["actual_los_days"])
    col3.metric("Difference (days)", trace["los_delta"])

    st.info(trace["narrative"])

    st.write(f"**Denial flag:** {'Yes' if trace['denial_flag'] else 'No'}")
    st.write(f"**Clinician override logged:** {'Yes' if trace['clinician_override_logged'] else 'No'}")
    st.write(f"**Final decision:** {trace['final_decision'].capitalize()}")
    st.write(f"**Appealed:** {'Yes' if trace['appealed'] else 'No'}")
    st.write(f"**Appeal overturned:** {'Yes' if trace['appeal_overturned'] else 'No'}")


def main():
    st.set_page_config(page_title="Denial Audit Trail -- Synthetic Demo", layout="wide")
    st.title("Denial Audit Trail")
    st.warning(SYNTHETIC_BANNER)

    conn = get_conn()

    tab_dashboard, tab_drilldown = st.tabs(["Dashboard", "Claim Drill-Down"])

    with tab_dashboard:
        render_dashboard(conn)

    with tab_drilldown:
        render_drilldown(conn)


if __name__ == "__main__":
    main()
