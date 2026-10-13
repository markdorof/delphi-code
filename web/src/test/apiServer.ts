import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";

export const SERVER_TOKEN = "test-server-token";
export const apiServer = setupServer();

beforeAll(() => apiServer.listen({ onUnhandledRequest: "error" }));
afterEach(() => apiServer.resetHandlers());
afterAll(() => apiServer.close());

export function ndjson(lines: unknown[], chunkSize = 7): Response {
  const text = lines.map((line) => `${JSON.stringify(line)}\n`).join("");
  const encoded = new TextEncoder().encode(text);
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let start = 0; start < encoded.length; start += chunkSize) {
        controller.enqueue(encoded.slice(start, start + chunkSize));
      }
      controller.close();
    },
  });
  return new Response(body, { headers: { "Content-Type": "application/x-ndjson" } });
}
