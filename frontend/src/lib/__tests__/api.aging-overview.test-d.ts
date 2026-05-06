/**
 * Finding E5: AgingOverview.trend must carry both canonical fields
 * (days_to_pay + avg_days_to_pay) and both deprecated aliases (dpo + avg_dpo).
 *
 * Accuracy convention §2 (deprecated alias lifetime when renaming response
 * fields): when renaming a response field, keep the old key as a deprecated
 * alias for one release. The trend element previously carried days_to_pay/dpo
 * but was missing avg_days_to_pay and the matching avg_dpo alias.
 *
 * This is a type-only test (.test-d.ts). It runs via `vitest --typecheck`
 * and fails at compile time when the four required fields are absent.
 */
import { describe, it, expectTypeOf } from "vitest";
import type { AgingOverview } from "../api";

type TrendElement = AgingOverview["trend"][number];

describe("AgingOverview.trend - Finding E5 alias parity", () => {
  it("trend element exposes month and both canonical day-to-pay fields", () => {
    // #then
    expectTypeOf<TrendElement>().toHaveProperty("month");
    expectTypeOf<TrendElement>().toHaveProperty("days_to_pay");
    expectTypeOf<TrendElement>().toHaveProperty("avg_days_to_pay");
  });

  it("trend element exposes both deprecated aliases (dpo, avg_dpo)", () => {
    // #then
    expectTypeOf<TrendElement>().toHaveProperty("dpo");
    expectTypeOf<TrendElement>().toHaveProperty("avg_dpo");
  });

  it("avg_days_to_pay is typed as number | undefined on trend items", () => {
    // #then
    expectTypeOf<TrendElement>()
      .toHaveProperty("avg_days_to_pay")
      .toEqualTypeOf<number | undefined>();
    expectTypeOf<TrendElement>()
      .toHaveProperty("avg_dpo")
      .toEqualTypeOf<number | undefined>();
  });
});
