import createClient, { type Middleware } from "openapi-fetch";
import { ApiFailure } from "./apiFailure";
import type { paths } from "./schema";

export type ApiClient = ReturnType<typeof createApiClient>;

export function createApiClient(serverToken: string, baseUrl = window.location.origin) {
  const client = createClient<paths>({ baseUrl, fetch: (request) => globalThis.fetch(request) });
  client.use(bearerToken(serverToken));
  return client;
}

export function bearerToken(serverToken: string): Middleware {
  return {
    onRequest({ request }) {
      request.headers.set("Authorization", `Bearer ${serverToken}`);
      return request;
    },
  };
}

export function dataOrFailure<Data>(answer: { data?: Data; error?: unknown; response: Response }): Data {
  if (answer.error !== undefined || answer.data === undefined) {
    throw ApiFailure.fromBody(answer.response.status, answer.error);
  }
  return answer.data;
}
