# 0027: Saved properties and comparison use stored facts

Saved properties are keyed by listing ID, with editable notes and the original save time.
Saving again updates the note; removing is idempotent. This is the existing single-user app.

Comparison accepts 2–4 distinct IDs and assembles each property's latest stored run detail.
It never spends searches or recomputes metrics. The source search is linked in every column.
The UI highlights ties for the lowest cost or highest value, ignoring unknown values and
requiring at least two known values. Scores from different profiles are not highlighted
against each other, since they have different criteria. Row highlights are aids for reading,
not a claim that a property is the best investment.
