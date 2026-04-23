const rawBase = import.meta.env.VITE_API_URL || "/api";

const trimTrailingSlash = (value) => value.replace(/\/+$/, "");

const normalizeApiBase = (value) => {
  const normalized = trimTrailingSlash(value || "/api");
  if (!normalized) return "/api";
  if (normalized === "/api" || normalized.endsWith("/api")) return normalized;
  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return `${normalized}/api`;
  }
  return normalized;
};

export const API_URL = normalizeApiBase(rawBase);
