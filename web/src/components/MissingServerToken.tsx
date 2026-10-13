export function MissingServerToken() {
  return (
    <section className="mx-auto max-w-xl px-4 py-16">
      <h1 className="mb-2 font-semibold text-xl">Open Delphi Code from your terminal</h1>
      <p className="text-muted-foreground">
        This page needs the address that <code className="font-mono">delphi-code ui</code> opens or prints. Run it again
        to get a working link.
      </p>
    </section>
  );
}
