/**
 * Indian money units for budget inputs. 1 lakh = 1,00,000 and 1 crore = 1,00,00,000 rupees.
 * The API always takes whole rupees; these helpers convert at the edges of the UI.
 */

export type MoneyUnit = "lakh" | "crore";

export const UNIT_INR: Record<MoneyUnit, number> = { lakh: 100_000, crore: 10_000_000 };

export const UNIT_LABEL: Record<MoneyUnit, string> = { lakh: "Lakh", crore: "Crore" };

/** An amount typed in a unit, as whole rupees. Null for empty, non-numeric or negative input. */
export function toInr(amount: string, unit: MoneyUnit): number | null {
  const trimmed = amount.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < 0) return null;
  return Math.round(value * UNIT_INR[unit]);
}

/** Whole rupees in the unit an investor would type: crore from ₹1 Cr upwards, else lakh. */
export function fromInr(inr: number): { amount: string; unit: MoneyUnit } {
  const unit: MoneyUnit = inr >= UNIT_INR.crore ? "crore" : "lakh";
  return { amount: compact(inr / UNIT_INR[unit]), unit };
}

/** Short display form: "₹80 L", "₹1.25 Cr", "₹45,000". */
export function formatInr(inr: number): string {
  if (inr >= UNIT_INR.crore) return `₹${compact(inr / UNIT_INR.crore)} Cr`;
  if (inr >= UNIT_INR.lakh) return `₹${compact(inr / UNIT_INR.lakh)} L`;
  return `₹${inr.toLocaleString("en-IN")}`;
}

/** Up to two decimals, no trailing zeros: 80, 1.25, 0.5. */
function compact(value: number): string {
  return String(Number(value.toFixed(2)));
}
