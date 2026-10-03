import { describe, expect, it } from "vitest";

import { formatInr, fromInr, toInr } from "./money";

describe("toInr", () => {
  it("converts lakh and crore to whole rupees", () => {
    expect(toInr("80", "lakh")).toBe(8_000_000);
    expect(toInr("1.25", "crore")).toBe(12_500_000);
    expect(toInr("0.85", "crore")).toBe(8_500_000); // 0.85 * 1e7 is 8500000.000000001 in floats
    expect(toInr(" 45.5 ", "lakh")).toBe(4_550_000);
  });

  it("returns null for empty, non-numeric or negative input", () => {
    expect(toInr("", "lakh")).toBeNull();
    expect(toInr("   ", "crore")).toBeNull();
    expect(toInr("abc", "lakh")).toBeNull();
    expect(toInr("-1", "lakh")).toBeNull();
  });
});

describe("fromInr", () => {
  it("uses crore from 1 Cr upwards, lakh below", () => {
    expect(fromInr(8_000_000)).toEqual({ amount: "80", unit: "lakh" });
    expect(fromInr(10_000_000)).toEqual({ amount: "1", unit: "crore" });
    expect(fromInr(12_500_000)).toEqual({ amount: "1.25", unit: "crore" });
  });

  it("round-trips through toInr", () => {
    for (const inr of [500_000, 8_000_000, 9_950_000, 12_500_000, 250_000_000]) {
      const { amount, unit } = fromInr(inr);
      expect(toInr(amount, unit)).toBe(inr);
    }
  });
});

describe("formatInr", () => {
  it("formats in Cr, L or plain rupees", () => {
    expect(formatInr(12_500_000)).toBe("₹1.25 Cr");
    expect(formatInr(8_000_000)).toBe("₹80 L");
    expect(formatInr(45_000)).toBe("₹45,000");
  });
});
