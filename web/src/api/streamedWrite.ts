import { ApiFailure } from "./apiFailure";
import type { ProgressEvent } from "./progressEvents";
import type { paths } from "./schema";

const NDJSON = "application/x-ndjson";

type StreamedResultOf<Operation> = Operation extends {
  responses: { 200: { content: { [NDJSON]: infer Result } } };
}
  ? Result
  : never;

export type StreamedWritePath = {
  [Path in keyof paths]: StreamedResultOf<paths[Path]["post"]> extends never ? never : Path;
}[keyof paths];

export type StreamedWriteResult<Path extends StreamedWritePath> = StreamedResultOf<paths[Path]["post"]>;

export type StreamedWriteBody<Path extends StreamedWritePath> = paths[Path]["post"] extends {
  requestBody?: { content: { "application/json": infer Body } };
}
  ? Body
  : undefined;

type StreamedLine<Result> =
  | ProgressEvent
  | { done: Result }
  | { failed: { code: string; message: string }; data?: unknown };

export interface StreamedWrite<Path extends StreamedWritePath> {
  path: Path;
  body: StreamedWriteBody<Path>;
  serverToken: string;
  onProgress: (event: ProgressEvent) => void;
}

export async function runStreamedWrite<Path extends StreamedWritePath>(
  write: StreamedWrite<Path>,
): Promise<StreamedWriteResult<Path>> {
  const response = await fetch(write.path, {
    method: "POST",
    headers: { Authorization: `Bearer ${write.serverToken}`, "Content-Type": "application/json" },
    body: JSON.stringify(write.body ?? {}),
  });
  if (!response.ok || response.body === null) {
    throw ApiFailure.fromBody(response.status, await response.json().catch(() => undefined));
  }
  for await (const line of jsonLines<StreamedLine<StreamedWriteResult<Path>>>(response.body)) {
    if ("event" in line) {
      write.onProgress(line);
    } else if ("done" in line) {
      return line.done;
    } else {
      throw new ApiFailure(line.failed.code, line.failed.message, response.status, line.data);
    }
  }
  throw new ApiFailure("stream_ended", "The server stopped answering before the write finished", response.status);
}

export async function* jsonLines<Line>(body: ReadableStream<Uint8Array>): AsyncGenerator<Line> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let unfinishedLine = "";
  for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) {
    const lines = (unfinishedLine + decoder.decode(chunk.value, { stream: true })).split("\n");
    unfinishedLine = lines.pop() ?? "";
    yield* parsedLines<Line>(lines);
  }
  yield* parsedLines<Line>([unfinishedLine + decoder.decode()]);
}

function* parsedLines<Line>(lines: string[]): Generator<Line> {
  for (const line of lines) {
    if (line.trim()) {
      yield JSON.parse(line) as Line;
    }
  }
}
