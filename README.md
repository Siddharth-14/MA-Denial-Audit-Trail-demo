# Denial Audit Trail

A small demo app that makes algorithmic Medicare Advantage post-acute-care denial decisions
auditable after the fact. It is inspired by public reporting on *Estate of Gene B. Lokken et al.
v. UnitedHealth Group*, litigation over UnitedHealth/naviHealth's nH Predict algorithm, and
illustrates one possible pattern for a decision-audit trail: a per-claim record of what an
algorithm predicted, what actually happened, whether a clinician overrode the flag, and what
happened on appeal.

This project uses **100% synthetic data**, generated locally by a seeded script (see
`data/generate_synthetic_claims.py`). It has no access to and does not use any real
UnitedHealth/Optum system, data, model, or code, and it does not reproduce or reverse-engineer the
actual nH Predict algorithm. See **Non-goals** below for the full scope boundary.

## Litigation context and sources

- ArentFox Schiff, discovery-order summary of *Estate of Gene B. Lokken et al. v. UnitedHealth
  Group*
- CBS News, reporting on the *Lokken* litigation and the disclosed AI-driven denial/appeal
  statistics
- Georgetown University Health Care Litigation Tracker, entry for *Estate of Gene B. Lokken et al.
  v. UnitedHealth Group*

### Non-goals (hard)

1. **No real PHI, no connection to any Optum/UnitedHealth internal system.** 100% synthetic data,
   generated locally and visibly labeled "SYNTHETIC" throughout the UI.
2. **Does not reproduce or reverse-engineer the actual nH Predict model.** Only the documented
   denial-flow *mechanics* (predicted-vs-actual LOS trigger, override presence) are modeled — this
   is the non-goal a reader would most reasonably expect to be in scope, and it isn't.
3. **Renders no clinical or legal judgment** on whether any real historical denial was correct.
4. **No live claims-intake or appeals-processing workflow** — this is a read-only audit/observability
   layer, not a production decision system.
5. **No integration with any real EHR, claims clearinghouse, or CMS system** — all data loads from a
   bundled seed file at startup.

### Data sources

| Source | Public or synthetic | How obtained | Limitation |
|---|---|---|---|
| Individual claim records (predicted LOS, actual LOS, override flag, appeal outcome) | Synthetic | Generated in Python from a documented rule (denial flag fires when actual LOS exceeds predicted LOS by a threshold, absent a logged override) | Not real Optum data; illustrates the *mechanism*, not real patients |
| Overall denial/overturn-rate scale (~90% overturn on appeal) | Public, used only to calibrate synthetic distribution | CBS News reporting on *Lokken* court filings; AMA 2024 physician survey on AI-driven prior-auth denials | One party's disputed litigation statistic, not an audited industry baseline — presented as such in the UI |
| Diagnosis category taxonomy | Public | Simplified categories loosely modeled on CMS post-acute care groupings | Simplified for demo clarity, not clinically exhaustive |

## Running locally

```bash
pip install -r requirements.txt
python data/generate_synthetic_claims.py   # optional -- regenerates data/claims.db
streamlit run app/streamlit_app.py
```

The repo ships with a pre-generated `data/claims.db`, so the app runs instantly with zero setup.

## Deploying (Streamlit Community Cloud)

1. Push this repo to a public GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo, and set the main file
   path to `app/streamlit_app.py`.
3. Deploy. No secrets or environment variables are needed — there are no external API calls.

**Live demo:** _TBD — deploy via Streamlit Community Cloud, then add the link here._
