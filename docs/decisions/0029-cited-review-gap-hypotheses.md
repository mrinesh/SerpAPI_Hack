# 0029: Review gaps are sampled, cited hypotheses

For each commercial locality, read the first low-rating review page of the business with
the most reviews and a Maps data ID. The default is one place; a setting can raise it to
three. No pagination. The existing gateway enforces cache, replay and budgets. A missing
review or model response is visible and retried on the next run, preserving the Maps report.

DeepSeek selects from a fixed set of complaint themes with exact quotes and review IDs.
Code requires two distinct reviews rated at most 3, checks each quote against the stored
text and the theme vocabulary, and computes displayed counts. Unknown IDs, fabricated
quotes, duplicate citations and unsupported themes are discarded. Confidence is 0.55:
this is a limited, low-rating-biased sample, not a prevalence estimate or proof of demand.
The result is a potential gap to investigate and never changes property rankings.

The response retains bounded review text and source links, excludes author information
from model input, and freezes the report with the run. Report schema version 2 invalidates
old shared caches; old run snapshots remain readable with review status `not_loaded`.

Provider parameters and fields were checked against the
[SerpApi Google Maps Reviews documentation](https://serpapi.com/google-maps-reviews-api)
on 2026-10-10. The commercial demo adds one real SerpApi recording and one real DeepSeek
recording; tests never fake committed provider recordings.
