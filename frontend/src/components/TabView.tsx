import React from 'react';
import { Code2, Eye, Rocket } from 'lucide-react';

interface TabViewProps {
  activeTab: 'code' | 'preview';
  onTabChange: (tab: 'code' | 'preview') => void;
  previewStatusLabel?: string;
  autoOpenPreview?: boolean;
  onAutoOpenPreviewChange?: (value: boolean) => void;
}

export function TabView({
  activeTab,
  onTabChange,
  previewStatusLabel,
  autoOpenPreview = true,
  onAutoOpenPreviewChange,
}: TabViewProps) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-appia-border/70 bg-appia-surface/90 px-2 py-2 shadow-appia-card">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onTabChange('code')}
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition ${
            activeTab === 'code'
              ? 'bg-appia-accent-soft text-appia-foreground shadow-appia-glow'
              : 'text-appia-muted hover:text-appia-foreground/90'
          }`}
        >
          <Code2 className="h-4 w-4" />
          Code
        </button>
        <button
          type="button"
          onClick={() => onTabChange('preview')}
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition ${
            activeTab === 'preview'
              ? 'bg-appia-accent-soft text-appia-foreground shadow-appia-glow'
              : 'text-appia-muted hover:text-appia-foreground/90'
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>
      <div className="flex items-center gap-3 text-xs text-appia-muted">
        {previewStatusLabel && (
          <span className="inline-flex items-center gap-1 rounded-full border border-appia-border/70 bg-appia-surface px-2 py-1 font-medium text-appia-foreground/80">
            <Rocket className="h-3.5 w-3.5 text-appia-accent" />
            {previewStatusLabel}
          </span>
        )}
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-appia-border/80 bg-appia-surface px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-appia-muted hover:border-appia-accent/40">
          <input
            type="checkbox"
            className="h-3.5 w-3.5 rounded border-appia-border/70 bg-appia-surface text-appia-accent focus:ring-appia-accent/40"
            checked={autoOpenPreview}
            onChange={(event) =>
              onAutoOpenPreviewChange?.(event.target.checked)
            }
          />
          Auto open preview
        </label>
      </div>
    </div>
  );
}
