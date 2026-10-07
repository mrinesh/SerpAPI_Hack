import type { CompetitorReading, CompetitorReport, PropertyType } from "../../api/types";

type Level = CompetitorReport["density_level"];

const READING_LABELS: Record<CompetitorReading, string> = {
  competition: "Competition",
  cluster: "Business cluster",
};

/** What the density means for one reading (ADR 0023). Cautious on purpose: a count of map
 * results is a signal to check, not a verdict. */
const READING_TEXT: Record<CompetitorReading, Record<Level, (business: string) => string>> = {
  competition: {
    high: (b) => `Crowded: many ${b} places nearby compete for the same customers.`,
    medium: (b) => `Some ${b} competition nearby.`,
    low: (b) => `Few ${b} places nearby: less competition, but check that there is demand.`,
  },
  cluster: {
    high: (b) => `A strong ${b} cluster: an established business area, a sign of tenant demand.`,
    medium: (b) => `An established ${b} presence nearby, a sign of tenant demand.`,
    low: (b) => `Few ${b} businesses nearby: a weaker cluster for finding tenants.`,
  },
};

export interface ReadingLine {
  type: PropertyType;
  label: string; // "Business cluster: medium"
  text: string;
}

/** One line per property type the profile searched for; only one type when `only` is given
 * (the detail page reads the report for its own listing). */
export function readingLines(report: CompetitorReport, only?: PropertyType | null): ReadingLine[] {
  const level = report.density_level ?? "low";
  return (Object.entries(report.readings ?? {}) as [PropertyType, CompetitorReading][])
    .filter(([type]) => !only || type === only)
    .map(([type, reading]) => ({
      type,
      label: `${READING_LABELS[reading]}: ${level}`,
      text: READING_TEXT[reading][level](report.business_type),
    }));
}

/** "7 places within 2 km of the Koramangala centre, from the first 20 Google Maps results
 * (more exist, so this is a floor)". */
export function countLine(report: CompetitorReport): string {
  const count = report.competitors?.length ?? 0;
  const seen = `from the first ${report.results_seen} Google Maps results`;
  const floor = report.more_available ? " (more exist, so this is a floor)" : "";
  return `${count} ${count === 1 ? "place" : "places"} within ${report.radius_km} km of the ${report.locality} centre, ${seen}${floor}.`;
}
