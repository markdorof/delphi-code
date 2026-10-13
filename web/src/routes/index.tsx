import { createFileRoute } from "@tanstack/react-router";
import { SearchForm } from "@/search/SearchForm";
import { SearchResults } from "@/search/SearchResults";
import { searchFiltersFromUrl } from "@/search/searchFilters";

export const Route = createFileRoute("/")({
  validateSearch: searchFiltersFromUrl,
  component: SearchPage,
});

function SearchPage() {
  const filters = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6">
      <SearchForm
        key={JSON.stringify(filters)}
        filters={filters}
        onSearch={(chosen) => navigate({ search: searchFiltersFromUrl({ ...chosen }) })}
      />
      <SearchResults filters={filters} />
    </div>
  );
}
