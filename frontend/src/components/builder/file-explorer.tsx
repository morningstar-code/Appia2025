'use client';

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, File, FolderTree, Search, Sparkles } from "lucide-react";
import { FileItem } from "@/lib/builder/types";

interface FileExplorerProps {
  files: FileItem[];
  onFileSelect: (file: FileItem) => void;
  activePath?: string | null;
  title?: string;
}

interface FileNodeProps {
  item: FileItem;
  depth: number;
  onFileClick: (file: FileItem) => void;
  activePath?: string | null;
  autoExpand?: boolean;
}

function filterTree(items: FileItem[], query: string): FileItem[] {
  if (!query) {
    return items;
  }
  const q = query.toLowerCase();

  const filterNode = (node: FileItem): FileItem | null => {
    if (node.type === "folder") {
      const children = (node.children ?? [])
        .map(filterNode)
        .filter(Boolean) as FileItem[];
      if (
        children.length > 0 ||
        node.name.toLowerCase().includes(q) ||
        node.path.toLowerCase().includes(q)
      ) {
        return {
          ...node,
          children,
        };
      }
      return null;
    }

    if (node.name.toLowerCase().includes(q) || node.path.toLowerCase().includes(q)) {
      return { ...node };
    }

    return null;
  };

  return items.map(filterNode).filter(Boolean) as FileItem[];
}

function FileNode({ item, depth, onFileClick, activePath, autoExpand = false }: FileNodeProps) {
  const [isExpanded, setIsExpanded] = useState(autoExpand);
  const isActive = item.type === "file" && activePath === item.path;

  const toggle = () => {
    if (item.type === "folder") {
      setIsExpanded((prev) => !prev);
    } else {
      onFileClick(item);
    }
  };

  return (
    <div className="select-none">
      <button
        type="button"
        onClick={toggle}
        className={`flex w-full items-center gap-2 rounded-lg border border-transparent px-2 py-1.5 text-left text-sm transition ${
          isActive
            ? "bg-primary/10 text-foreground shadow"
            : "text-foreground/80 hover:border-border hover:bg-card"
        }`}
        style={{ paddingLeft: `${Math.max(depth - 1, 0) * 1.25 + 0.75}rem` }}
      >
        {item.type === "folder" && (
          <span className="text-muted-foreground">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </span>
        )}
        {item.type === "folder" ? (
          <FolderTree className="h-4 w-4 text-muted-foreground" />
        ) : (
          <File className="h-4 w-4 text-primary" />
        )}
        <span className="truncate text-sm">{item.name}</span>
        {item.type === "file" && (
          <span className="ml-auto text-[10px] uppercase text-muted-foreground">
            {item.name.split(".").pop()}
          </span>
        )}
      </button>
      {item.type === "folder" && isExpanded && item.children && (
        <div className="pl-3">
          {item.children.map((child) => (
            <FileNode
              key={child.path}
              item={child}
              depth={depth + 1}
              onFileClick={onFileClick}
              activePath={activePath}
              autoExpand={autoExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileExplorer({ files, onFileSelect, activePath, title = "Workspace" }: FileExplorerProps) {
  const [query, setQuery] = useState("");
  const filteredFiles = useMemo(() => filterTree(files, query), [files, query]);

  return (
    <aside className="flex h-full flex-col gap-4">
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Files
          </span>
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          Live
        </div>
      </div>

      <label className="relative">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search files…"
          className="w-full rounded-2xl border bg-surface py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
      </label>

      <div className="flex-1 overflow-y-auto pr-1">
        {filteredFiles.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed bg-muted/40 px-6 text-center text-sm text-muted-foreground">
            {query ? "No matching files" : "Generated files will appear here once Appia creates them."}
          </div>
        ) : (
          <div className="space-y-1 text-sm">
            {filteredFiles.map((item) => (
              <FileNode
                key={item.path}
                item={item}
                depth={0}
                onFileClick={onFileSelect}
                activePath={activePath}
                autoExpand={Boolean(query)}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
