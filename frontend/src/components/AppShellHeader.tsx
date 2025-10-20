import React from 'react';
import { Sparkles, History, Command, Play, Wand2 } from 'lucide-react';

interface AppShellHeaderProps {
  prompt: string;
  statusLabel: string;
  statusTone?: 'neutral' | 'active' | 'success' | 'warning' | 'error';
  onRunAgain?: () => void;
  busy?: boolean;
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
}: AppShellHeaderProps) {
  const statusClassName = statusToneStyles[statusTone];

  return (
    <header className="relative z-30 border-b border-appia-border/70 bg-appia-surface/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-full border border-appia-border/80 bg-appia-sunken px-3 py-1.5 text-sm font-medium text-appia-foreground shadow-appia-card">
            <Sparkles className="h-4 w-4 text-appia-accent" />
            Appia Builder
          </div>
          <div className="hidden items-center gap-2 text-sm text-appia-muted md:flex">
            <History className="h-4 w-4 text-appia-muted" />
            <span className="truncate max-w-[320px] text-appia-foreground/80">{prompt}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
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
