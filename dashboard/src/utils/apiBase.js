const rawBase = import.meta.env.VITE_API_URL || "/api";

const trimTrailingSlash = (value) => value.replace(/\/+$/, "");

const normalizeApiBase = (value) => {
  if (!value) return "/api";
  let normalized = trimTrailingSlash(value);
  if (normalized.endsWith("/api")) return normalized;
  
  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return `${normalized}/api`;
  }
  return `${normalized}/api`;
};

export const API_URL = normalizeApiBase(rawBase);
