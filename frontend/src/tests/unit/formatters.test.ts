import { describe, expect, it } from "vitest";
import { formatCurrency, formatPercent } from "@/utils/formatters";

describe("finance formatters", () => {
  it("formats SAP payload amounts using currency codes", () => {
    expect(formatCurrency(1210, "EUR")).toContain("1,210");
  });
  it("formats confidence values as percentages", () => {
    expect(formatPercent(0.93)).toBe("93%");
  });
});
