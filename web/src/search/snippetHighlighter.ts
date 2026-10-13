import type { HighlighterCore, LanguageRegistration, ThemedToken } from "shiki/core";

type LanguageModule = Promise<{ default: LanguageRegistration[] }>;

const LIGHT_THEME = "github-light-default";
const DARK_THEME = "github-dark-default";

const LANGUAGE_MODULES_BY_INDEXED_LANGUAGE: Record<string, () => LanguageModule> = {
  bash: () => import("shiki/dist/langs/bash.mjs"),
  c: () => import("shiki/dist/langs/c.mjs"),
  cpp: () => import("shiki/dist/langs/cpp.mjs"),
  csharp: () => import("shiki/dist/langs/csharp.mjs"),
  css: () => import("shiki/dist/langs/css.mjs"),
  dart: () => import("shiki/dist/langs/dart.mjs"),
  elixir: () => import("shiki/dist/langs/elixir.mjs"),
  go: () => import("shiki/dist/langs/go.mjs"),
  haskell: () => import("shiki/dist/langs/haskell.mjs"),
  hcl: () => import("shiki/dist/langs/hcl.mjs"),
  html: () => import("shiki/dist/langs/html.mjs"),
  java: () => import("shiki/dist/langs/java.mjs"),
  javascript: () => import("shiki/dist/langs/javascript.mjs"),
  json: () => import("shiki/dist/langs/json.mjs"),
  kotlin: () => import("shiki/dist/langs/kotlin.mjs"),
  lua: () => import("shiki/dist/langs/lua.mjs"),
  markdown: () => import("shiki/dist/langs/markdown.mjs"),
  php: () => import("shiki/dist/langs/php.mjs"),
  proto: () => import("shiki/dist/langs/proto.mjs"),
  python: () => import("shiki/dist/langs/python.mjs"),
  r: () => import("shiki/dist/langs/r.mjs"),
  ruby: () => import("shiki/dist/langs/ruby.mjs"),
  rust: () => import("shiki/dist/langs/rust.mjs"),
  scala: () => import("shiki/dist/langs/scala.mjs"),
  sql: () => import("shiki/dist/langs/sql.mjs"),
  svelte: () => import("shiki/dist/langs/svelte.mjs"),
  swift: () => import("shiki/dist/langs/swift.mjs"),
  toml: () => import("shiki/dist/langs/toml.mjs"),
  tsx: () => import("shiki/dist/langs/tsx.mjs"),
  typescript: () => import("shiki/dist/langs/typescript.mjs"),
  vue: () => import("shiki/dist/langs/vue.mjs"),
  xml: () => import("shiki/dist/langs/xml.mjs"),
  yaml: () => import("shiki/dist/langs/yaml.mjs"),
};

let sharedHighlighter: Promise<HighlighterCore> | undefined;

function highlighter(): Promise<HighlighterCore> {
  sharedHighlighter ??= Promise.all([import("shiki/core"), import("shiki/engine/javascript")]).then(
    ([{ createHighlighterCore }, { createJavaScriptRegexEngine }]) =>
      createHighlighterCore({
        themes: [
          import("shiki/dist/themes/github-light-default.mjs"),
          import("shiki/dist/themes/github-dark-default.mjs"),
        ],
        langs: [],
        engine: createJavaScriptRegexEngine(),
      }),
  );
  return sharedHighlighter;
}

export function canHighlight(language: string): boolean {
  return language in LANGUAGE_MODULES_BY_INDEXED_LANGUAGE;
}

export async function highlightedLines(code: string, language: string): Promise<ThemedToken[][] | null> {
  const languageModule = LANGUAGE_MODULES_BY_INDEXED_LANGUAGE[language];
  if (languageModule === undefined) {
    return null;
  }
  const loaded = await highlighter();
  if (!loaded.getLoadedLanguages().includes(language)) {
    await loaded.loadLanguage(languageModule());
  }
  return loaded.codeToTokens(code, {
    lang: language,
    themes: { light: LIGHT_THEME, dark: DARK_THEME },
    defaultColor: false,
  }).tokens;
}
