import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRouter, RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createApiClient } from "./api/apiClient";
import { ApiConnectionProvider } from "./api/apiContext";
import { reloadWhenTokenArrives, serverTokenFromPageAddress } from "./api/serverToken";
import { MissingServerToken } from "./components/MissingServerToken";
import { routeTree } from "./routeTree.gen";
import "./styles.css";

const queryClient = new QueryClient();
const router = createRouter({ routeTree, context: { queryClient } });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const serverToken = serverTokenFromPageAddress(window.location, window.history, window.sessionStorage);
if (serverToken === null) {
  reloadWhenTokenArrives(window);
}
const root = document.getElementById("root");
if (root === null) {
  throw new Error("index.html has no #root element");
}

createRoot(root).render(
  <StrictMode>
    {serverToken === null ? (
      <MissingServerToken />
    ) : (
      <ApiConnectionProvider connection={{ client: createApiClient(serverToken), serverToken }}>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </ApiConnectionProvider>
    )}
  </StrictMode>,
);
