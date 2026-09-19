import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement the Pointer Events / scrollIntoView APIs Radix's `Select` (and other
// Radix primitives) call when opening/navigating a dropdown — without these, clicking a
// shadcn/Radix `<Select>` in a test throws `target.hasPointerCapture is not a function` instead
// of actually opening it. Polyfilled once here (not per-test-file) since every future test that
// interacts with a `Select` — this codebase's first being Phase 5 part 4's `TransferForm` /
// `TransactionForm` / savings-distribution-rule item pickers — needs the same fix.
if (typeof Element !== "undefined") {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (!Element.prototype.setPointerCapture) {
    Element.prototype.setPointerCapture = () => {};
  }
  if (!Element.prototype.releasePointerCapture) {
    Element.prototype.releasePointerCapture = () => {};
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => {};
  }
}
