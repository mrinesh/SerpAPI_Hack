/**
 * Profile wizard state and its pure logic: per-step checks, and conversion to and from the API
 * shape. The backend is the authority on validation; these checks only catch the obvious before
 * a round trip, and server 422s land in the same `FieldErrors` shape.
 */

import type {
  InvestmentGoal,
  InvestorProfile,
  InvestorProfileIn,
  ProfileOptions,
  PropertyType,
  RiskAppetite,
  Segment,
  TargetSuggestionIn,
} from "../../api/types";
import { fromInr, toInr, type MoneyUnit } from "../../lib/money";

export interface MoneyValue {
  amount: string;
  unit: MoneyUnit;
}

export interface ProfileFormState {
  name: string;
  segment: Segment | "";
  propertyTypes: PropertyType[];
  sizeMin: string;
  sizeMax: string;
  businessType: string;
  localities: string[];
  mustHaves: string[];
  budgetMin: MoneyValue;
  budgetMax: MoneyValue;
  goal: InvestmentGoal | "";
  targetRoi: string;
  expectedGrowth: string;
  riskAppetite: RiskAppetite | "";
}

type ApiField = keyof InvestorProfileIn;

/** API field name -> message. */
export type FieldErrors = Partial<Record<ApiField, string>>;

/** Which API field each form value is sent as, so editing a value clears its error. */
export const FORM_TO_API: Record<keyof ProfileFormState, ApiField> = {
  name: "name",
  segment: "segment",
  propertyTypes: "property_types",
  sizeMin: "size_min_sqft",
  sizeMax: "size_max_sqft",
  businessType: "business_type",
  localities: "localities",
  mustHaves: "must_haves",
  budgetMin: "budget_min_inr",
  budgetMax: "budget_max_inr",
  goal: "goal",
  targetRoi: "target_roi_pct",
  expectedGrowth: "expected_growth_pct",
  riskAppetite: "risk_appetite",
};

export const STEPS: { title: string; fields: ApiField[] }[] = [
  {
    title: "What",
    fields: ["name", "segment", "property_types", "size_min_sqft", "size_max_sqft", "business_type"],
  },
  { title: "Where", fields: ["city", "localities", "must_haves"] },
  {
    title: "Money",
    fields: [
      "budget_min_inr",
      "budget_max_inr",
      "goal",
      "target_roi_pct",
      "expected_growth_pct",
      "risk_appetite",
    ],
  },
];

export function emptyForm(): ProfileFormState {
  return {
    name: "",
    segment: "",
    propertyTypes: [],
    sizeMin: "",
    sizeMax: "",
    businessType: "",
    localities: [],
    mustHaves: [],
    budgetMin: { amount: "", unit: "lakh" },
    budgetMax: { amount: "", unit: "lakh" },
    goal: "",
    targetRoi: "",
    expectedGrowth: "",
    riskAppetite: "",
  };
}

export function formFromProfile(profile: InvestorProfile): ProfileFormState {
  return {
    name: profile.name,
    segment: profile.segment,
    propertyTypes: profile.property_types,
    sizeMin: profile.size_min_sqft?.toString() ?? "",
    sizeMax: profile.size_max_sqft?.toString() ?? "",
    businessType: profile.business_type ?? "",
    localities: profile.localities,
    mustHaves: profile.must_haves ?? [],
    budgetMin:
      profile.budget_min_inr != null ? fromInr(profile.budget_min_inr) : { amount: "", unit: "lakh" },
    budgetMax: fromInr(profile.budget_max_inr),
    goal: profile.goal,
    targetRoi: profile.target_roi_pct.toString(),
    expectedGrowth: profile.expected_growth_pct?.toString() ?? "",
    riskAppetite: profile.risk_appetite,
  };
}

/** True when the goal's ROI measure involves price growth, so the growth override matters. */
export function goalUsesGrowth(goal: ProfileFormState["goal"], options: ProfileOptions): boolean {
  const measure = options.goals.find((g) => g.value === goal)?.measure;
  return measure !== undefined && measure !== "rental_yield";
}

export function validateStep(
  step: number,
  form: ProfileFormState,
  options: ProfileOptions,
): FieldErrors {
  const errors: FieldErrors = {};
  if (step === 0) {
    if (!form.name.trim()) errors.name = "Give the profile a name.";
    if (!form.segment) errors.segment = "Choose residential or commercial.";
    if (form.propertyTypes.length === 0)
      errors.property_types = "Choose at least one property type.";
    const sizeMin = parseWholeNumber(form.sizeMin);
    const sizeMax = parseWholeNumber(form.sizeMax);
    if (sizeMin === "invalid") errors.size_min_sqft = "Enter a whole number of sq ft.";
    if (sizeMax === "invalid") errors.size_max_sqft = "Enter a whole number of sq ft.";
    else if (typeof sizeMin === "number" && typeof sizeMax === "number" && sizeMax < sizeMin)
      errors.size_max_sqft = "Maximum size must be at least the minimum size.";
    if (form.segment === "commercial" && !form.businessType.trim())
      errors.business_type = "Business type is required for commercial profiles.";
  }
  if (step === 1) {
    if (form.localities.length === 0) errors.localities = "Choose at least one locality.";
    if (form.localities.length > options.max_localities)
      errors.localities = `Choose at most ${options.max_localities} localities.`;
  }
  if (step === 2) {
    const budgetMin = toInr(form.budgetMin.amount, form.budgetMin.unit);
    const budgetMax = toInr(form.budgetMax.amount, form.budgetMax.unit);
    if (form.budgetMin.amount.trim() && budgetMin === null)
      errors.budget_min_inr = "Enter a number.";
    if (!form.budgetMax.amount.trim()) errors.budget_max_inr = "Enter the maximum budget.";
    else if (budgetMax === null || budgetMax === 0)
      errors.budget_max_inr = "Enter a number above zero.";
    else if (budgetMin !== null && budgetMax < budgetMin)
      errors.budget_max_inr = "Maximum budget must be at least the minimum budget.";
    if (!form.goal) errors.goal = "Choose an investment goal.";
    const roi = parsePercent(form.targetRoi, 0, 100);
    if (roi === null || roi === "invalid")
      errors.target_roi_pct = "Enter a target ROI between 0 and 100%.";
    if (goalUsesGrowth(form.goal, options) && parsePercent(form.expectedGrowth, -100, 100) === "invalid")
      errors.expected_growth_pct = "Enter a growth rate between -100 and 100%, or leave it blank.";
    if (!form.riskAppetite) errors.risk_appetite = "Choose a risk appetite.";
  }
  return errors;
}

export function validateAll(form: ProfileFormState, options: ProfileOptions): FieldErrors {
  return STEPS.reduce<FieldErrors>(
    (errors, _, step) => ({ ...errors, ...validateStep(step, form, options) }),
    {},
  );
}

/** The first step holding an error, or -1. */
export function firstStepWithError(errors: FieldErrors): number {
  return STEPS.findIndex((step) => step.fields.some((field) => errors[field]));
}

/** The API payload for a form that passed `validateAll`. */
export function toPayload(form: ProfileFormState, options: ProfileOptions): InvestorProfileIn {
  const growth = goalUsesGrowth(form.goal, options) ? parsePercent(form.expectedGrowth, -100, 100) : null;
  return {
    name: form.name.trim(),
    segment: form.segment as Segment,
    property_types: form.propertyTypes,
    size_min_sqft: numberOrNull(parseWholeNumber(form.sizeMin)),
    size_max_sqft: numberOrNull(parseWholeNumber(form.sizeMax)),
    business_type: form.segment === "commercial" ? form.businessType.trim() : null,
    city: options.city,
    localities: form.localities,
    must_haves: form.mustHaves,
    budget_min_inr: toInr(form.budgetMin.amount, form.budgetMin.unit),
    budget_max_inr: toInr(form.budgetMax.amount, form.budgetMax.unit) as number,
    goal: form.goal as InvestmentGoal,
    target_roi_pct: Number(form.targetRoi),
    expected_growth_pct: numberOrNull(growth),
    risk_appetite: form.riskAppetite as RiskAppetite,
  };
}

/** Empty -> null; a positive whole number -> it; anything else -> "invalid". */
function parseWholeNumber(text: string): number | null | "invalid" {
  const trimmed = text.trim();
  if (!trimmed) return null;
  return /^\d+$/.test(trimmed) && Number(trimmed) > 0 ? Number(trimmed) : "invalid";
}

/** Empty -> null; a number within [min, max] -> it; anything else -> "invalid". */
function parsePercent(text: string, min: number, max: number): number | null | "invalid" {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) && value >= min && value <= max ? value : "invalid";
}

function numberOrNull(value: number | null | "invalid"): number | null {
  return typeof value === "number" ? value : null;
}

/** What a target suggestion depends on, once known; risk defaults to balanced until chosen. */
export function suggestionInput(
  form: ProfileFormState, options: ProfileOptions,
): TargetSuggestionIn | null {
  if (!form.segment || form.propertyTypes.length === 0 || form.localities.length === 0 || !form.goal)
    return null;
  return {
    segment: form.segment,
    property_types: form.propertyTypes,
    city: options.city,
    localities: form.localities,
    goal: form.goal,
    risk_appetite: form.riskAppetite || "balanced",
  };
}

/** The target to show after a suggestion arrives, or null to leave the field alone: only an
 * empty field, or one still holding the previous suggestion, is filled. An investor's own value,
 * including a saved profile's, is never overwritten. */
export function applySuggestion(
  current: string, suggested: number | null | undefined, lastSuggested: string | null,
): string | null {
  if (suggested == null) return null;
  const next = String(suggested);
  if (current === next) return null;
  return current.trim() === "" || current === lastSuggested ? next : null;
}
