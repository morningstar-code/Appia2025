'use client';

import { MonitorDot } from "lucide-react";

interface TerminalProps {
  logs: string[];
  title?: string;
}

export function Terminal({ logs, title = 'Background tasks' }: TerminalProps) {
  return (
    <section className="flex h-full flex-col overflow-hidden rounded-3xl border bg-card shadow">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <MonitorDot className="h-4 w-4 text-primary" />
          {title}
        </div>
        <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Live
        </div>
      </header>
      <div className="flex-1 overflow-y-auto bg-muted/20 px-4 py-3 font-mono text-xs text-muted-foreground">
        {logs.length === 0 ? (
          <div className="text-muted-foreground/80">Waiting for commands…</div>
        ) : (
          logs.map((log, index) => (
            <div key={`${log}-${index}`} className="mb-1 whitespace-pre-wrap text-foreground">
              {log}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
