import { Link, useLocation } from "@tanstack/react-router";
import { ApiFailure } from "@/api/apiFailure";
import { setupFixes } from "@/setup/modelSetupFailures";
import { MissingServerToken } from "./MissingServerToken";

export function FailureMessage({ failure }: { failure: Error }) {
  const onSetupPage = useLocation({ select: (location) => location.pathname === "/setup" });
  if (failure instanceof ApiFailure && failure.needsNewServerToken) {
    return <MissingServerToken />;
  }
  return (
    <p role="alert" className="text-destructive">
      {failure.message}
      {failure instanceof ApiFailure && setupFixes(failure.code) && !onSetupPage && (
        <>
          {" "}
          <Link to="/setup" className="font-medium text-foreground underline underline-offset-4">
            Set up the model
          </Link>
        </>
      )}
    </p>
  );
}
