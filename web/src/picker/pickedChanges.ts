export interface PickedChanges {
  added: string[];
  removed: string[];
}

export function pickedChanges(listedKeys: string[], chosenKeys: Set<string>, trackedKeys: Set<string>): PickedChanges {
  return {
    added: listedKeys.filter((key) => chosenKeys.has(key) && !trackedKeys.has(key)),
    removed: listedKeys.filter((key) => !chosenKeys.has(key) && trackedKeys.has(key)),
  };
}
