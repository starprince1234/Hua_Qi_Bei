'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { getEvents } from '@/lib/api';
import type { NewsEvent, NewsEventList } from '@/types/intelligence';

type ImpactDirection = NewsEvent['impact_direction'];
type ImpactLevel = NewsEvent['impact_level'];

interface EventFilters {
  impact_direction: '' | ImpactDirection;
  impact_level: '' | ImpactLevel;
  source: string;
  from_date: string;
  to_date: string;
  keyword: string;
}

const INITIAL_FILTERS: EventFilters = {
  impact_direction: '',
  impact_level: '',
  source: '',
  from_date: '',
  to_date: '',
  keyword: '',
};

interface CachedNewsState {
  filters: EventFilters;
  eventList: NewsEventList;
}

const NEWS_CACHE_KEY = 'huaqibei.newsEvents.cache.v1';
let memoryNewsCache: CachedNewsState | null = null;

const directionStyles: Record<ImpactDirection, string> = {
  bullish: 'border-green-500/40 bg-green-500/10 text-green-300',
  bearish: 'border-red-500/40 bg-red-500/10 text-red-300',
  neutral: 'border-gray-500/40 bg-gray-500/10 text-gray-300',
};

const levelStyles: Record<ImpactLevel, string> = {
  high: 'border-red-400/50 bg-red-400/10 text-red-200',
  medium: 'border-amber-400/50 bg-amber-400/10 text-amber-200',
  low: 'border-blue-400/50 bg-blue-400/10 text-blue-200',
};

const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to load news events.';
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function readCachedNewsState(): CachedNewsState | null {
  if (memoryNewsCache) {
    return memoryNewsCache;
  }

  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(NEWS_CACHE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedNewsState;
    if (!parsed?.eventList?.items || !parsed.filters) {
      return null;
    }
    memoryNewsCache = parsed;
    return parsed;
  } catch {
    return null;
  }
}

function writeCachedNewsState(nextState: CachedNewsState): void {
  memoryNewsCache = nextState;

  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(NEWS_CACHE_KEY, JSON.stringify(nextState));
  } catch {
    // Keep the in-memory cache even if browser storage is unavailable or full.
  }
}

function ProviderStatusBadge({ providerStatus }: { providerStatus: string }) {
  return (
    <span
      className="rounded-full border border-gray-600 bg-gray-800 px-2 py-1 text-xs font-medium text-gray-300"
      title="Provider/cache status returned by the backend."
    >
      Provider: {providerStatus}
    </span>
  );
}

function ImpactBadge({ direction }: { direction: ImpactDirection }) {
  return (
    <span className={`rounded-full border px-2 py-1 text-xs font-semibold capitalize ${directionStyles[direction]}`}>
      {direction}
    </span>
  );
}

function ImpactLevelBadge({ level }: { level: ImpactLevel }) {
  return (
    <span className={`rounded-full border px-2 py-1 text-xs font-semibold capitalize ${levelStyles[level]}`}>
      {level} impact
    </span>
  );
}

function EventLink({ url }: { url: string }) {
  if (!url) {
    return <span className="text-xs text-gray-500">No source URL</span>;
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-xs font-medium text-accent-primary underline-offset-4 hover:underline"
    >
      Open source
    </a>
  );
}

function NewsCard({ event, providerStatus }: { event: NewsEvent; providerStatus: string }) {
  return (
    <motion.article
      variants={itemVariants}
      exit="exit"
      className="rounded-lg border border-gray-800 bg-gray-900 p-4 shadow-lg shadow-black/10"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <ImpactBadge direction={event.impact_direction} />
        <ImpactLevelBadge level={event.impact_level} />
        <ProviderStatusBadge providerStatus={providerStatus} />
      </div>
      <h3 className="text-base font-bold leading-6 text-white">{event.title}</h3>
      <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-300">{event.summary}</p>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-gray-400">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">Time</p>
          <p className="text-gray-200">{formatTimestamp(event.published_at)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">Source</p>
          <p className="text-gray-200">{event.source}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">Confidence</p>
          <p className="text-gray-200">{formatScore(event.confidence)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">Impact score</p>
          <p className="text-gray-200">{event.impact_score.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">URL</p>
          <EventLink url={event.url} />
        </div>
      </div>
      {event.affected_industries.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {event.affected_industries.map((industry) => (
            <span key={`${event.event_id}-${industry}`} className="rounded-full bg-gray-800 px-2 py-1 text-xs text-gray-300">
              {industry}
            </span>
          ))}
        </div>
      )}
      {event.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {event.tags.map((tag) => (
            <span key={`${event.event_id}-${tag}`} className="rounded-full bg-gray-950 px-2 py-1 text-xs text-gray-400">
              {tag}
            </span>
          ))}
        </div>
      )}
    </motion.article>
  );
}

export default function NewsPanel() {
  const [initialCachedState] = useState<CachedNewsState | null>(() => memoryNewsCache);
  const [filters, setFilters] = useState<EventFilters>(initialCachedState?.filters ?? INITIAL_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<EventFilters>(initialCachedState?.filters ?? INITIAL_FILTERS);
  const [eventList, setEventList] = useState<NewsEventList | null>(initialCachedState?.eventList ?? null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cachedState = readCachedNewsState();
    if (!cachedState) {
      return;
    }

    setFilters(cachedState.filters);
    setAppliedFilters(cachedState.filters);
    setEventList(cachedState.eventList);
  }, []);

  const sources = useMemo(() => {
    const eventSources = eventList?.items.map((event) => event.source).filter(Boolean) ?? [];
    return Array.from(new Set(eventSources)).sort((a, b) => a.localeCompare(b));
  }, [eventList]);

  const loadEvents = useCallback(async (nextFilters: EventFilters = appliedFilters) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await getEvents({
        impact_direction: nextFilters.impact_direction || undefined,
        impact_level: nextFilters.impact_level || undefined,
        source: nextFilters.source.trim() || undefined,
        from_date: nextFilters.from_date || undefined,
        to_date: nextFilters.to_date || undefined,
        keyword: nextFilters.keyword.trim() || undefined,
        limit: 50,
      });
      setAppliedFilters(nextFilters);
      setEventList(data);
      writeCachedNewsState({ filters: nextFilters, eventList: data });
    } catch (loadError: unknown) {
      setError(getErrorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [appliedFilters]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void loadEvents(filters);
  };

  const resetFilters = () => {
    setFilters(INITIAL_FILTERS);
  };

  const events = eventList?.items ?? [];
  const providerStatus = eventList?.provider_status ?? 'unavailable';
  const hasCachedEvents = Boolean(eventList);
  const hasPendingFilterChanges = JSON.stringify(filters) !== JSON.stringify(appliedFilters);

  return (
    <section className="w-full max-w-7xl mx-auto p-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-6"
      >
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">News Intelligence</h2>
            <p className="mt-1 text-sm text-gray-400">
              News stays cached on this page. Change filters, then press Apply to fetch a fresh snapshot.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-gray-700 bg-gray-800 px-3 py-1 text-sm text-gray-300">
              {eventList ? `${events.length} events` : 'No snapshot loaded'}
            </span>
            <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-sm text-amber-200">
              Updated: {eventList ? formatTimestamp(eventList.updated_at) : '-'}
            </span>
            <ProviderStatusBadge providerStatus={providerStatus} />
            {hasPendingFilterChanges && (
              <span className="rounded-full border border-blue-400/40 bg-blue-400/10 px-3 py-1 text-sm text-blue-200">
                Pending filters
              </span>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-6">
          <label className="space-y-2 text-sm text-gray-300">
            <span>Impact direction</span>
            <select
              value={filters.impact_direction}
              onChange={(event) => setFilters((current) => ({ ...current, impact_direction: event.target.value as EventFilters['impact_direction'] }))}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 focus:border-accent-primary focus:outline-none"
            >
              <option value="">All directions</option>
              <option value="bullish">Bullish</option>
              <option value="bearish">Bearish</option>
              <option value="neutral">Neutral</option>
            </select>
          </label>

          <label className="space-y-2 text-sm text-gray-300">
            <span>Impact level</span>
            <select
              value={filters.impact_level}
              onChange={(event) => setFilters((current) => ({ ...current, impact_level: event.target.value as EventFilters['impact_level'] }))}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 focus:border-accent-primary focus:outline-none"
            >
              <option value="">All levels</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </label>

          <label className="space-y-2 text-sm text-gray-300">
            <span>Source</span>
            <input
              list="news-sources"
              value={filters.source}
              onChange={(event) => setFilters((current) => ({ ...current, source: event.target.value }))}
              placeholder="Any source"
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 placeholder:text-gray-500 focus:border-accent-primary focus:outline-none"
            />
            <datalist id="news-sources">
              {sources.map((source) => (
                <option key={source} value={source} />
              ))}
            </datalist>
          </label>

          <label className="space-y-2 text-sm text-gray-300">
            <span>From date</span>
            <input
              type="date"
              value={filters.from_date}
              onChange={(event) => setFilters((current) => ({ ...current, from_date: event.target.value }))}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 focus:border-accent-primary focus:outline-none"
            />
          </label>

          <label className="space-y-2 text-sm text-gray-300">
            <span>To date</span>
            <input
              type="date"
              value={filters.to_date}
              onChange={(event) => setFilters((current) => ({ ...current, to_date: event.target.value }))}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 focus:border-accent-primary focus:outline-none"
            />
          </label>

          <label className="space-y-2 text-sm text-gray-300">
            <span>Keyword</span>
            <input
              value={filters.keyword}
              onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
              placeholder="oil, OPEC, freight..."
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-200 placeholder:text-gray-500 focus:border-accent-primary focus:outline-none"
            />
          </label>

          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 rounded-md bg-accent-primary px-4 py-2 font-medium text-background transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
            >
              Apply
            </button>
            <button
              type="button"
              onClick={resetFilters}
              disabled={isLoading}
              className="rounded-md border border-gray-700 px-4 py-2 font-medium text-gray-300 transition-colors hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reset
            </button>
          </div>
        </form>
      </motion.div>

      {isLoading && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-gray-300">
          Fetching news events...
        </div>
      )}

      {!isLoading && error && (
        <div className="rounded-lg border border-red-700 bg-red-900/30 p-6 text-red-200">
          <p className="font-semibold">News events failed to load.</p>
          <p className="mt-1 text-sm">{error}</p>
          <p className="mt-3 text-sm text-red-100/80">Update filters if needed, then press Apply to request a fresh snapshot.</p>
        </div>
      )}

      {!isLoading && !error && !hasCachedEvents && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-gray-300">
          Press Apply to fetch the latest news snapshot.
        </div>
      )}

      {!isLoading && !error && hasCachedEvents && events.length === 0 && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-gray-300">
          No news events matched the selected filters.
        </div>
      )}

      {!isLoading && !error && events.length > 0 && (
        <>
          <motion.div variants={listVariants} initial="hidden" animate="visible" className="grid gap-4 md:hidden">
            <AnimatePresence>
              {events.map((event) => (
                <NewsCard key={event.event_id} event={event} providerStatus={providerStatus} />
              ))}
            </AnimatePresence>
          </motion.div>

          <motion.div
            variants={listVariants}
            initial="hidden"
            animate="visible"
            className="hidden overflow-hidden rounded-lg border border-gray-800 bg-gray-900 md:block"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-300">
                <thead className="bg-gray-950/70 text-xs uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Title</th>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Impact</th>
                    <th className="px-4 py-3">URL</th>
                    <th className="px-4 py-3">Confidence</th>
                    <th className="px-4 py-3">Provider</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {events.map((event) => (
                      <motion.tr
                        key={event.event_id}
                        variants={itemVariants}
                        exit="exit"
                        className="border-t border-gray-800 align-top"
                      >
                        <td className="max-w-xl px-4 py-4">
                          <p className="font-semibold text-white">{event.title}</p>
                          <p className="mt-1 line-clamp-2 text-xs leading-5 text-gray-400">{event.summary}</p>
                        </td>
                        <td className="whitespace-nowrap px-4 py-4 text-gray-300">{formatTimestamp(event.published_at)}</td>
                        <td className="whitespace-nowrap px-4 py-4 text-gray-300">{event.source}</td>
                        <td className="px-4 py-4">
                          <div className="flex flex-wrap gap-2">
                            <ImpactBadge direction={event.impact_direction} />
                            <ImpactLevelBadge level={event.impact_level} />
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-4 py-4">
                          <EventLink url={event.url} />
                        </td>
                        <td className="whitespace-nowrap px-4 py-4 text-gray-200">{formatScore(event.confidence)}</td>
                        <td className="whitespace-nowrap px-4 py-4">
                          <ProviderStatusBadge providerStatus={providerStatus} />
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </motion.div>
        </>
      )}
    </section>
  );
}
