# 0007. Single-user local app; auth deferred

- **Status:** Superseded for optional account mode by [ADR 0030](0030-p2-evidence-tools-and-optional-accounts.md); retained for local demo mode
- **Date:** 2026-10-03

## Context
The concept lists auth in the backend layer. The hackathon demo runs locally for one person, and
the deadline is seven days away.

## Decision
No authentication in the MVP. Profiles, saved properties and alerts belong to the single local
user. Auth and multi-user are tracked as F-21 (P2).

## Consequences
- Less to build and no credential handling in a public repo.
- Adding auth later means adding an owner column to profiles, saved properties and alerts.
