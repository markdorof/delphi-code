import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, createRouter, RouterProvider } from "@tanstack/react-router";
import { render } from "@testing-library/react";
import { createApiClient } from "@/api/apiClient";
import { ApiConnectionProvider } from "@/api/apiContext";
import { routeTree } from "@/routeTree.gen";
import { SERVER_TOKEN } from "./apiServer";

export const TEST_API_ORIGIN = "http://127.0.0.1:8123";

export function renderAppAt(url: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [url] }),
  });
  const connection = { client: createApiClient(SERVER_TOKEN, TEST_API_ORIGIN), serverToken: SERVER_TOKEN };
  render(
    <ApiConnectionProvider connection={connection}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ApiConnectionProvider>,
  );
  return router;
}
