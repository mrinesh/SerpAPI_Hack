import { useSearchParams } from "react-router";

import { Placeholder } from "../components/Placeholder";

export function ComparePage() {
  const [params] = useSearchParams();
  const ids = params.getAll("ids");
  return (
    <Placeholder title="Compare" features={["F-08"]}>
      <p>
        Side-by-side table for 2–4 properties: price, size, price per sq ft vs area, yield, match
        score, amenities, flags. The best value in each row is highlighted.
      </p>
      <p>Selected: {ids.length ? ids.join(", ") : "none"}</p>
    </Placeholder>
  );
}
