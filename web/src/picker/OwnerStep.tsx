import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useState } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import type { components } from "@/api/schema";
import { FailureMessage } from "@/components/FailureMessage";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type HostingService = components["schemas"]["HostingServiceResponse"];

export function OwnerStep({ service, onChoose }: { service: HostingService; onChoose: (owner: string) => void }) {
  const { client } = useApiConnection();
  const owners = useQuery({
    queryKey: ["hosting-services", service.domain, "owners"],
    queryFn: async () =>
      dataOrFailure(
        await client.GET("/api/hosting-services/{domain}/owners", { params: { path: { domain: service.domain } } }),
      ).owners,
  });
  const onlyOwner = owners.data?.length === 1 ? owners.data[0] : undefined;
  useEffect(() => {
    if (onlyOwner) {
      onChoose(onlyOwner.slug);
    }
  }, [onlyOwner, onChoose]);

  if (owners.isPending || onlyOwner) {
    return (
      <p className="text-muted-foreground">
        Listing {service.owner_noun}s on {service.name}…
      </p>
    );
  }
  if (owners.isError) {
    return <FailureMessage failure={owners.error} />;
  }
  if (owners.data === null) {
    return <TypedOwner service={service} onChoose={onChoose} />;
  }
  return (
    <section className="grid gap-3">
      <h2 className="font-medium first-letter:uppercase">
        Which {service.name} {service.owner_noun}?
      </h2>
      <Command className="rounded-lg border">
        <CommandInput placeholder={`Find a ${service.owner_noun}…`} />
        <CommandList>
          <CommandEmpty>No {service.owner_noun} matches.</CommandEmpty>
          {owners.data.map((owner) => (
            <CommandItem key={owner.slug} value={`${owner.name} ${owner.slug}`} onSelect={() => onChoose(owner.slug)}>
              {owner.name}
              {owner.name !== owner.slug && <span className="text-muted-foreground">{owner.slug}</span>}
            </CommandItem>
          ))}
        </CommandList>
      </Command>
    </section>
  );
}

function TypedOwner({ service, onChoose }: { service: HostingService; onChoose: (owner: string) => void }) {
  const id = useId();
  const [owner, setOwner] = useState(service.suggested_owner ?? "");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (owner.trim()) {
      onChoose(owner.trim());
    }
  }
  return (
    <form onSubmit={submit} className="grid max-w-md gap-2">
      <Label htmlFor={id}>
        These credentials cannot list {service.name} {service.owner_noun}s. Which {service.owner_noun} should be
        indexed?
      </Label>
      <div className="flex gap-2">
        <Input id={id} value={owner} onChange={(event) => setOwner(event.target.value)} autoFocus />
        <Button type="submit" disabled={!owner.trim()}>
          Continue
        </Button>
      </div>
    </form>
  );
}
