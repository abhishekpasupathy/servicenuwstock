import useSWR from "swr";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://servicenuwstock-api.onrender.com/api/v1";

export async function api<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export function useApi<T>(path: string, refreshInterval = 60000) {
  return useSWR<T>(path, api, { refreshInterval, revalidateOnFocus: false });
}

export function money(value?: number | null) {
  return `$${Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

export function pct(value?: number | null) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}
