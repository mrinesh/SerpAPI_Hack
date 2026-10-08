# S-04 · Commute times from google_maps_directions: is "9 AM" traffic-aware in India?

- **Status:** Done (2026-10-08); decisions at the end
- **Spend:** 4 SerpApi searches (spike) + 5 to record the demos' remaining hubs = 9
- **Evidence:** `backend/fixtures/serpapi/google_maps_directions/`; `tests/unit/test_area.py`
  (`test_departure_is_read_as_local_wall_clock_time`) checks the figures below.
- **Run one yourself:** `uv run python -m app.cli serp google_maps_directions
  start_coords=12.9698196,77.7499721 end_addr="Manyata Tech Park, Nagavara, Bengaluru"
  time=depart_at:1791882000`

Goal: before building F-23, find out whether `time=depart_at:<unix>` gives traffic-aware
driving times in Bengaluru, and whether a fixed departure keeps working once its date has passed.
SerpApi's docs don't cover either point.

## Method

The same request four times, changing only the departure. Each one started at Whitefield's
recorded F-05 centre (`12.9698196,77.7499721`), went to `Manyata Tech Park, Nagavara,
Bengaluru`, and used `travel_mode=0` (driving), `distance_unit=0` (km), `gl=in` and `hl=en`.

| `depart_at` | Meant as | Google's URL (`!8j`) | First route | Typical range | Google's note |
|---|---|---|---|---|---|
| 1791862200 | Tue 13 Oct 09:00 IST, as a true instant | `!8j1791862200` | 40 min, 21.5 km | 30–55 min | "the usual traffic" |
| 1791840600 | Tue 13 Oct 03:00 IST, as a true instant | `!8j1791840600` | 1 hr, 21.5 km | 50 min to 1 hr 25 min | "despite the usual traffic"; other routes "Heavy traffic, as usual" |
| 1790652600 | Tue 29 Sep 09:00 IST (in the past) | `!8j1790652600` | 40 min, 21.5 km | 30–55 min | "the usual traffic" |
| 1791882000 | **Tue 13 Oct 09:00 as local wall-clock time** (09:00Z) | `!8j1791882000` | **1 hr 10 min**, 21.4 km | **55 min to 1 hr 50 min** | "despite the usual traffic"; others "Heavy traffic, as usual" |

## Findings

1. **The times are traffic-aware.** The same 21.5 km takes 40 min in one slot and 1 hr 10 min in
   another, and `typical_duration_range` and `extensions` change with them.
2. **Google reads `depart_at` as local wall-clock time written as UTC.** SerpApi passes the
   value straight into Google Maps' `!8j` field. The "09:00 IST" instant came back as a quiet
   03:30 drive, and the "03:00 IST" instant as a 21:30 evening rush. For 09:00 in Bengaluru, send
   the Unix time of 09:00 **UTC** on that date.
3. **A past date still works.** The 29 Sep departure returned the same route, times and range as
   13 Oct at the same hour, so Google answers with typical traffic for that weekday and hour.
   A pinned departure therefore keeps working after its date.
4. **Hub addresses resolve to the intended places** (from `places_info`): "RMZ ECOWORLD,
   Bellandur", "Manyata Tech Park … Nagavara" (once "Manyata Tech Park Rd") and "Electronic
   City Phase I". The resolved address can vary slightly between departures, so hub positions
   are kept per locality and never treated as one fixed point.
5. **Range formats seen:** "30–55 min", "40 min to 1 hr", "55 min to 1 hr 50 min",
   "1 hr 5 min to 2 hr 20 min" and "1–2 hr".

## Decisions (ADR 0026)

- `COMMUTE_DEPART_AT` defaults to `1791882000`, which is Tuesday 09:00 local time. It is pinned
  so that the cache key and recordings never change.
- Show Google's route time for that departure, together with its typical range. Both are
  SerpApi fields and neither is computed by us.
- Recorded demo drives at 9 AM:

  | From | ORR (Bellandur) | Manyata Tech Park | Electronic City |
  |---|---|---|---|
  | Whitefield | 1 hr (45 min–1 hr 30), 11.8 km | 1 hr 10 (55 min–1 hr 50), 21.4 km | 1 hr 20 (1–2 hr), 33.2 km |
  | Koramangala | 45 min (35 min–1 hr 10), 9.0 km | 1 hr 5 (45 min–1 hr 40), 17.9 km | 35 min (22–55 min), 14.7 km |
