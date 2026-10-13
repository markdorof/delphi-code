import { useQuery } from "@tanstack/react-query";
import { cn } from "cn";
import { CheckIcon, ChevronsUpDownIcon } from "lucide-react";
import { useState } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const EVERY_PROJECT_LABEL = "All indexed projects";

export function ProjectPicker({
  id,
  projectKey,
  onChange,
}: {
  id: string;
  projectKey: string | undefined;
  onChange: (projectKey: string | undefined) => void;
}) {
  const { client } = useApiConnection();
  const [open, setOpen] = useState(false);
  const indexedProjects = useQuery({
    queryKey: ["projects", { indexed: true }],
    queryFn: async () =>
      dataOrFailure(await client.GET("/api/projects", { params: { query: { indexed: true } } })).repos,
  });

  function choose(chosen: string | undefined) {
    onChange(chosen);
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button id={id} variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between">
          <span className="truncate">{projectKey ?? EVERY_PROJECT_LABEL}</span>
          <ChevronsUpDownIcon className="opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) min-w-72 p-0" align="start">
        <Command>
          <CommandInput placeholder="Find a project…" />
          <CommandList>
            <CommandEmpty>
              {indexedProjects.isPending ? "Loading projects…" : "No indexed project matches."}
            </CommandEmpty>
            <CommandGroup>
              <CommandItem value={EVERY_PROJECT_LABEL} onSelect={() => choose(undefined)}>
                <CheckIcon className={cn(projectKey === undefined ? "opacity-100" : "opacity-0")} />
                {EVERY_PROJECT_LABEL}
              </CommandItem>
              {indexedProjects.data?.map((project) => (
                <CommandItem key={project.key} value={project.key} onSelect={() => choose(project.key)}>
                  <CheckIcon className={cn(projectKey === project.key ? "opacity-100" : "opacity-0")} />
                  <span className="truncate font-mono text-xs">{project.key}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
