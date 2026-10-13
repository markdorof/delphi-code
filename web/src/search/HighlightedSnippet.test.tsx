import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HighlightedSnippet } from "./HighlightedSnippet";

function renderSnippet(text: string, language: string) {
  const { container } = render(
    <QueryClientProvider client={new QueryClient()}>
      <HighlightedSnippet text={text} language={language} firstLineNumber={17} />
    </QueryClientProvider>,
  );
  return container;
}

describe("HighlightedSnippet", () => {
  it("numbers lines from the hit's first line", () => {
    renderSnippet("first\nsecond\n", "text");

    expect(screen.getByText("17")).toBeTruthy();
    expect(screen.getByText("18")).toBeTruthy();
    expect(screen.queryByText("19")).toBeNull();
  });

  it("colours tokens for both themes once the language loads", async () => {
    const container = renderSnippet("def check_password(user):\n    return False\n", "python");

    await waitFor(() => expect(container.querySelector('[style*="--shiki-light"]')).not.toBeNull());
    expect(container.querySelector('[style*="--shiki-dark"]')).not.toBeNull();
    expect(container.textContent).toContain("def check_password(user):");
  });
});
