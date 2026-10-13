import { ApiFailure } from "@/api/apiFailure";
import { MissingServerToken } from "./MissingServerToken";

export function FailureMessage({ failure }: { failure: Error }) {
  if (failure instanceof ApiFailure && failure.needsNewServerToken) {
    return <MissingServerToken />;
  }
  return (
    <p role="alert" className="text-destructive">
      {failure.message}
    </p>
  );
}
