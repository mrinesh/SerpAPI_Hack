# S-02 · Extraction accuracy: regex vs DeepSeek

- **Status:** Done (2026-10-07); decisions at the end
- **Spend:** 0 SerpApi searches (S-01 recordings); 31 DeepSeek lite calls, recorded
- **Labels:** `backend/fixtures/spikes/s02_labels.json`, written by Claude Code from the snippet
  text. **Awaiting review by the product owner**; the numbers below change if a label does.
- **Run it:** `uv run python scripts/s02_accuracy.py` (replay; `--regex-only` needs no
  recordings, `--record` records missing calls). `tests/integration/test_s02_replay.py` checks
  that it still gives these numbers.

Goal: measure how well listing facts are read from the portals' search-page snippets, and decide
which fields need the LLM and which the regex parsers handle alone.

## Sample

20 priced snippet entries from the recorded S-01 searches (portal search pages, never single
listings, ADR 0011), one per result where possible:

| | 99acres | NoBroker | MagicBricks | Total |
|---|---|---|---|---|
| Residential | 7 | 4 | 2 | 13 |
| Commercial | 3 | 3 | 1 | 7 |

19 are listings; 1 is a page description that cleaning nevertheless reads as one.

Each label is what a careful reader takes from the entry's own text: price, price per sq ft,
size, BHK and sale status. A value that follows by arithmetic from two stated figures
(price = rate × size) is labelled as derived; ranges are labelled with their lower bound, as
the parser intends; text stating two statuses ("Resale … Ready To Move") accepts either.
Numbers match within 2%. Prices quoted as sales but plainly rents (₹3.6 Lac for 4,800 sq ft)
are scored as quoted: catching those is F-12's job, not extraction's.

## Three ways of reading

1. **Regex**: the cleaning parsers alone (`cleaning.py`), what discovery produces.
2. **LLM alone**: `extract_listing` (DeepSeek lite) asked for every field, given the entry's text
   with no parsed facts, through the shipped grounding check (each value must be supported by a
   quoted span of the text).
3. **Shipped**: regex first, then `extract_listing` only for the fields regex left empty.

## Results (19 listings)

Correct out of 19, with wrong (w), missed (m) and spurious (s: a value the text does not state).

| Field | Regex | LLM alone | Shipped |
|---|---|---|---|
| Price | **19** | 15 (4 m) | **19** |
| Price per sq ft | **19** | not asked (computed in code) | – |
| Size | 18 (1 w) | 14 (5 m) | 18 (1 w) |
| BHK | **19** | **19** | **19** |
| Status | 18 (1 s) | **19** | 18 (1 s) |

**Regex errors** (both pass through the shipped pipeline, because regex left no gap to fill):
- *Size from a range*: 99acres, "ranging from 1415.0 sq. ft. to 1470.0 sq. ft., ₹1.25 - 1.28 Cr
  ₹10,241 /sqft". The parser ignores the stated range and computes 1,220.6 sq ft from
  price ÷ rate.
- *Status from page filter text*: MagicBricks, "Choose from over 22+ Flats … Buy Ready to move,
  Resale, apartments/flats in Hebbal within ₹ 1 Crore. ₹1.15 Cr". "Ready to move" describes the
  page's filters, not the property.

**LLM-alone errors**: none wrong, none invented. It misses what needs arithmetic: the
NoBroker entries that quote rate and size but no price ("₹7,600/sq.ft · 1250 sqft"), the sizes
implied by price ÷ rate, and the "₹1.25 - 1.28 Cr" range. Its grounding check drops any figure
that is not written in the text, by design (ADR 0013).

**Not a listing**: NoBroker's "Finding for resale or new flats for sale below 60 lakhs in
Electronic City … 45 Lakhs Flats for" is a page description; all three ways read it as a
₹45 L flat. Verification is what has to catch it.

## Decisions

- **Regex stays first for every field.** It is right on 19/19 prices, rates and BHK, needs no
  call, and does the arithmetic the grounded LLM refuses to do.
- **The LLM stays a gap filler**, as shipped. It never produced a wrong value here, so it is a
  safe fallback when regex finds nothing, but asked for everything it would lose a fifth of
  prices and a quarter of sizes.
- **Status is the one field where the LLM beat regex**, by telling page filters from the entry.
  Not enough on one error to change the design; revisit with the parser fixes below.
- **Parser follow-ups** (F-02, P1), each with its S-02 entry as the test case:
  1. take a stated size range ("ranging from X sq. ft. to Y") before computing size;
  2. do not read sale status from page filter text ("Buy Ready to move, Resale, …");
  3. skip "<price> Flats for" page-description phrases as entries.
