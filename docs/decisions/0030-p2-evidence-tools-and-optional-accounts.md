# 0030. P2 evidence tools and optional accounts

Status: Accepted

P2 reuses run snapshots. Risk mentions are cited investigation flags with unknowns, not hazard
probabilities or legal clearance. Forecasts continue only adequately sampled public interest,
with a holdout error check and descriptive bands; a single annual price change cannot support
a price forecast. Neither changes investment ranking. PDF export reads the authorized snapshot.

Owned-property tracking uses manual, dated amounts. Scenarios compute amortization and exit
cash flows from explicit assumptions rather than letting the LLM invent financing terms.
The language parser produces a reviewable partial draft from a bounded grammar, preserving
exact matches and unresolved criteria. This works offline without fabricated provider responses.

Accounts are optional (`AUTH_ENABLED=false` by default, forced off for `make demo`). New users
never claim pre-existing data. Additive `profile_owners`, `users`, `auth_sessions`, `auth_attempts`
and `user_saved_properties` tables preserve legacy profiles and saved notes without rebuilding
their primary keys. Missing owners represent the local workspace; owner-filtered profile IDs
scope runs, details, observations, alerts and app history. Portfolio rows already have owner IDs.
Shared public listing and area caches contain no private notes or investor criteria.

Sessions use random 256-bit tokens stored only as hashes, 24-hour expiry, rotation on login,
revocation on logout, HttpOnly/SameSite Strict cookies and CSRF headers for writes. Passwords
use salted scrypt (N=2^17,r=8,p=1). Registration/login are atomically limited to 10 attempts per
IP per 15-minute window in SQLite. JSON responses use no-store; the frontend clears private
query caches on account changes or expiry. Scheduled alerts explicitly run as an internal system
job; API-triggered checks cover the calling owner's profiles only. Pipeline threads recover
the owner from the stored profile relation. Tests exercise direct cross-account reads/mutations
and PDF downloads, not just hidden UI controls.

Sources: [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[CFPB amortization](https://www.consumerfinance.gov/ask-cfpb/how-does-paying-down-a-mortgage-work-en-1943/).

This is a local account system, not a hosted identity provider. Password recovery, MFA,
email verification, admin account management and user billing are outside this first release.
HTTPS and Secure cookies are required for hosted use. Reverse-proxy deployments must configure
trusted client IP handling and edge rate limits; a proxy may otherwise share an IP's attempt cap.
