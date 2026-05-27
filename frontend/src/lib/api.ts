export const API_BASE =
  process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api"
    : "/api";

export function authHeaders(token: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}
