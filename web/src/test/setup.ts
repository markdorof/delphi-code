import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

class ResizeObserverThatNeverFires {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver ??= ResizeObserverThatNeverFires;
Element.prototype.scrollIntoView ??= () => {};

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});
