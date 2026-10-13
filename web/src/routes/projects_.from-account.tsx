import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { OwnerStep } from "@/picker/OwnerStep";
import { RepositoryStep } from "@/picker/RepositoryStep";
import { ServiceStep } from "@/picker/ServiceStep";

interface PickerPosition {
  service?: string;
  owner?: string;
}

export const Route = createFileRoute("/projects_/from-account")({
  validateSearch: (search: Record<string, unknown>): PickerPosition => ({
    ...(typeof search.service === "string" && search.service ? { service: search.service } : {}),
    ...(typeof search.service === "string" && typeof search.owner === "string" && search.owner
      ? { owner: search.owner }
      : {}),
  }),
  component: RepositoryPickerPage,
});

function RepositoryPickerPage() {
  const { client } = useApiConnection();
  const position = Route.useSearch();
  const navigate = Route.useNavigate();
  const services = useQuery({
    queryKey: ["hosting-services"],
    queryFn: async () => dataOrFailure(await client.GET("/api/hosting-services")).hosting_services,
  });
  const service = services.data?.find(({ domain }) => domain === position.service);
  const chooseService = useCallback(
    (domain: string) => void navigate({ search: { service: domain }, replace: true }),
    [navigate],
  );
  const chooseOwner = useCallback(
    (owner: string) => void navigate({ search: (current) => ({ ...current, owner }) }),
    [navigate],
  );

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6">
      <header className="grid gap-1">
        <h1 className="font-semibold text-lg">Add from your account</h1>
        <nav aria-label="Picker steps" className="flex flex-wrap gap-x-2 text-muted-foreground text-sm">
          <Link to="/projects" className="hover:text-foreground">
            Projects
          </Link>
          {service && (
            <>
              <span aria-hidden>/</span>
              <Link to="/projects/from-account" className="hover:text-foreground">
                {service.name}
              </Link>
            </>
          )}
          {service && position.owner && (
            <>
              <span aria-hidden>/</span>
              <Link to="/projects/from-account" search={{ service: service.domain }} className="hover:text-foreground">
                {position.owner}
              </Link>
            </>
          )}
        </nav>
      </header>
      {!service && <ServiceStep onChoose={chooseService} />}
      {service && !position.owner && <OwnerStep service={service} onChoose={chooseOwner} />}
      {service && position.owner && <RepositoryStep service={service} owner={position.owner} />}
    </div>
  );
}
