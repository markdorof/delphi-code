import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { Plugin } from "vite";

const NODE_MODULES = "/node_modules/";
const LICENSE_FILE_NAME = /^(licen[cs]e|copying|notice)(\.|-|$)/i;
// Tailwind compiles these into the stylesheet, so they never show up as bundled modules.
const PACKAGES_COMPILED_INTO_THE_STYLESHEET = ["tailwindcss", "tw-animate-css"];

interface PackageNotice {
  name: string;
  version: string;
  license: string;
  texts: string[];
}

export function thirdPartyLicensesFile(fileName: string): Plugin {
  return {
    name: "third-party-licenses-file",
    apply: "build",
    generateBundle() {
      const roots = new Set<string>();
      for (const moduleId of this.getModuleIds()) {
        const root = packageRootOf(moduleId);
        if (root) {
          roots.add(root);
        }
      }
      for (const name of PACKAGES_COMPILED_INTO_THE_STYLESHEET) {
        roots.add(join(process.cwd(), "node_modules", name));
      }
      const notices = new Map<string, PackageNotice>();
      for (const root of roots) {
        const notice = packageNotice(root);
        notices.set(`${notice.name}@${notice.version}`, notice);
      }
      const sorted = [...notices.values()].sort((left, right) => left.name.localeCompare(right.name));
      this.emitFile({ type: "asset", fileName, source: licensesText(sorted) });
    },
  };
}

function packageRootOf(moduleId: string): string | null {
  const path = moduleId.replace(/^\0/, "").split("?")[0] ?? "";
  const start = path.lastIndexOf(NODE_MODULES);
  if (start === -1) {
    return null;
  }
  const afterNodeModules = path.slice(start + NODE_MODULES.length).split("/");
  const nameParts = afterNodeModules[0]?.startsWith("@") ? 2 : 1;
  return path.slice(0, start + NODE_MODULES.length) + afterNodeModules.slice(0, nameParts).join("/");
}

function packageNotice(root: string): PackageNotice {
  const manifest = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
    name: string;
    version: string;
    license?: string;
  };
  const licenseFiles = existsSync(root) ? readdirSync(root).filter((file) => LICENSE_FILE_NAME.test(file)) : [];
  return {
    name: manifest.name,
    version: manifest.version,
    license: manifest.license ?? "UNKNOWN",
    texts: licenseFiles.sort().map((file) => readFileSync(join(root, file), "utf8").trim()),
  };
}

function licensesText(notices: PackageNotice[]): string {
  const header =
    "Third-party software bundled into the Delphi Code web UI, with the license texts each package ships.\n";
  const sections = notices.map((notice) =>
    [
      `${notice.name} ${notice.version} (${notice.license})`,
      ...(notice.texts.length ? notice.texts : ["This package ships no license file; see its declared license."]),
    ].join("\n\n"),
  );
  const separator = `\n\n${"=".repeat(80)}\n\n`;
  return `${[header, ...sections].join(separator)}\n`;
}
