const DEFAULT_API_BASE = '/api/v1';

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
    if (normalized.endsWith('/api/v1')) {
      return normalized;
    }
    if (normalized.endsWith('/api')) {
      return `${normalized}/v1`;
    }
    return `${normalized}/api/v1`;
  }

  try {
    const parsed = new URL(normalized);
    const path = trimTrailingSlash(parsed.pathname);
    const origin = `${parsed.protocol}//${parsed.host}`;

    if (!path || path === '/') {
      return `${origin}/api/v1`;
    }
    if (path.endsWith('/api/v1')) {
      return `${origin}${path}`;
    }
    if (path.endsWith('/api')) {
      return `${origin}${path}/v1`;
    }
    return `${origin}${path}/api/v1`;
  } catch {
    return DEFAULT_API_BASE;
  }
}
