import { createContext, type ReactNode, useContext } from "react";
import type { ApiClient } from "./apiClient";

export interface ApiConnection {
  client: ApiClient;
  serverToken: string;
}

const ApiConnectionContext = createContext<ApiConnection | null>(null);

export function ApiConnectionProvider({ connection, children }: { connection: ApiConnection; children: ReactNode }) {
  return <ApiConnectionContext.Provider value={connection}>{children}</ApiConnectionContext.Provider>;
}

export function useApiConnection(): ApiConnection {
  const connection = useContext(ApiConnectionContext);
  if (connection === null) {
    throw new Error("useApiConnection needs an ApiConnectionProvider");
  }
  return connection;
}
