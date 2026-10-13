import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { FailureMessage } from "@/components/FailureMessage";
import { Button } from "@/components/ui/button";
import { CredentialsGuide } from "./CredentialsGuide";

export function ServiceStep({ onChoose }: { onChoose: (domain: string) => void }) {
  const { client } = useApiConnection();
  const services = useQuery({
    queryKey: ["hosting-services"],
    queryFn: async () => dataOrFailure(await client.GET("/api/hosting-services")).hosting_services,
  });
  const onlyService = services.data?.length === 1 ? services.data[0] : undefined;
  useEffect(() => {
    if (onlyService) {
      onChoose(onlyService.domain);
    }
  }, [onlyService, onChoose]);

  if (services.isPending || onlyService) {
    return <p className="text-muted-foreground">Looking for your accounts…</p>;
  }
  if (services.isError) {
    return <FailureMessage failure={services.error} />;
  }
  if (services.data.length === 0) {
    return <CredentialsGuide />;
  }
  return (
    <section className="grid gap-3">
      <h2 className="font-medium">Which account?</h2>
      <div className="flex flex-wrap gap-2">
        {services.data.map((service) => (
          <Button key={service.domain} variant="outline" onClick={() => onChoose(service.domain)}>
            {service.name}
          </Button>
        ))}
      </div>
    </section>
  );
}
