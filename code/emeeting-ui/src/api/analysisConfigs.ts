import { apiFetch } from "./http";
import type { AnalysisModules, UserAnalysisConfig } from "../types/db";

export async function getAnalysisConfigs(): Promise<UserAnalysisConfig[]> {
  const res = await apiFetch("/analysis-configs");
  if (!res.ok) throw new Error("Failed to fetch analysis configs");
  const json = await res.json();
  return Array.isArray(json) ? (json as UserAnalysisConfig[]) : [];
}

export async function createAnalysisConfig(payload: {
  name: string;
  modulesJson: AnalysisModules;
  isDefault?: boolean;
}): Promise<UserAnalysisConfig> {
  const res = await apiFetch("/analysis-configs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create analysis config");
  return (await res.json()) as UserAnalysisConfig;
}

export async function deleteAnalysisConfig(configId: number): Promise<void> {
  const res = await apiFetch(`/analysis-configs/${configId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete analysis config");
}

