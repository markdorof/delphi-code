import type { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Link, Outlet } from "@tanstack/react-router";

export interface RouterContext {
  queryClient: QueryClient;
}

const NAVIGATION = [
  { to: "/", label: "Search" },
  { to: "/projects", label: "Projects" },
] as const;

export const Route = createRootRouteWithContext<RouterContext>()({
  component: AppShell,
});

function AppShell() {
  return (
    <div className="min-h-dvh">
      <header className="border-b">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <Link to="/" className="font-semibold">
            Delphi Code
          </Link>
          {NAVIGATION.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="text-muted-foreground text-sm hover:text-foreground"
              activeProps={{ className: "text-foreground" }}
              activeOptions={{ exact: true, includeSearch: false }}
            >
              {label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
