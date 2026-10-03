import { useParams } from "react-router";

import { Placeholder } from "../components/Placeholder";

export function RunPage() {
  const { runId } = useParams();
  return (
    <Placeholder title={`Run ${runId ?? ""}`} features={["F-20", "F-04", "F-19", "F-12"]}>
      <p>
        Live pipeline progress (plan → fetch → clean → verify → enrich → rank) with counts,
        searches used and cache hits, polled from <code>GET /api/runs/:id</code>.
      </p>
      <p>
        Then the ranked shortlist: score, plain-language reason, key metrics and quality flags per
        card, a map of results coloured by score, and a "filtered out" list with reasons.
      </p>
    </Placeholder>
  );
}
