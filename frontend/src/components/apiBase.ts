const DEFAULT_API_BASE = '/api';

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

export function getApiBasePath(): string {
  const rawBase = (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE).trim();
  if (!rawBase) {
    return DEFAULT_API_BASE;
  }

  const normalized = trimTrailingSlash(rawBase);

  if (normalized.startsWith('/')) {
    return normalized.endsWith('/api/v1') ? normalized.slice(0, -3) : normalized;
  }

  try {
    const parsed = new URL(normalized);
    const path = trimTrailingSlash(parsed.pathname);
    const origin = `${parsed.protocol}//${parsed.host}`;

    if (!path || path === '/') {
      return `${origin}/api`;
    }
    if (path.endsWith('/api/v1')) {
      return `${origin}${path.slice(0, -3)}`;
    }
    if (path.endsWith('/api')) {
      return `${origin}${path}`;
    }
    return `${origin}${path}/api`;
  } catch {
    return DEFAULT_API_BASE;
  }
}
