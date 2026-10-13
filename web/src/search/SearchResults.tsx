import { useQuery } from "@tanstack/react-query";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { FailureMessage } from "@/components/FailureMessage";
import { SearchHitCard } from "./SearchHitCard";
import { commaSeparatedValues, DEFAULT_SEARCH_LIMIT, type SearchFilters } from "./searchFilters";

export function SearchResults({ filters }: { filters: SearchFilters }) {
  const { client } = useApiConnection();
  const query = filters.q;
  const search = useQuery({
    queryKey: ["search", filters],
    enabled: query !== undefined,
    queryFn: async () =>
      dataOrFailure(
        await client.GET("/api/search", {
          params: {
            query: {
              query: query ?? "",
              ...(filters.project ? { project: filters.project } : {}),
              path: commaSeparatedValues(filters.path),
              language: commaSeparatedValues(filters.language),
              limit: filters.limit ?? DEFAULT_SEARCH_LIMIT,
            },
          },
        }),
      ),
  });

  if (query === undefined) {
    return (
      <p className="text-muted-foreground">
        Describe the code you want in plain words. Delphi Code finds it by meaning, not by exact names.
      </p>
    );
  }
  if (search.isPending) {
    return <p className="text-muted-foreground">Searching…</p>;
  }
  if (search.isError) {
    return <FailureMessage failure={search.error} />;
  }
  const { results } = search.data;
  const searched = "key" in search.data ? search.data.key : `${search.data.projects.length} indexed projects`;
  if (results.length === 0) {
    return (
      <p className="text-muted-foreground">
        Nothing in {searched} matches “{query}”.
      </p>
    );
  }
  return (
    <section className="grid grid-cols-[minmax(0,1fr)] gap-3" aria-label="Search results">
      <p className="text-muted-foreground text-sm">
        {results.length} {results.length === 1 ? "match" : "matches"} in {searched}
      </p>
      {results.map((hit) => (
        <SearchHitCard
          key={`${hit.key ?? ""}:${hit.path}:${hit.start_line}`}
          hit={hit}
          projectKey={"key" in search.data ? search.data.key : ""}
        />
      ))}
    </section>
  );
}
