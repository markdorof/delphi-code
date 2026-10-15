import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import type { components } from "@/api/schema";
import { FailureMessage } from "@/components/FailureMessage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type AccountConnection = components["schemas"]["AccountConnectionResponse"];

export function ConnectionsSection() {
  const { client } = useApiConnection();
  const connections = useQuery({
    queryKey: ["account-connections"],
    queryFn: async () => dataOrFailure(await client.GET("/api/account-connections")).connections,
  });

  return (
    <section aria-labelledby="connections-heading" className="grid gap-3 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 id="connections-heading" className="font-medium">
          Bitbucket and GitHub accounts
        </h2>
        <Button variant="outline" size="sm" onClick={() => connections.refetch()} disabled={connections.isFetching}>
          {connections.isFetching ? "Checking…" : "Check again"}
        </Button>
      </div>
      {connections.isPending && <p className="text-muted-foreground text-sm">Checking your accounts…</p>}
      {connections.isError && <FailureMessage failure={connections.error} />}
      {connections.data && (
        <ul className="grid gap-3 text-sm">
          {connections.data.map((connection) => (
            <ConnectionRow key={connection.domain} connection={connection} />
          ))}
        </ul>
      )}
    </section>
  );
}

function ConnectionRow({ connection }: { connection: AccountConnection }) {
  return (
    <li aria-label={connection.name} className="grid gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{connection.name}</span>
        <ConnectionBadge connection={connection} />
        {connection.state === "connected" && (
          <Link
            to="/projects/from-account"
            search={{ service: connection.domain }}
            className="ml-auto underline underline-offset-4"
          >
            Pick repositories
          </Link>
        )}
      </div>
      <p className="break-words text-muted-foreground">{connectionDetail(connection)}</p>
    </li>
  );
}

function ConnectionBadge({ connection }: { connection: AccountConnection }) {
  switch (connection.state) {
    case "connected":
      return (
        <Badge variant="secondary">{connection.account ? `Connected as ${connection.account}` : "Connected"}</Badge>
      );
    case "failed":
      return <Badge variant="destructive">Not working</Badge>;
    case "not_connected":
      return <Badge variant="outline">Not connected</Badge>;
  }
}

function connectionDetail(connection: AccountConnection): string {
  switch (connection.state) {
    case "connected":
      return `Using the ${connection.credentials_source}.`;
    case "failed":
      return connection.problem ?? "";
    case "not_connected":
      return `To connect, ${connection.how_to_connect}.`;
  }
}
