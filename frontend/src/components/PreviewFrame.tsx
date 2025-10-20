import { WebContainer, WebContainerProcess } from '@webcontainer/api';
import React, { useEffect, useMemo, useState } from 'react';
import { Globe2, PlugZap, RefreshCcwDot } from 'lucide-react';
import { FileItem } from '../types';

export type PreviewStatus = 'idle' | 'installing' | 'starting' | 'ready' | 'error' | 'waiting';

interface PreviewFrameProps {
  files: FileItem[];
  webContainer?: WebContainer;
  isReady: boolean;
  onStatusChange?: (status: PreviewStatus) => void;
}

export const PREVIEW_STATUS_LABELS: Record<PreviewStatus, string> = {
  idle: 'Idle',
  waiting: 'Waiting for files',
  installing: 'Installing dependencies',
  starting: 'Starting dev server',
  ready: 'Live preview ready',
  error: 'Preview unavailable',
};

export function PreviewFrame({
  files,
  webContainer,
  isReady,
  onStatusChange,
}: PreviewFrameProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<PreviewStatus>('idle');
  const [error, setError] = useState<string | null>(null);

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
      process.output
        .pipeTo(
          new WritableStream({
            write(data) {
              console.log(`[Preview:${label}]`, decoder.decode(data));
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

      try {
        await webContainer.fs.readFile(packageJsonPath!, 'utf-8');
      } catch {
        setStatus('error');
        setError('Preview unavailable: package.json is not accessible within the workspace.');
        return;
      }

      setStatus('installing');
      setError(null);
      setUrl(null);

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
        devProcess = await webContainer.spawn(
          'npm',
          ['run', 'dev', '--', '--host', '0.0.0.0', '--port', '5173'],
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
  }, [webContainer, files, hasPackageJson, isReady, packageJsonPath]);

  return (
    <div className="flex h-full flex-col gap-4 rounded-2xl border border-appia-border/70 bg-appia-surface/90 p-4 shadow-appia-card">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-appia-foreground/90">
          <Globe2 className="h-4 w-4 text-appia-accent" />
          Live Preview
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
            status === 'ready'
              ? 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200'
              : status === 'error'
              ? 'border-rose-400/40 bg-rose-500/10 text-rose-200'
              : 'border-appia-border/70 bg-appia-surface text-appia-muted'
          }`}
        >
          <RefreshCcwDot className="h-3.5 w-3.5" />
          {PREVIEW_STATUS_LABELS[status]}
        </span>
      </header>

      <div className="relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl border border-appia-border/70 bg-gradient-to-br from-appia-surface to-appia-sunken">
        {!url ? (
          <div className="flex flex-col items-center gap-3 text-center text-sm text-appia-muted">
            <PlugZap className="h-6 w-6 text-appia-accent" />
            <span>{error ?? PREVIEW_STATUS_LABELS[status]}</span>
            {!isReady && <span className="text-xs text-appia-muted/80">Waiting for build steps…</span>}
          </div>
        ) : (
          <iframe
            title="Appia preview"
            src={url}
            className="h-full w-full overflow-hidden rounded-[28px] border border-appia-border/40 bg-white"
          />
        )}
      </div>
    </div>
  );
}
