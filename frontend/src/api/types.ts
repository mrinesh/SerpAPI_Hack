/**
 * Friendly names for the generated OpenAPI types. Never hand-write a response type: change the
 * Pydantic schema in backend/app/schemas, run `make types`, then alias it here.
 */

import type { components } from "./schema";

type Schemas = components["schemas"];

export type HealthStatus = Schemas["HealthStatus"];
export type BudgetStatus = Schemas["BudgetStatus"];
export type InvestorProfileIn = Schemas["InvestorProfileIn"];
export type InvestorProfile = Schemas["InvestorProfile"];
export type ProfileOptions = Schemas["ProfileOptions"];
export type Segment = Schemas["Segment"];
export type PropertyType = Schemas["PropertyType"];
export type InvestmentGoal = Schemas["InvestmentGoal"];
export type RiskAppetite = Schemas["RiskAppetite"];
export type ROIMeasure = Schemas["ROIMeasure"];
export type PipelineRun = Schemas["PipelineRun"];
export type StageEvent = Schemas["StageEvent"];
export type Recommendation = Schemas["Recommendation"];
export type Listing = Schemas["Listing"];
export type SaleStatus = Schemas["SaleStatus"];
export type Portal = Schemas["Portal"];
export type RunStatus = Schemas["RunStatus"];
export type Verification = Schemas["Verification"];
export type QualityFlag = Schemas["QualityFlag"];
export type InvestmentMetrics = Schemas["InvestmentMetrics"];
export type AreaIntel = Schemas["AreaIntel"];
export type AreaAccess = Schemas["AreaAccess"];
export type Amenity = Schemas["Amenity"];
export type CompetitorReport = Schemas["CompetitorReport"];
export type PropertyDetail = Schemas["PropertyDetail"];
export type PriceObservation = Schemas["PriceObservation"];
export type CompareResult = Schemas["CompareResult"];
export type SavedProperty = Schemas["SavedProperty"];
export type Alert = Schemas["Alert"];
export type SourceRef = Schemas["SourceRef"];
export type SerpEngine = Schemas["SerpEngine"];
export type ExtractionMethod = Schemas["ExtractionMethod"];
/** Any `Sourced[T]` field (F-11): a value with its confidence, method and sources. */
export type SourcedField =
  | Schemas["Sourced_float_"]
  | Schemas["Sourced_int_"]
  | Schemas["Sourced_str_"]
  | Schemas["Sourced_PropertyType_"]
  | Schemas["Sourced_SaleStatus_"]
  | Schemas["Sourced_GeoPoint_"];
export type TargetSuggestion = Schemas["TargetSuggestion"];
export type TargetSuggestionIn = Schemas["TargetSuggestionIn"];
