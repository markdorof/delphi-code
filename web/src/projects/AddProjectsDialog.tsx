import { type FormEvent, useId, useState } from "react";
import { useWriteActivity } from "@/activity/WriteActivityProvider";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { commaSeparatedValues } from "@/forms/commaSeparatedValues";
import { addSummary } from "./writeSummaries";

export function AddProjectsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const ids = useId();
  const { startWrite } = useWriteActivity();
  const [sources, setSources] = useState("");
  const [ref, setRef] = useState("");
  const [paths, setPaths] = useState("");
  const [languages, setLanguages] = useState("");
  const [ignores, setIgnores] = useState("");
  const [indexNow, setIndexNow] = useState(true);
  const sourceList = sources
    .split("\n")
    .map((source) => source.trim())
    .filter(Boolean);

  function submit(event: FormEvent) {
    event.preventDefault();
    onOpenChange(false);
    void startWrite({
      title: `Adding ${sourceList.length === 1 ? sourceList[0] : `${sourceList.length} projects`}`,
      path: "/api/projects",
      body: {
        sources: sourceList,
        ...(ref.trim() ? { ref: ref.trim() } : {}),
        path: commaSeparatedValues(paths),
        language: commaSeparatedValues(languages),
        ignore: commaSeparatedValues(ignores),
        no_sync: !indexNow,
      },
      summary: addSummary,
    });
    setSources("");
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Add projects</DialogTitle>
            <DialogDescription>
              Track local folders or remote repositories. Sync all keeps every tracked project up to date.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-1.5">
            <Label htmlFor={`${ids}-sources`}>Folders or repositories, one per line</Label>
            <Textarea
              id={`${ids}-sources`}
              required
              rows={3}
              placeholder={"/Users/you/src/api\ngithub.com/acme/web"}
              value={sources}
              onChange={(event) => setSources(event.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField
              id={`${ids}-ref`}
              label="Branch or tag"
              placeholder="Default branch"
              value={ref}
              onChange={setRef}
            />
            <TextField id={`${ids}-paths`} label="Paths" placeholder="src/*, lib/*" value={paths} onChange={setPaths} />
            <TextField
              id={`${ids}-languages`}
              label="Languages"
              placeholder="python, go"
              value={languages}
              onChange={setLanguages}
            />
            <TextField
              id={`${ids}-ignores`}
              label="Also ignore"
              placeholder="*.generated.ts"
              value={ignores}
              onChange={setIgnores}
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
          <DialogFooter>
            <Button type="submit" disabled={sourceList.length === 0}>
              Add
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function TextField({
  id,
  label,
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} placeholder={placeholder} value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
