import "@testing-library/jest-dom/vitest";

// Ensure JSDOM triggers the "md" media query so Tailwind's `md:flex` is active
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Set viewport to trigger md+ breakpoints (≥768px)
Object.defineProperty(window, "innerWidth", { writable: true, value: 1280 });
Object.defineProperty(window, "innerHeight", { writable: true, value: 800 });
