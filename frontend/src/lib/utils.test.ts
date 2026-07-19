import { describe, expect, it } from "vitest";

import { cn, formatDuration } from "./utils";

describe("utils", () => {
  it("formats short duration", () => {
    expect(formatDuration(45)).toBe("45 min");
  });

  it("formats long duration", () => {
    expect(formatDuration(120)).toBe("2 h");
    expect(formatDuration(95)).toBe("1 h 35");
  });

  it("merges classes", () => {
    expect(cn("text-red-500", "text-blue-500")).toContain("text-blue-500");
  });
});
