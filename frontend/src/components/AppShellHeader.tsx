import React, { useState } from 'react';
import {
  Sparkles,
  History,
  Command,
  Play,
  Wand2,
  Database,
  ChevronDown,
} from 'lucide-react';

interface VersionMeta {
  id: string;
  label: string;
  createdAt: number;
}

interface AppShellHeaderProps {
  prompt: string;
  statusLabel: string;
  statusTone?: 'neutral' | 'active' | 'success' | 'warning' | 'error';
  onRunAgain?: () => void;
  busy?: boolean;
  onDatabaseClick?: () => void;
  databaseOpen?: boolean;
  versions?: VersionMeta[];
  activeVersionId?: string | null;
  onSelectVersion?: (id: string) => void;
}

const statusToneStyles: Record<NonNullable<AppShellHeaderProps['statusTone']>, string> = {
  neutral: 'bg-appia-surface text-appia-muted border-appia-border',
  active: 'bg-appia-accent-soft text-appia-foreground border-appia-accent/40 shadow-appia-glow',
  success: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30',
  warning: 'bg-amber-500/15 text-amber-200 border-amber-400/30',
  error: 'bg-rose-500/15 text-rose-200 border-rose-400/30',
};

export function AppShellHeader({
  prompt,
  statusLabel,
  statusTone = 'neutral',
  onRunAgain,
  busy = false,
  onDatabaseClick,
  databaseOpen = false,
  versions = [],
  activeVersionId = null,
  onSelectVersion,
}: AppShellHeaderProps) {
  const statusClassName = statusToneStyles[statusTone];
  const [versionMenuOpen, setVersionMenuOpen] = useState(false);

  return (
    <header className="relative z-30 border-b border-appia-border/70 bg-appia-surface/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1680px] items-center justify-between px-6">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 rounded-full border border-appia-border/80 bg-appia-sunken px-3 py-1.5 text-sm font-semibold text-appia-foreground shadow-appia-card">
            <Sparkles className="h-4 w-4 text-appia-accent" />
            Appia Builder
          </div>
          <div className="hidden items-center gap-3 text-sm text-appia-muted lg:flex">
            <History className="h-4 w-4 text-appia-muted" />
            <span className="truncate max-w-[360px] text-appia-foreground/85">{prompt}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {versions.length > 0 && (
            <div
              className="relative"
              onMouseEnter={() => setVersionMenuOpen(true)}
              onMouseLeave={() => setVersionMenuOpen(false)}
            >
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-xl border border-appia-border/70 bg-appia-surface px-3 py-2 text-sm font-medium text-appia-foreground/90 hover:border-appia-accent/40"
                onClick={() => setVersionMenuOpen((prev) => !prev)}
              >
                Version{' '}
                {versions.find((version) => version.id === activeVersionId)?.label ?? 'Current'}
                <ChevronDown className="h-4 w-4 text-appia-muted" />
              </button>
              {onSelectVersion && versionMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-60 overflow-hidden rounded-2xl border border-appia-border/70 bg-appia-surface/95 text-sm text-appia-foreground shadow-appia-card">
                  <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-appia-muted">
                    Version History
                  </div>
                  <button
                    type="button"
                    onClick={() => onSelectVersion('__current__')}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left transition hover:bg-appia-accent-soft/40 ${
                      activeVersionId === null
                        ? 'text-appia-foreground'
                        : 'text-appia-foreground/85'
                    }`}
                  >
                    <span>Current workspace</span>
                    <span className="text-xs text-appia-muted">Live</span>
                  </button>
                  {versions.map((version) => (
                    <button
                      key={version.id}
                      type="button"
                      onClick={() => onSelectVersion(version.id)}
                      className={`flex w-full items-center justify-between px-3 py-2 text-left transition hover:bg-appia-accent-soft/40 ${
                        version.id === activeVersionId
                          ? 'text-appia-foreground'
                          : 'text-appia-foreground/85'
                      }`}
                    >
                      <span>{version.label}</span>
                      <span className="text-xs text-appia-muted">
                        {new Date(version.createdAt).toLocaleTimeString()}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium uppercase tracking-wide transition ${statusClassName}`}
          >
            {busy ? (
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-appia-accent opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-appia-accent" />
              </span>
            ) : (
              <Wand2 className="h-3.5 w-3.5 text-current" />
            )}
            {statusLabel}
          </div>
          <button
            type="button"
            onClick={onDatabaseClick}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
              databaseOpen
                ? 'border-appia-accent/60 bg-appia-accent-soft text-appia-foreground shadow-appia-glow'
                : 'border-appia-border/80 bg-appia-surface text-appia-foreground/90 hover:border-appia-accent/60'
            }`}
          >
            <Database className="h-4 w-4 text-appia-accent" />
            Database
          </button>
          <div className="hidden items-center gap-2 text-xs font-medium text-appia-muted md:flex">
            <div className="inline-flex items-center gap-1 rounded-lg border border-appia-border/80 bg-appia-surface px-2 py-1">
              <Command className="h-3.5 w-3.5 text-appia-muted" />
              <span>/</span>
            </div>
            <div className="inline-flex items-center gap-1 rounded-lg border border-appia-border/80 bg-appia-surface px-2 py-1">
              <Command className="h-3.5 w-3.5 text-appia-muted" />
              <span>K</span>
            </div>
          </div>
          {onRunAgain && (
            <button
              onClick={onRunAgain}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-full border border-appia-accent/40 bg-appia-accent-soft px-4 py-2 text-sm font-medium text-appia-foreground transition hover:border-appia-accent/60 hover:shadow-appia-glow disabled:cursor-not-allowed disabled:border-appia-border disabled:bg-appia-surface disabled:text-appia-muted"
            >
              <Play className="h-4 w-4" />
              Run Again
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
