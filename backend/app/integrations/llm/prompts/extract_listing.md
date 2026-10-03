<!--
task: extract_listing · feature: F-03 · tier: lite
inputs: {hit_json} (one RawSearchHit)
output: app.pipeline.verification.ExtractedListing
-->
TODO(F-03): write the prompt. It must tell the model to:
- classify the hit as listing / project / aggregate / other before extracting anything;
- extract only what the text states (price, size, bedrooms, type, locality, amenities, posted date);
- return null rather than guess, with a per-field confidence and the exact text span used;
- normalise Indian price formats ("85 L", "1.2 Cr", "₹ 45,000/month") to integer INR.
