<!--
task: verify_listing · feature: F-03 · tier: reasoning
inputs: {profile_json}, {listing_json}
output: app.schemas.listing.Verification
-->
TODO(F-03): write the prompt. It must tell the model to:
- score 0-100 against the profile and pick a verdict (strong / partial / weak / reject);
- list matched criteria, mismatches and missing data separately;
- judge only from the sourced fields provided, never from outside knowledge of the property.
