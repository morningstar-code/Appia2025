'use client';

import { WebContainer, WebContainerProcess } from "@webcontainer/api";
import { useEffect, useMemo, useState } from "react";
import { Globe2, PlugZap, RefreshCcwDot, RotateCcw } from "lucide-react";
import { FileItem } from "@/lib/builder/types";

export type PreviewStatus = 'idle' | 'installing' | 'starting' | 'ready' | 'error' | 'waiting';

interface PreviewFrameProps {
  files: FileItem[];
  webContainer?: WebContainer;
  isReady: boolean;
  onStatusChange?: (status: PreviewStatus) => void;
  onLog?: (line: string) => void;
}

export const PREVIEW_STATUS_LABELS: Record<PreviewStatus, string> = {
  idle: 'Idle',
  waiting: 'Waiting for files',
  installing: 'Installing dependencies',
  starting: 'Starting dev server',
  ready: 'Live preview ready',
  error: 'Preview unavailable',
};

export function PreviewFrame({ files, webContainer, isReady, onStatusChange, onLog }: PreviewFrameProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<PreviewStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [runToken, setRunToken] = useState(0);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  const packageJsonPath = useMemo(() => {
    const traverse = (items: FileItem[]): string | null => {
      for (const item of items) {
        if (item.type === 'file' && item.name === 'package.json') {
          return item.path;
        }
        if (item.type === 'folder' && item.children) {
          const result = traverse(item.children);
          if (result) {
            return result;
          }
        }
      }
      return null;
    };

    return traverse(files);
  }, [files]);

  const hasPackageJson = Boolean(packageJsonPath);

  useEffect(() => {
    onStatusChange?.(status);
  }, [status, onStatusChange]);

  useEffect(() => {
    if (!webContainer || files.length === 0 || !isReady) {
      setStatus(isReady ? 'waiting' : 'idle');
      return;
    }

    let cancelled = false;
    let disposeServerReady: (() => void) | undefined;
    let installProcess: WebContainerProcess | undefined;
    let devProcess: WebContainerProcess | undefined;

    const pipeProcessOutput = (process: WebContainerProcess, label: string) => {
      const decoder = new TextDecoder();
      (process.output as unknown as ReadableStream<Uint8Array>)
        .pipeTo(
          new WritableStream<Uint8Array>({
            write(data) {
              const text = decoder.decode(data);
              onLog?.(`[preview:${label}] ${text.trim()}`);
            },
          }),
        )
        .catch(() => {
          /* ignore stream errors */
        });
    };

    const startPreview = async () => {
      if (!hasPackageJson) {
        setStatus('error');
        setError('Preview unavailable: package.json was not found in the generated files.');
        return;
      }

      let packageJsonRaw: string | null = null;
      try {
        packageJsonRaw = await webContainer.fs.readFile(packageJsonPath!, 'utf-8');
      } catch {
        setStatus('error');
        setError('Preview unavailable: package.json is not accessible within the workspace.');
        return;
      }

      let packageJson: Record<string, unknown> = {};
      try {
        packageJson = packageJsonRaw ? JSON.parse(packageJsonRaw) : {};
      } catch {
        /* ignore parse error, handled below */
      }

      const scripts =
        packageJson &&
        typeof packageJson === 'object' &&
        packageJson !== null &&
        typeof (packageJson as { scripts?: unknown }).scripts === 'object'
          ? ((packageJson as { scripts?: Record<string, string> }).scripts ?? {})
          : {};

      const preferredScripts = ['dev', 'start', 'preview'];
      const selectedScript = preferredScripts.find((name) => typeof scripts?.[name] === 'string') ?? null;

      if (!selectedScript) {
        setStatus('error');
        setError('Preview unavailable: package.json is missing a dev/start script.');
        return;
      }

      const scriptCommand = scripts?.[selectedScript] ?? '';
      const needsHostArgs =
        selectedScript === 'dev' && typeof scriptCommand === 'string' && /vite|next|svelte-kit/i.test(scriptCommand);

      setStatus('installing');
      setError(null);
      setUrl(null);
      setHasLoadedOnce(false);

      try {
        const packageDir = packageJsonPath?.includes('/')
          ? packageJsonPath?.split('/').slice(0, -1).join('/')
          : '.';

        installProcess = await webContainer.spawn(
          'npm',
          ['install'],
          packageDir === '.' ? undefined : { cwd: packageDir },
        );
        pipeProcessOutput(installProcess, 'install');
        const installExitCode = await installProcess.exit;
        if (cancelled) {
          return;
        }
        if (installExitCode !== 0) {
          throw new Error(`npm install failed with exit code ${installExitCode}`);
        }

        setStatus('starting');
        const runArgs = needsHostArgs
          ? ['run', selectedScript, '--', '--host', '0.0.0.0', '--port', '5173']
          : ['run', selectedScript];

        devProcess = await webContainer.spawn(
          'npm',
          runArgs,
          packageDir === '.' ? undefined : { cwd: packageDir },
        );
        pipeProcessOutput(devProcess, 'dev');

        disposeServerReady = webContainer.on('server-ready', (_port, previewUrl) => {
          if (cancelled) {
            return;
          }
          setUrl(previewUrl);
          setStatus('ready');
        });

        devProcess.exit
          .then((code) => {
            if (!cancelled && code !== 0) {
              setError(`Preview server exited with code ${code}.`);
              setStatus('error');
              setUrl(null);
            }
          })
          .catch(() => {
            /* exit promise rejected when process killed; ignore */
          });
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setError(message);
          setStatus('error');
          setUrl(null);
        }
      }
    };

    startPreview();

    return () => {
      cancelled = true;
      disposeServerReady?.();
      installProcess?.kill();
      devProcess?.kill();
      setUrl(null);
      setStatus('idle');
    };
  }, [webContainer, files, hasPackageJson, isReady, packageJsonPath, runToken, onLog]);

  useEffect(() => {
    if (status === 'ready' && url && !hasLoadedOnce) {
      const fallback = setTimeout(() => {
        if (!hasLoadedOnce) {
          setStatus('error');
          setError('Preview loaded but no content rendered. Try restarting.');
        }
      }, 8000);
      return () => clearTimeout(fallback);
    }
  }, [status, url, hasLoadedOnce]);

  const handleReload = () => {
    setRunToken((prev) => prev + 1);
    setStatus('installing');
    setError(null);
    setUrl(null);
    setHasLoadedOnce(false);
  };

  return (
    <div className="flex h-full flex-col gap-4 rounded-2xl border bg-card p-4 shadow">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Globe2 className="h-4 w-4 text-primary" />
          Live Preview
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
              status === 'ready'
                ? 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200'
                : status === 'error'
                ? 'border-rose-400/40 bg-rose-500/10 text-rose-200'
                : 'border-border bg-card text-muted-foreground'
            }`}
          >
            <RefreshCcwDot className="h-3.5 w-3.5" />
            {PREVIEW_STATUS_LABELS[status]}
          </span>
          <button
            type="button"
            onClick={handleReload}
            className="inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:border-primary/40 hover:text-foreground"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Restart preview
          </button>
        </div>
      </header>

      <div className="relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl border bg-gradient-to-br from-card to-muted">
        {!url ? (
          <div className="flex flex-col items-center gap-3 text-center text-sm text-muted-foreground">
            <PlugZap className="h-6 w-6 text-primary" />
            <span>{error ?? PREVIEW_STATUS_LABELS[status]}</span>
            {!isReady && <span className="text-xs text-muted-foreground/80">Waiting for build steps…</span>}
          </div>
        ) : (
          <iframe
            title="Appia preview"
            src={url}
            className="h-full w-full overflow-hidden rounded-[28px] border bg-white"
            onLoad={() => setHasLoadedOnce(true)}
          />
        )}
      </div>
    </div>
  );
}
