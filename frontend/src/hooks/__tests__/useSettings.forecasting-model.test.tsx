/**
 * Finding #16: ForecastingModel value space must match backend choices
 * (simple_average / linear / advanced). The old 'simple' / 'standard'
 * values produced 400 on every save -- feature non-functional.
 *
 * Backend ChoiceField source-of-truth lives at
 * backend/apps/authentication/serializers.py:84-87.
 */
import { describe, it, expect } from "vitest";

import {
  DEFAULT_SETTINGS,
  VALID_FORECASTING_MODELS,
  isValidForecastingModel,
} from "../useSettings";

describe("ForecastingModel -- Finding #16 value reconcile", () => {
  it("exposes exactly the three backend choices", () => {
    // #given backend serializer choices: simple_average, linear, advanced
    // #then VALID_FORECASTING_MODELS must mirror them with no extras
    expect([...VALID_FORECASTING_MODELS].sort()).toEqual(
      ["advanced", "linear", "simple_average"].sort(),
    );
  });

  it("validator accepts simple_average / linear / advanced", () => {
    // #given the three legal backend values
    // #when validating each
    // #then guard returns true for all
    expect(isValidForecastingModel("simple_average")).toBe(true);
    expect(isValidForecastingModel("linear")).toBe(true);
    expect(isValidForecastingModel("advanced")).toBe(true);
  });

  it("validator rejects legacy 'simple' / 'standard' (the buggy values)", () => {
    // #given the pre-fix values that caused 400s on every save
    // #when validating each
    // #then guard returns false (the frontend will swap them for the default)
    expect(isValidForecastingModel("simple")).toBe(false);
    expect(isValidForecastingModel("standard")).toBe(false);
  });

  it("validator rejects unrelated strings and non-strings", () => {
    // #given garbage inputs
    // #then guard returns false
    expect(isValidForecastingModel("")).toBe(false);
    expect(isValidForecastingModel("Advanced")).toBe(false);
    expect(isValidForecastingModel(undefined)).toBe(false);
    expect(isValidForecastingModel(null)).toBe(false);
    expect(isValidForecastingModel(42)).toBe(false);
  });

  it("default forecasting model is one of the three valid choices", () => {
    // #given DEFAULT_SETTINGS exported from the hook module
    // #then the seeded forecastingModel is in the legal set
    expect(["simple_average", "linear", "advanced"]).toContain(
      DEFAULT_SETTINGS.forecastingModel,
    );
  });
});
