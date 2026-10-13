import { useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { useApiConnection } from "@/api/apiContext";
import { ApiFailure } from "@/api/apiFailure";
import {
  runStreamedWrite,
  type StreamedWriteBody,
  type StreamedWritePath,
  type StreamedWriteResult,
} from "@/api/streamedWrite";
import {
  activityAfterProgress,
  failedActivity,
  startedActivity,
  succeededActivity,
  type WriteActivity,
} from "./writeActivity";

const QUERIES_A_WRITE_CHANGES = [["projects"], ["search"]];

export interface WriteRequest<Path extends StreamedWritePath> {
  title: string;
  path: Path;
  body: StreamedWriteBody<Path>;
  summary: (result: StreamedWriteResult<Path>) => string;
}

interface WriteActivityControls {
  activity: WriteActivity | null;
  writeRunning: boolean;
  startWrite: <Path extends StreamedWritePath>(
    request: WriteRequest<Path>,
  ) => Promise<StreamedWriteResult<Path> | undefined>;
  dismissActivity: () => void;
}

const WriteActivityContext = createContext<WriteActivityControls | null>(null);

export function WriteActivityProvider({ children }: { children: ReactNode }) {
  const { serverToken } = useApiConnection();
  const queryClient = useQueryClient();
  const [activity, setActivity] = useState<WriteActivity | null>(null);

  const startWrite = useCallback(
    async <Path extends StreamedWritePath>(request: WriteRequest<Path>) => {
      setActivity(startedActivity(request.title));
      try {
        const result = await runStreamedWrite({
          path: request.path,
          body: request.body,
          serverToken,
          onProgress: (event) => setActivity((current) => current && activityAfterProgress(current, event)),
        });
        setActivity((current) => current && succeededActivity(current, request.summary(result)));
        return result;
      } catch (error) {
        const failure =
          error instanceof ApiFailure ? error : new ApiFailure("network_error", String(error), 0, undefined);
        setActivity((current) => current && failedActivity(current, failure));
        return undefined;
      } finally {
        await Promise.all(QUERIES_A_WRITE_CHANGES.map((queryKey) => queryClient.invalidateQueries({ queryKey })));
      }
    },
    [serverToken, queryClient],
  );

  const controls = useMemo(
    () => ({
      activity,
      writeRunning: activity?.state === "running",
      startWrite,
      dismissActivity: () => setActivity(null),
    }),
    [activity, startWrite],
  );
  return <WriteActivityContext.Provider value={controls}>{children}</WriteActivityContext.Provider>;
}

export function useWriteActivity(): WriteActivityControls {
  const controls = useContext(WriteActivityContext);
  if (controls === null) {
    throw new Error("useWriteActivity needs a WriteActivityProvider");
  }
  return controls;
}
