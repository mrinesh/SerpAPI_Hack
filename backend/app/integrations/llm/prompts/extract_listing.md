<!--
task: extract_listing · feature: F-03 · tier: lite
inputs: {listing_json} (one candidate, with its `evidence` snippet text)
output: app.pipeline.verification.ExtractedListing
-->
TODO(F-03): write the prompt. It must tell the model to:
- extract only what the evidence text states (price, size, bedrooms, type, sale status);
- return null rather than guess, with a per-field confidence and the exact text span used;
- normalise Indian price formats ("85 L", "1.2 Cr", "₹ 45,000/month") to integer INR.
