import { useMutation } from "@tanstack/react-query";
import { type ReactNode, useId, useState } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { FailureMessage } from "@/components/FailureMessage";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ProjectPicker } from "@/search/ProjectPicker";

const SERVER_WORKING_FOLDER = ".";

export function DoctorSection() {
  const pickerId = useId();
  const { client } = useApiConnection();
  const [projectKey, setProjectKey] = useState<string | undefined>();
  const doctor = useMutation({
    mutationFn: async (project: string) =>
      dataOrFailure(await client.GET("/api/doctor", { params: { query: { project } } })),
  });
  const report = doctor.data;

  return (
    <section className="grid gap-3 rounded-lg border p-4">
      <h2 className="font-medium">Check the installation</h2>
      <p className="text-muted-foreground text-sm">
        Loads the model, embeds a test sentence, and checks SQLite and the index storage, all without network access.
      </p>
      <div className="grid gap-1.5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end sm:gap-2">
        <div className="grid gap-1.5">
          <Label htmlFor={pickerId}>Project</Label>
          <ProjectPicker
            id={pickerId}
            projectKey={projectKey}
            onChange={setProjectKey}
            noProjectLabel="The folder delphi-code ui started in"
          />
        </div>
        <Button onClick={() => doctor.mutate(projectKey ?? SERVER_WORKING_FOLDER)} disabled={doctor.isPending}>
          {doctor.isPending ? "Checking…" : "Run checks"}
        </Button>
      </div>
      {doctor.isError && <FailureMessage failure={doctor.error} />}
      {report && (
        <dl
          aria-label="Installation checks"
          className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm"
        >
          <Check label="Version">{report.version}</Check>
          <Check label="Model">{report.model}</Check>
          <Check label="Model checksum">
            <span className="font-mono">{report.model_sha256.slice(0, 16)}…</span>
          </Check>
          <Check label="Embedding">
            {report.dimensions} dimensions, self-distance {report.self_distance.toFixed(4)}
          </Check>
          <Check label="Storage">{report.cocoindex_storage}</Check>
          <Check label="SQLite">{report.sqlite}</Check>
          <Check label="Offline">{report.offline ? `yes (${report.network_guard})` : "no"}</Check>
          {report.project && <Check label="Project">{report.project}</Check>}
          {report.index_directory && <Check label="Index">{report.index_directory}</Check>}
          <Check label="Libraries">
            {Object.entries(report.dependencies)
              .map(([name, version]) => `${name} ${version}`)
              .join(", ")}
          </Check>
        </dl>
      )}
    </section>
  );
}

function Check({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="break-all">{children}</dd>
    </>
  );
}
