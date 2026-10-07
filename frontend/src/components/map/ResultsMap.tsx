import { divIcon } from "leaflet";
import { useEffect } from "react";
import { CircleMarker, LayerGroup, LayersControl, MapContainer, Marker, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import { Link } from "react-router";

import { formatInr } from "../../lib/money";
import {
  AMENITY_COLORS,
  COMPETITOR_COLOR,
  legendEntries,
  markerColor,
  STATUS_LABELS,
  type LatLng,
  type ListingMarker,
  type LocalityMarker,
  type MapItem,
  type MapLayout,
} from "./mapLayout";

const BENGALURU: LatLng = [12.9716, 77.5946];
const GROUP_LIMIT = 8;

/** F-19: a run's candidates on OpenStreetMap. Positions come only from SerpApi: a candidate's
 * own Google Maps GPS, or, when it has none, its locality's centre, drawn as one dashed group so
 * no point is invented. Amenities are the area's metro stations, schools and hospitals (F-05);
 * competitors are a commercial run's same-category businesses (F-06), on by default. With `focusId` (the detail page) the map shows one property and links nowhere. */
export function ResultsMap({ layout, runId, focusId, showAmenities = false, showFiltered = false, className = "h-96" }: {
  layout: MapLayout;
  runId: string;
  focusId?: string;
  showAmenities?: boolean;
  showFiltered?: boolean;
  className?: string;
}) {
  const filtered = layout.listings.filter((m) => m.item.status === "filtered");
  const visible = layout.listings.filter((m) => m.item.status !== "filtered");
  const link = focusId ? undefined : (item: MapItem) => `/runs/${runId}/properties/${item.listing.id}`;
  return (
    <div className={`relative z-0 overflow-hidden rounded-xl border border-slate-200 ${className}`}>
      <MapContainer center={layout.bounds[0] ?? BENGALURU} zoom={12} zoomSnap={0.5} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds bounds={layout.bounds} />
        {visible.map((marker) => <ListingPin key={marker.item.listing.id} marker={marker} link={link} />)}
        {layout.localities.map((group) => <LocalityPin key={group.locality} group={group} link={link} single={!!focusId} />)}
        <LayersControl position="topright">
          {filtered.length > 0 && (
            <LayersControl.Overlay name={`Filtered out (${filtered.length})`} checked={showFiltered}>
              <LayerGroup>
                {filtered.map((marker) => <ListingPin key={marker.item.listing.id} marker={marker} link={link} />)}
              </LayerGroup>
            </LayersControl.Overlay>
          )}
          {layout.amenities.length > 0 && (
            <LayersControl.Overlay name="Metro, schools, hospitals" checked={showAmenities}>
              <LayerGroup>
                {layout.amenities.map(({ position, amenity, locality }) => (
                  <CircleMarker
                    key={`${amenity.name}-${position.join(",")}`}
                    center={position}
                    radius={5}
                    pathOptions={{ color: "#fff", weight: 1.5, fillColor: AMENITY_COLORS[amenity.category], fillOpacity: 0.9 }}
                  >
                    <Tooltip>
                      {amenity.name}
                      {amenity.distance_km != null && ` · ${amenity.distance_km} km from the ${locality} centre`}
                    </Tooltip>
                  </CircleMarker>
                ))}
              </LayerGroup>
            </LayersControl.Overlay>
          )}
          {layout.competitors.length > 0 && (
            <LayersControl.Overlay
              name={`${layout.competitors[0].businessType} nearby (${layout.competitors.length})`}
              checked
            >
              <LayerGroup>
                {layout.competitors.map(({ position, competitor }) => (
                  <CircleMarker
                    key={`${competitor.place_id ?? competitor.name}-${position.join(",")}`}
                    center={position}
                    radius={5}
                    pathOptions={{ color: "#fff", weight: 1.5, fillColor: COMPETITOR_COLOR, fillOpacity: 0.9 }}
                  >
                    <Tooltip>
                      {competitor.name}
                      {competitor.category && ` · ${competitor.category}`}
                      {competitor.rating != null && ` · ${competitor.rating}★ (${competitor.reviews ?? 0})`}
                      {competitor.distance_km != null && ` · ${competitor.distance_km} km from the centre`}
                    </Tooltip>
                  </CircleMarker>
                ))}
              </LayerGroup>
            </LayersControl.Overlay>
          )}
        </LayersControl>
      </MapContainer>
    </div>
  );
}

/** Opens on the given points, and re-fits when they change (areas load after candidates). */
function FitBounds({ bounds }: { bounds: LatLng[] }) {
  const map = useMap();
  const key = JSON.stringify(bounds);
  useEffect(() => {
    const points = JSON.parse(key) as LatLng[];
    map.invalidateSize(); // the container may have been resized since the map was created
    if (points.length > 0) map.fitBounds(points, { padding: [32, 32], maxZoom: 15 });
  }, [map, key]);
  return null;
}

function ListingPin({ marker, link }: { marker: ListingMarker; link?: (item: MapItem) => string }) {
  const { item, position } = marker;
  const popup = (
    <Popup>
      <ItemLine item={item} link={link} />
      <p className="!my-1 text-xs text-slate-500">Position from Google Maps.</p>
    </Popup>
  );
  if (item.status === "ranked") {
    const icon = divIcon({
      className: "",
      iconSize: [26, 26],
      html: `<span style="background:${markerColor(item)}" class="flex h-[26px] w-[26px] items-center justify-center rounded-full border-2 border-white text-xs font-semibold text-white shadow">${item.rank}</span>`,
    });
    return <Marker position={position} icon={icon} zIndexOffset={1000 - (item.rank ?? 0)}>{popup}</Marker>;
  }
  return (
    <CircleMarker
      center={position}
      radius={6}
      pathOptions={{ color: "#fff", weight: 1.5, fillColor: markerColor(item), fillOpacity: 0.85 }}
    >
      {popup}
    </CircleMarker>
  );
}

function LocalityPin({ group, link, single }: { group: LocalityMarker; link?: (item: MapItem) => string; single: boolean }) {
  const icon = divIcon({
    className: "",
    iconSize: [34, 34],
    html: `<span class="flex h-[34px] w-[34px] items-center justify-center rounded-full border-2 border-dashed border-slate-600 bg-white/90 text-xs font-semibold text-slate-700 shadow">${single ? "≈" : group.items.length}</span>`,
  });
  const shown = group.items.slice(0, GROUP_LIMIT);
  return (
    <Marker position={group.position} icon={icon}>
      <Popup>
        <p className="!my-0 text-xs text-slate-500">
          {single
            ? `No position was quoted for this property; shown at the ${group.locality} centre.`
            : `${group.items.length} candidates with no position of their own, shown at the ${group.locality} centre.`}
        </p>
        <ul className="!my-1 max-h-48 space-y-1 overflow-y-auto">
          {shown.map((item) => <li key={item.listing.id}><ItemLine item={item} link={link} /></li>)}
        </ul>
        {group.items.length > shown.length && (
          <p className="!my-0 text-xs text-slate-500">+{group.items.length - shown.length} more in the list below.</p>
        )}
      </Popup>
    </Marker>
  );
}

function ItemLine({ item, link }: { item: MapItem; link?: (item: MapItem) => string }) {
  const { listing } = item;
  const status = item.status === "ranked" ? `Rank ${item.rank} · Score ${item.score}/100` : STATUS_LABELS[item.status];
  return (
    <div className="text-xs">
      {link
        ? <Link to={link(item)} className="font-medium text-slate-900 hover:underline">{listing.name}</Link>
        : <span className="font-medium text-slate-900">{listing.name}</span>}
      <span className="block text-slate-600">
        <span style={{ color: markerColor(item) }}>●</span> {status}
        {listing.price_inr.value != null && ` · ${formatInr(listing.price_inr.value)}`}
      </span>
    </div>
  );
}

/** The key under the map: only the colours on it, the approximate-position group, and what is missing. */
export function MapLegend({ layout }: { layout: MapLayout }) {
  const dot = (color: string, label: string) => (
    <span key={label} className="inline-flex items-center gap-1">
      <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} /> {label}
    </span>
  );
  return (
    <div className="space-y-1 text-xs text-slate-500">
      <p className="flex flex-wrap gap-x-3 gap-y-1">
        {legendEntries(layout).map(({ color, label }) => dot(color, label))}
        {layout.localities.length > 0 && (
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-dashed border-slate-600" /> No own position: locality centre
          </span>
        )}
      </p>
      {layout.unplaced.length > 0 && (
        <p>{layout.unplaced.length} candidates are not on the map: no position was quoted and their locality has no area data yet.</p>
      )}
    </div>
  );
}
