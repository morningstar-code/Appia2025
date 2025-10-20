'use client';

import { Code2, Eye, Rocket } from "lucide-react";

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
  const autoPreviewDisabled = !onAutoOpenPreviewChange;

  return (
    <div className="flex items-center justify-between rounded-2xl border bg-card px-2 py-2 shadow">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onTabChange('code')}
          className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition ${
            activeTab === 'code'
              ? 'bg-primary/10 text-foreground shadow'
              : 'text-muted-foreground hover:text-foreground'
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
              ? 'bg-primary/10 text-foreground shadow'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {previewStatusLabel && (
          <span className="inline-flex items-center gap-1 rounded-full border px-2 py-1 font-medium text-foreground">
            <Rocket className="h-3.5 w-3.5 text-primary" />
            {previewStatusLabel}
          </span>
        )}
        <label
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-semibold uppercase tracking-wide ${
            autoPreviewDisabled
              ? 'cursor-not-allowed text-muted-foreground/60'
              : 'cursor-pointer text-muted-foreground hover:border-primary/40'
          }`}
        >
          <input
            type="checkbox"
            className="h-3.5 w-3.5 rounded border bg-card text-primary focus:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
            checked={autoOpenPreview}
            disabled={autoPreviewDisabled}
            onChange={(event) => onAutoOpenPreviewChange?.(event.target.checked)}
          />
          Auto open preview
        </label>
      </div>
    </div>
  );
}
