import React from 'react';
import { MonitorDot } from 'lucide-react';

interface TerminalProps {
  logs: string[];
  title?: string;
}

export function Terminal({ logs, title = 'Background tasks' }: TerminalProps) {
  return (
    <section className="flex h-full flex-col overflow-hidden rounded-3xl border border-appia-border/70 bg-appia-surface/90 shadow-appia-card">
      <header className="flex items-center justify-between border-b border-appia-border/70 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium text-appia-foreground/90">
          <MonitorDot className="h-4 w-4 text-appia-accent" />
          {title}
        </div>
        <div className="inline-flex items-center gap-2 text-xs text-appia-muted">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Live
        </div>
      </header>
      <div className="flex-1 overflow-y-auto bg-appia-terminal px-4 py-3 font-mono text-xs text-appia-foreground/80">
        {logs.length === 0 ? (
          <div className="text-appia-muted/80">Waiting for commands…</div>
        ) : (
          logs.map((log, index) => (
            <div key={`${log}-${index}`} className="mb-1 whitespace-pre-wrap">
              {log}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
