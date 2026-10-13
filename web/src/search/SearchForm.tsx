import { SearchIcon } from "lucide-react";
import { type FormEvent, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ProjectPicker } from "./ProjectPicker";
import { DEFAULT_SEARCH_LIMIT, SEARCH_LIMIT_CHOICES, type SearchFilters } from "./searchFilters";

export function SearchForm({
  filters,
  onSearch,
}: {
  filters: SearchFilters;
  onSearch: (filters: SearchFilters) => void;
}) {
  const ids = useId();
  const [draft, setDraft] = useState(filters);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSearch(draft);
  }

  function changeDraft(name: keyof SearchFilters, value: string | number | undefined) {
    setDraft((current) => {
      const { [name]: _replaced, ...rest } = current;
      return value === undefined || value === "" ? rest : { ...rest, [name]: value };
    });
  }

  return (
    <search>
      <form onSubmit={submit} className="grid gap-3">
        <div className="flex gap-2">
          <Input
            aria-label="What are you looking for?"
            placeholder="Where are user passwords checked?"
            value={draft.q ?? ""}
            onChange={(event) => changeDraft("q", event.target.value)}
            autoFocus
            className="h-10"
          />
          <Button type="submit" className="h-10" disabled={!draft.q?.trim()}>
            <SearchIcon />
            Search
          </Button>
        </div>
        <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr_auto]">
          <div className="grid gap-1.5">
            <Label htmlFor={`${ids}-project`}>Project</Label>
            <ProjectPicker
              id={`${ids}-project`}
              projectKey={draft.project}
              onChange={(project) => changeDraft("project", project)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor={`${ids}-path`}>Paths</Label>
            <Input
              id={`${ids}-path`}
              placeholder="src/*, tests/*"
              value={draft.path ?? ""}
              onChange={(event) => changeDraft("path", event.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor={`${ids}-language`}>Languages</Label>
            <Input
              id={`${ids}-language`}
              placeholder="python, typescript"
              value={draft.language ?? ""}
              onChange={(event) => changeDraft("language", event.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor={`${ids}-limit`}>Results</Label>
            <Select
              value={String(draft.limit ?? DEFAULT_SEARCH_LIMIT)}
              onValueChange={(limit) => changeDraft("limit", Number(limit))}
            >
              <SelectTrigger id={`${ids}-limit`} className="w-full sm:w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SEARCH_LIMIT_CHOICES.map((limit) => (
                  <SelectItem key={limit} value={String(limit)}>
                    {limit}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </form>
    </search>
  );
}
