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
export type PipelineRun = Schemas["PipelineRun"];
export type StageEvent = Schemas["StageEvent"];
export type Recommendation = Schemas["Recommendation"];
export type Listing = Schemas["Listing"];
export type Verification = Schemas["Verification"];
export type InvestmentMetrics = Schemas["InvestmentMetrics"];
export type AreaIntel = Schemas["AreaIntel"];
export type CompetitorReport = Schemas["CompetitorReport"];
export type PropertyDetail = Schemas["PropertyDetail"];
export type CompareResult = Schemas["CompareResult"];
export type SavedProperty = Schemas["SavedProperty"];
export type Alert = Schemas["Alert"];
export type SourceRef = Schemas["SourceRef"];
