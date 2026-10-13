import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { LockIcon } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { useWriteActivity } from "@/activity/WriteActivityProvider";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import type { components } from "@/api/schema";
import { FailureMessage } from "@/components/FailureMessage";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { pickedSummary } from "@/projects/writeSummaries";
import { pickedChanges } from "./pickedChanges";

type HostingService = components["schemas"]["HostingServiceResponse"];
type Repository = components["schemas"]["RepositoryResponse"];

export function RepositoryStep({ service, owner }: { service: HostingService; owner: string }) {
  const { client } = useApiConnection();
  const repositories = useQuery({
    queryKey: ["hosting-services", service.domain, "owners", owner, "repositories"],
    queryFn: async () =>
      dataOrFailure(
        await client.GET("/api/hosting-services/{domain}/owners/{owner}/repositories", {
          params: { path: { domain: service.domain, owner } },
        }),
      ).repositories,
  });
  const trackedKeys = useQuery({
    queryKey: ["projects"],
    queryFn: async () => dataOrFailure(await client.GET("/api/projects")),
    select: (listing) => new Set(listing.repos.filter((project) => project.tracked).map((project) => project.key)),
  });

  if (repositories.isPending || trackedKeys.isPending) {
    return <p className="text-muted-foreground">Listing {owner}'s repositories…</p>;
  }
  if (repositories.isError || trackedKeys.isError) {
    return <FailureMessage failure={(repositories.error ?? trackedKeys.error) as Error} />;
  }
  if (repositories.data.length === 0) {
    return <p className="text-muted-foreground">These credentials see no repositories in {owner}.</p>;
  }
  return (
    <RepositoryChoice
      key={`${service.domain}/${owner}`}
      owner={owner}
      repositories={repositories.data}
      trackedKeys={trackedKeys.data}
    />
  );
}

function RepositoryChoice({
  owner,
  repositories,
  trackedKeys,
}: {
  owner: string;
  repositories: Repository[];
  trackedKeys: Set<string>;
}) {
  const ids = useId();
  const navigate = useNavigate();
  const { startWrite, writeRunning } = useWriteActivity();
  const [chosenKeys, setChosenKeys] = useState(
    () => new Set(repositories.filter((repository) => trackedKeys.has(repository.key)).map(({ key }) => key)),
  );
  const [filter, setFilter] = useState("");
  const [ref, setRef] = useState("");
  const [indexNow, setIndexNow] = useState(true);
  const changes = pickedChanges(
    repositories.map(({ key }) => key),
    chosenKeys,
    trackedKeys,
  );
  const shown = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return repositories.filter((repository) =>
      `${repository.slug} ${repository.description}`.toLowerCase().includes(needle),
    );
  }, [repositories, filter]);

  function choose(key: string, chosen: boolean) {
    setChosenKeys((current) => {
      const next = new Set(current);
      if (chosen) {
        next.add(key);
      } else {
        next.delete(key);
      }
      return next;
    });
  }

  async function apply() {
    const report = await startWrite({
      title: `Updating tracked repositories in ${owner}`,
      path: "/api/projects/picked",
      body: { ...changes, ...(ref.trim() ? { ref: ref.trim() } : {}), no_sync: !indexNow },
      summary: pickedSummary,
    });
    if (report) {
      await navigate({ to: "/projects" });
    }
  }

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 className="font-medium">Repositories to index in {owner}</h2>
        <Input
          aria-label="Filter repositories"
          placeholder="Filter…"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className="sm:w-64"
        />
      </div>
      <ul className="grid max-h-[50vh] overflow-y-auto rounded-lg border">
        {shown.map((repository) => {
          const checkboxId = `${ids}-${repository.key}`;
          return (
            <li key={repository.key} className="flex items-start gap-3 border-b px-3 py-2 last:border-b-0">
              <Checkbox
                id={checkboxId}
                className="mt-0.5"
                checked={chosenKeys.has(repository.key)}
                onCheckedChange={(checked) => choose(repository.key, checked === true)}
              />
              <Label htmlFor={checkboxId} className="grid min-w-0 flex-1 gap-0.5 font-normal">
                <span className="flex items-center gap-1.5 font-mono text-sm">
                  {repository.slug}
                  {repository.private && <LockIcon className="size-3 text-muted-foreground" aria-label="Private" />}
                  {trackedKeys.has(repository.key) && (
                    <span className="font-sans text-muted-foreground text-xs">tracked</span>
                  )}
                </span>
                {repository.description && (
                  <span className="truncate text-muted-foreground text-xs">{repository.description}</span>
                )}
              </Label>
            </li>
          );
        })}
      </ul>
      <div className="grid gap-3 rounded-lg border p-4">
        <ChangeList title="Track" keys={changes.added} />
        <ChangeList title="Stop tracking and delete the index of" keys={changes.removed} />
        {changes.added.length + changes.removed.length === 0 && (
          <p className="text-muted-foreground text-sm">Check or uncheck repositories to change what is tracked.</p>
        )}
        {changes.added.length > 0 && (
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Label htmlFor={`${ids}-ref`}>Branch or tag</Label>
              <Input
                id={`${ids}-ref`}
                placeholder="Default branch"
                value={ref}
                onChange={(event) => setRef(event.target.value)}
                className="w-40"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id={`${ids}-index-now`}
                checked={indexNow}
                onCheckedChange={(checked) => setIndexNow(checked === true)}
              />
              <Label htmlFor={`${ids}-index-now`}>Index them now</Label>
            </div>
          </div>
        )}
        <div>
          <Button
            onClick={() => void apply()}
            disabled={writeRunning || changes.added.length + changes.removed.length === 0}
          >
            Apply changes
          </Button>
        </div>
      </div>
    </section>
  );
}

function ChangeList({ title, keys }: { title: string; keys: string[] }) {
  if (keys.length === 0) {
    return null;
  }
  return (
    <div className="grid gap-1 text-sm">
      <p className="font-medium">{title}</p>
      <ul className="grid gap-0.5 font-mono text-xs">
        {keys.map((key) => (
          <li key={key}>{key}</li>
        ))}
      </ul>
    </div>
  );
}
