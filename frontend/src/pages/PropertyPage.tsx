import { useParams } from "react-router";

import { Placeholder } from "../components/Placeholder";

export function PropertyPage() {
  const { listingId } = useParams();
  return (
    <Placeholder
      title={`Property ${listingId ?? ""}`}
      features={["F-07", "F-09", "F-05", "F-06", "F-11"]}
    >
      <p>
        Header facts (price, size, type, locality) each with a source link and confidence badge;
        investment metrics (price per sq ft vs area, yields, cap rate) with assumptions.
      </p>
      <p>
        Area panel: amenities map, news and infrastructure, price level, rental demand. Commercial
        only: competitor map, density, ratings and market gaps. Footer: every source used.
      </p>
    </Placeholder>
  );
}
