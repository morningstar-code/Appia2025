import React from 'react';
import Editor from '@monaco-editor/react';
import { FileItem } from '../types';
import { FileText, Sparkles } from 'lucide-react';

interface CodeEditorProps {
  file: FileItem | null;
  readOnly?: boolean;
}

export function CodeEditor({ file, readOnly = true }: CodeEditorProps) {
  if (!file) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-appia-border/60 bg-appia-surface/40 text-center text-sm text-appia-muted">
        <div className="flex flex-col items-center gap-2">
          <Sparkles className="h-5 w-5 text-appia-accent" />
          <span>Select a file to inspect the generated code.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-appia-border/70 bg-appia-surface/90 shadow-appia-card">
      <div className="flex items-center justify-between border-b border-appia-border/70 px-4 py-2.5">
        <div className="flex items-center gap-2 text-sm font-medium text-appia-foreground/90">
          <FileText className="h-4 w-4 text-appia-accent" />
          <span className="truncate">{file.path}</span>
        </div>
        <span className="rounded-md border border-appia-border/60 bg-appia-surface px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-appia-muted">
          Read only
        </span>
      </div>
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          defaultLanguage="typescript"
          theme="vs-dark"
          value={file.content || ''}
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            fontFamily: '"JetBrains Mono", "Fira Code", ui-monospace',
            smoothScrolling: true,
          }}
        />
      </div>
    </div>
  );
}
