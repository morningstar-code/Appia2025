import React from 'react';
import { Database, Plus, ArrowRight } from 'lucide-react';

interface DatabasePanelProps {
  open: boolean;
  onClose: () => void;
}

export function DatabasePanel({ open, onClose }: DatabasePanelProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-end bg-black/30 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative h-full w-[420px] border-l border-appia-border/80 bg-appia-surface/95 shadow-[0_20px_60px_rgba(3,7,18,0.6)]"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-appia-border/70 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-appia-accent-soft text-appia-foreground">
              <Database className="h-5 w-5 text-appia-accent" />
            </span>
            <div>
              <h2 className="text-base font-semibold text-appia-foreground">Database</h2>
              <p className="text-xs text-appia-muted/80">
                Model your tables, relationships, and seed data.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-appia-border/60 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-appia-muted hover:border-appia-accent/50 hover:text-appia-foreground"
          >
            Close
          </button>
        </header>

        <div className="flex h-full flex-col justify-between px-6 py-8 text-sm text-appia-foreground/85">
          <div className="space-y-4">
            <p className="leading-relaxed text-appia-muted">
              Ask Appia to scaffold a database schema or start from scratch. Once configured,
              tables and seed data will appear in the generated project automatically.
            </p>
            <div className="rounded-3xl border border-dashed border-appia-border/70 bg-appia-sunken px-5 py-6 text-center">
              <p className="text-appia-foreground/90">
                Tell Appia what tables, columns, and relationships you need. We will sync them into
                your project structure instantly.
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-2xl border border-appia-border/80 bg-appia-surface px-4 py-3 text-sm font-medium text-appia-foreground transition hover:border-appia-accent/50 hover:bg-appia-accent-soft/40"
            >
              <span className="inline-flex items-center gap-2">
                <Plus className="h-4 w-4 text-appia-accent" />
                Start a schema with Appia
              </span>
              <ArrowRight className="h-4 w-4 text-appia-muted" />
            </button>
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-2xl border border-appia-border/80 bg-appia-surface px-4 py-3 text-sm font-medium text-appia-foreground transition hover:border-appia-accent/50 hover:bg-appia-accent-soft/40"
            >
              <span className="inline-flex items-center gap-2">
                <Database className="h-4 w-4 text-appia-accent" />
                Import existing SQL
              </span>
              <ArrowRight className="h-4 w-4 text-appia-muted" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
