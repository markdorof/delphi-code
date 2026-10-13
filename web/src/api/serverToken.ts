const TOKEN_IN_ADDRESS = /^#token=(.+)$/;
const STORED_TOKEN_KEY = "delphi-code-server-token";

export function serverTokenFromPageAddress(location: Location, history: History, storage: Storage): string | null {
  const handedOver = TOKEN_IN_ADDRESS.exec(location.hash)?.[1];
  if (handedOver) {
    storage.setItem(STORED_TOKEN_KEY, decodeURIComponent(handedOver));
    history.replaceState(history.state, "", `${location.pathname}${location.search}`);
  }
  return storage.getItem(STORED_TOKEN_KEY);
}

export function reloadWhenTokenArrives(window: Window): void {
  window.addEventListener("hashchange", () => {
    if (TOKEN_IN_ADDRESS.test(window.location.hash)) {
      window.location.reload();
    }
  });
}
