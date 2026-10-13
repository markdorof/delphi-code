import { type FormEvent, useId, useState } from "react";
import { useWriteActivity } from "@/activity/WriteActivityProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setupSummary } from "./setupSummary";

export function ModelSetupSection() {
  const importId = useId();
  const { startWrite, writeRunning } = useWriteActivity();
  const [importFrom, setImportFrom] = useState("");

  function setUp(from: string | undefined) {
    void startWrite({
      title: from ? `Importing the model from ${from}` : "Setting up the model",
      path: "/api/setup",
      body: from ? { from } : {},
      summary: setupSummary,
    });
  }

  function importModel(event: FormEvent) {
    event.preventDefault();
    setUp(importFrom.trim());
  }

  return (
    <section className="grid gap-3 rounded-lg border p-4">
      <h2 className="font-medium">Embedding model</h2>
      <p className="text-muted-foreground text-sm">
        Downloads the pinned model once and checks it against bundled hashes. An installed model that passes is reused.
      </p>
      <div>
        <Button onClick={() => setUp(undefined)} disabled={writeRunning}>
          Set up the model
        </Button>
      </div>
      <form onSubmit={importModel} className="grid gap-1.5">
        <Label htmlFor={importId}>Or import a prepared model folder, without network access</Label>
        <div className="flex gap-2">
          <Input
            id={importId}
            placeholder="/absolute/path/to/all-MiniLM-L6-v2"
            value={importFrom}
            onChange={(event) => setImportFrom(event.target.value)}
            className="font-mono text-sm"
          />
          <Button type="submit" variant="outline" disabled={writeRunning || !importFrom.trim()}>
            Import
          </Button>
        </div>
      </form>
    </section>
  );
}
