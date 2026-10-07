import { describe, it, expect } from "vitest";

/**
 * FarmApp Frontend — Example Unit Test
 *
 * Replace with actual component tests as the project grows.
 * Tests are run with Vitest (configured in vite.config.ts).
 */

describe("Example Test Suite", () => {
  it("should pass a basic sanity check", () => {
    expect(1 + 1).toBe(2);
  });

  it("should handle string operations", () => {
    const greeting = "Hello, FarmApp!";
    expect(greeting).toContain("FarmApp");
    expect(greeting.length).toBeGreaterThan(0);
  });
});
