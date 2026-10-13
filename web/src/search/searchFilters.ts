export const SEARCH_LIMIT_CHOICES = [5, 10, 20, 50] as const;
export const DEFAULT_SEARCH_LIMIT = 10;

export interface SearchFilters {
  q?: string;
  project?: string;
  path?: string;
  language?: string;
  limit?: number;
}

export function searchFiltersFromUrl(search: Record<string, unknown>): SearchFilters {
  const filters: SearchFilters = {};
  for (const name of ["q", "project", "path", "language"] as const) {
    const value = search[name];
    if (typeof value === "string" && value.trim()) {
      filters[name] = value.trim();
    }
  }
  const limit = Number(search.limit);
  if ((SEARCH_LIMIT_CHOICES as readonly number[]).includes(limit) && limit !== DEFAULT_SEARCH_LIMIT) {
    filters.limit = limit;
  }
  return filters;
}
