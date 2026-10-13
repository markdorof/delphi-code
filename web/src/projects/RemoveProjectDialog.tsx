import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import type { components } from "@/api/schema";
import { FailureMessage } from "@/components/FailureMessage";
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
import { Label } from "@/components/ui/label";
import type { ListedProject } from "./listedProject";

export type ProjectRemoval = components["schemas"]["ProjectRemovalResponse"];

export function RemoveProjectDialog({
  project,
  onClose,
  onRemoved,
}: {
  project: ListedProject | null;
  onClose: () => void;
  onRemoved: (removal: ProjectRemoval) => void;
}) {
  return (
    <Dialog open={project !== null} onOpenChange={(open) => open || onClose()}>
      <DialogContent>
        {project && <RemovalConfirmation key={project.key} project={project} onRemoved={onRemoved} />}
      </DialogContent>
    </Dialog>
  );
}

function RemovalConfirmation({
  project,
  onRemoved,
}: {
  project: ListedProject;
  onRemoved: (removal: ProjectRemoval) => void;
}) {
  const { client } = useApiConnection();
  const queryClient = useQueryClient();
  const keepIndexId = useId();
  const [keepIndex, setKeepIndex] = useState(false);
  const removal = useMutation({
    mutationFn: async () =>
      dataOrFailure(
        await client.DELETE("/api/projects", { params: { query: { name: project.key, keep_index: keepIndex } } }),
      ),
    onSuccess: async (removed) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      onRemoved(removed);
    },
  });
  const deletesIndex = !keepIndex && project.index_directory !== null;
  return (
    <>
      <DialogHeader>
        <DialogTitle>Remove {project.key}?</DialogTitle>
        <DialogDescription>
          {project.tracked ? "Sync will stop updating it. " : ""}
          {deletesIndex ? "Its index is deleted; your files are not touched." : "Your files are not touched."}
        </DialogDescription>
      </DialogHeader>
      {project.tracked && project.index_directory && (
        <div className="flex items-center gap-2">
          <Checkbox
            id={keepIndexId}
            checked={keepIndex}
            onCheckedChange={(checked) => setKeepIndex(checked === true)}
          />
          <Label htmlFor={keepIndexId}>Keep the index so it stays searchable</Label>
        </div>
      )}
      {removal.isError && <FailureMessage failure={removal.error} />}
      <DialogFooter>
        <Button variant="destructive" disabled={removal.isPending} onClick={() => removal.mutate()}>
          {removal.isPending ? "Removing…" : "Remove"}
        </Button>
      </DialogFooter>
    </>
  );
}
