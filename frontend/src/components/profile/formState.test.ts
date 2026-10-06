import { describe, expect, it } from "vitest";

import type { InvestorProfile, ProfileOptions } from "../../api/types";
import {
  applySuggestion,
  emptyForm,
  firstStepWithError,
  formFromProfile,
  suggestionInput,
  toPayload,
  validateAll,
  validateStep,
  type ProfileFormState,
} from "./formState";

// Mirrors the shape of GET /api/meta/profile-options; only what the logic reads matters.
const OPTIONS: ProfileOptions = {
  city: "Bengaluru",
  segments: [],
  localities: [],
  locality_source: "test",
  max_localities: 5,
  business_type_suggestions: [],
  goals: [
    { value: "rental_income", label: "Rental income", measure: "rental_yield", measure_label: "" },
    { value: "appreciation", label: "Appreciation", measure: "price_growth", measure_label: "" },
    { value: "balanced", label: "Balanced", measure: "total_return", measure_label: "" },
  ],
  risk_levels: [],
};

const VALID: ProfileFormState = {
  ...emptyForm(),
  name: " East Bengaluru yield ",
  segment: "residential",
  propertyTypes: ["apartment"],
  localities: ["whitefield", "kr-puram"],
  budgetMin: { amount: "50", unit: "lakh" },
  budgetMax: { amount: "1.2", unit: "crore" },
  goal: "rental_income",
  targetRoi: "4",
  riskAppetite: "balanced",
};

describe("validateStep", () => {
  it("passes a complete form on every step", () => {
    expect(validateAll(VALID, OPTIONS)).toEqual({});
  });

  it("flags missing basics on step 1", () => {
    const errors = validateStep(0, emptyForm(), OPTIONS);
    expect(Object.keys(errors).sort()).toEqual(["name", "property_types", "segment"]);
  });

  it("requires a business type for commercial only", () => {
    const commercial = { ...VALID, segment: "commercial" as const, propertyTypes: ["office" as const] };
    expect(validateStep(0, commercial, OPTIONS).business_type).toBeDefined();
    expect(validateStep(0, { ...commercial, businessType: "Cafe" }, OPTIONS)).toEqual({});
  });

  it("checks size and budget ranges", () => {
    expect(validateStep(0, { ...VALID, sizeMin: "1500", sizeMax: "900" }, OPTIONS).size_max_sqft)
      .toBe("Maximum size must be at least the minimum size.");
    expect(validateStep(0, { ...VALID, sizeMin: "12.5" }, OPTIONS).size_min_sqft).toBeDefined();
    const inverted = { ...VALID, budgetMin: { amount: "2", unit: "crore" as const } };
    expect(validateStep(2, inverted, OPTIONS).budget_max_inr)
      .toBe("Maximum budget must be at least the minimum budget.");
  });

  it("limits localities to 1..max", () => {
    expect(validateStep(1, { ...VALID, localities: [] }, OPTIONS).localities).toBeDefined();
    const six = ["a", "b", "c", "d", "e", "f"];
    expect(validateStep(1, { ...VALID, localities: six }, OPTIONS).localities)
      .toBe("Choose at most 5 localities.");
  });

  it("bounds the target ROI and growth override", () => {
    expect(validateStep(2, { ...VALID, targetRoi: "" }, OPTIONS).target_roi_pct).toBeDefined();
    expect(validateStep(2, { ...VALID, targetRoi: "120" }, OPTIONS).target_roi_pct).toBeDefined();
    const growth = { ...VALID, goal: "appreciation" as const, expectedGrowth: "-150" };
    expect(validateStep(2, growth, OPTIONS).expected_growth_pct).toBeDefined();
    expect(validateStep(2, { ...growth, expectedGrowth: "-5" }, OPTIONS)).toEqual({});
  });
});

describe("firstStepWithError", () => {
  it("finds the step that owns the field", () => {
    expect(firstStepWithError({ localities: "x" })).toBe(1);
    expect(firstStepWithError({ business_type: "x", goal: "y" })).toBe(0);
    expect(firstStepWithError({ city: "x" })).toBe(1);
    expect(firstStepWithError({})).toBe(-1);
  });
});

describe("toPayload", () => {
  it("builds the API body in rupees with trimmed text", () => {
    expect(toPayload(VALID, OPTIONS)).toEqual({
      name: "East Bengaluru yield",
      segment: "residential",
      property_types: ["apartment"],
      size_min_sqft: null,
      size_max_sqft: null,
      business_type: null,
      city: "Bengaluru",
      localities: ["whitefield", "kr-puram"],
      must_haves: [],
      budget_min_inr: 5_000_000,
      budget_max_inr: 12_000_000,
      goal: "rental_income",
      target_roi_pct: 4,
      expected_growth_pct: null,
      risk_appetite: "balanced",
    });
  });

  it("sends the growth override only for goals that use growth", () => {
    expect(toPayload({ ...VALID, expectedGrowth: "6" }, OPTIONS).expected_growth_pct).toBeNull();
    expect(toPayload({ ...VALID, goal: "balanced", expectedGrowth: "6" }, OPTIONS).expected_growth_pct)
      .toBe(6);
  });

  it("round-trips through formFromProfile", () => {
    const payload = toPayload({ ...VALID, goal: "balanced", expectedGrowth: "-2.5" }, OPTIONS);
    const profile: InvestorProfile = {
      ...payload,
      id: "p1",
      created_at: "2026-10-03T00:00:00Z",
      updated_at: "2026-10-03T00:00:00Z",
      roi_measure: "total_return",
    };
    expect(toPayload(formFromProfile(profile), OPTIONS)).toEqual(payload);
  });
});

describe("target suggestion", () => {
  it("fills an empty field or one still holding the last suggestion, never the investor's value", () => {
    expect(applySuggestion("", 3, null)).toBe("3");
    expect(applySuggestion("3", 3.5, "3")).toBe("3.5"); // risk changed, untouched suggestion
    expect(applySuggestion("4", 3.5, "3")).toBeNull(); // the investor typed 4
    expect(applySuggestion("4", 3, null)).toBeNull(); // editing a saved profile
    expect(applySuggestion("3", 3, "3")).toBeNull(); // nothing to change
    expect(applySuggestion("", null, null)).toBeNull(); // no data
  });

  it("asks only once the profile says what and where, with balanced risk by default", () => {
    const form = { ...emptyForm(), segment: "residential", propertyTypes: ["apartment"],
      localities: ["whitefield"], goal: "rental_income" } as ProfileFormState;
    const options = { city: "Bengaluru" } as ProfileOptions;
    expect(suggestionInput(form, options)).toEqual({ segment: "residential", property_types: ["apartment"],
      city: "Bengaluru", localities: ["whitefield"], goal: "rental_income", risk_appetite: "balanced" });
    expect(suggestionInput({ ...form, goal: "" }, options)).toBeNull();
  });
});
