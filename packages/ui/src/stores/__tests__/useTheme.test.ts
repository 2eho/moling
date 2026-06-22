import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useTheme, THEMES, isDarkTheme, detectSystemTheme, type ThemeId } from "../useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    // Reset store to defaults before each test
    useTheme.setState({ theme: "moling", autoFollow: false });
    // Clear localStorage between tests
    localStorage.clear();
  });

  describe("initial state", () => {
    it("has moling as default theme", () => {
      expect(useTheme.getState().theme).toBe("moling");
    });

    it("has autoFollow set to false by default", () => {
      expect(useTheme.getState().autoFollow).toBe(false);
    });
  });

  describe("setTheme", () => {
    it("changes theme to specified ID", () => {
      useTheme.getState().setTheme("dracula");

      expect(useTheme.getState().theme).toBe("dracula");
    });

    it("sets autoFollow to false when manually changing theme", () => {
      useTheme.setState({ autoFollow: true });

      useTheme.getState().setTheme("nord");

      expect(useTheme.getState().autoFollow).toBe(false);
    });

    it("sets data-theme attribute on document element", () => {
      useTheme.getState().setTheme("onedark");

      expect(document.documentElement.getAttribute("data-theme")).toBe("onedark");
    });
  });

  describe("cycleNext", () => {
    it("cycles to the next theme in THEMES list", () => {
      useTheme.setState({ theme: "moling" });

      useTheme.getState().cycleNext();

      // moling → nord (index 0 → 1)
      expect(useTheme.getState().theme).toBe("nord");
      expect(useTheme.getState().autoFollow).toBe(false);
    });

    it("wraps around to first theme when at end", () => {
      // Set to last theme
      useTheme.setState({ theme: "github-light" });

      useTheme.getState().cycleNext();

      // Should wrap to first theme (moling)
      expect(useTheme.getState().theme).toBe("moling");
    });
  });

  describe("resetToAuto", () => {
    it("sets autoFollow to true", () => {
      useTheme.getState().resetToAuto();

      expect(useTheme.getState().autoFollow).toBe(true);
    });

    it("sets theme based on system preference", () => {
      // Mock dark mode
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      useTheme.getState().resetToAuto();

      expect(useTheme.getState().autoFollow).toBe(true);
      expect(useTheme.getState().theme).toBe("moling"); // dark → moling
    });
  });

  describe("persistence", () => {
    it("persists theme to localStorage via zustand persist", () => {
      useTheme.getState().setTheme("dracula");

      const stored = localStorage.getItem("vibe-writing-theme");
      expect(stored).toBeTruthy();

      const parsed = JSON.parse(stored!);
      expect(parsed.state.theme).toBe("dracula");
    });
  });

  describe("isDarkTheme", () => {
    it("returns true for dark themes", () => {
      expect(isDarkTheme("moling")).toBe(true);
      expect(isDarkTheme("nord")).toBe(true);
      expect(isDarkTheme("dracula")).toBe(true);
    });

    it("returns false for light themes", () => {
      expect(isDarkTheme("solarized-light")).toBe(false);
      expect(isDarkTheme("paper")).toBe(false);
      expect(isDarkTheme("github-light")).toBe(false);
    });
  });

  describe("THEMES", () => {
    it("contains 8 themes", () => {
      expect(THEMES).toHaveLength(8);
    });

    it("all themes have id, name, icon, description", () => {
      for (const theme of THEMES) {
        expect(theme.id).toBeTruthy();
        expect(theme.name).toBeTruthy();
        expect(theme.icon).toBeTruthy();
        expect(theme.description).toBeTruthy();
      }
    });
  });

  describe("detectSystemTheme", () => {
    it("returns moling for dark mode preference", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      expect(detectSystemTheme()).toBe("moling");
    });

    it("returns solarized-light for light mode preference", () => {
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: false, // neither dark
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      expect(detectSystemTheme()).toBe("solarized-light");
    });
  });
});
