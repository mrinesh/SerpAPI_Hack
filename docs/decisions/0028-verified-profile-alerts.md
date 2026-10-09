# 0028: Alerts compare successful profile snapshots

An alert check refreshes each idle profile synchronously through the existing budgeted
pipeline. Only strong or partial verified matches from successful runs produce alerts.
Failed refreshes are reported per profile and do not replace the successful baseline; other
profiles still get checked. The first successful check reports verified matches as new.
Later checks compare against the latest successful run and suppress previously seen IDs.

Candidate IDs include price (ADR 0011). Across different IDs, price comparisons require an
explicit project name, stated size, same portal/locality/type/bedrooms and exactly one quote
per identity in both runs. Generic or ambiguous snippets never establish a price drop.
Alerts describe a change in quoted price and ask the user to confirm the same unit.

A process-wide lock serializes manual and scheduled checks. Active profiles are skipped.
Event IDs are deterministic per profile/run/kind/listing. Read status is persisted and marking
read is idempotent. This is a single-process local app, not a distributed task queue.
