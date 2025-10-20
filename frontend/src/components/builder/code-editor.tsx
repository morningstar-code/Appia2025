'use client';

import Editor from "@monaco-editor/react";
import { FileItem } from "@/lib/builder/types";
import { Sparkles, FileText } from "lucide-react";

interface CodeEditorProps {
  file: FileItem | null;
}

export function CodeEditor({ file }: CodeEditorProps) {
  if (!file) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl border border-dashed bg-muted/30 text-sm text-muted-foreground">
        <div className="flex flex-col items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <span>Select a file to inspect the generated code.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border bg-card shadow">
      <header className="flex items-center justify-between border-b px-4 py-2.5">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FileText className="h-4 w-4 text-primary" />
          <span className="truncate">{file.path}</span>
        </div>
        <span className="rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Read only
        </span>
      </header>
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          defaultLanguage="typescript"
          theme="vs-dark"
          value={file.content || ""}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: "on",
            scrollBeyondLastLine: false,
            smoothScrolling: true,
          }}
        />
      </div>
    </div>
  );
}
