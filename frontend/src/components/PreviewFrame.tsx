import { WebContainer, WebContainerProcess } from '@webcontainer/api';
import React, { useEffect, useMemo, useState } from 'react';
import { FileItem } from '../types';

interface PreviewFrameProps {
  files: FileItem[];
  webContainer?: WebContainer;
  isReady: boolean;
}

export function PreviewFrame({ files, webContainer, isReady }: PreviewFrameProps) {
  // Track preview lifecycle
  const [url, setUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'installing' | 'starting' | 'ready' | 'error'>('idle');
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

    const result = traverse(files);
    console.log('[Preview] packageJsonPath', result);
    return result;
  }, [files]);

  const hasPackageJson = Boolean(packageJsonPath);

  useEffect(() => {
    if (!webContainer || files.length === 0 || !isReady) {
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
              console.log(`[${label}]`, decoder.decode(data));
            }
          })
        )
        .catch(() => {
          /* ignore stream errors */
        });
    };

    const startPreview = async () => {
      if (!hasPackageJson) {
        setStatus('error');
        setError('Preview unavailable: generated files are missing package.json.');
        return;
      }

      // Ensure the virtual filesystem already contains the mounted project
      try {
        await webContainer.fs.readFile(packageJsonPath!, 'utf-8');
      } catch {
        setStatus('error');
        setError('Preview unavailable: package.json is not accessible in the workspace.');
        return;
      }

      setStatus('installing');
      setError(null);
      setUrl(null);

      try {
        const packageDir = packageJsonPath?.includes('/')
          ? packageJsonPath?.split('/').slice(0, -1).join('/')
          : '.';

        console.log('[Preview] package.json detected at', packageJsonPath, 'cwd', packageDir);

        installProcess = await webContainer.spawn(
          'npm',
          ['install'],
          packageDir === '.' ? undefined : { cwd: packageDir }
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
          packageDir === '.' ? undefined : { cwd: packageDir }
        );
        pipeProcessOutput(devProcess, 'dev');

        disposeServerReady = webContainer.on('server-ready', (_port, previewUrl) => {
          if (cancelled) {
            return;
          }
          setUrl(previewUrl);
          setStatus('ready');
        });

        devProcess.exit.then((code) => {
          if (!cancelled && code !== 0) {
            setError(`Preview server exited unexpectedly with code ${code}.`);
            setStatus('error');
            setUrl(null);
          }
        }).catch(() => {
          /* exit promise rejected when process killed; safe to ignore */
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
    };
  }, [webContainer, files, hasPackageJson, isReady, packageJsonPath]);

  const renderStatusMessage = () => {
    if (!isReady) {
      return 'Waiting for build steps to finish...';
    }
    if (error) {
      return error;
    }
    if (status === 'installing') {
      return 'Installing dependencies...';
    }
    if (status === 'starting') {
      return 'Starting development server...';
    }
    return 'Loading preview...';
  };

  return (
    <div className="h-full flex items-center justify-center text-gray-400">
      {!url && (
        <div className="text-center px-6">
          <p className="mb-2">{renderStatusMessage()}</p>
        </div>
      )}
      {url && <iframe width="100%" height="100%" src={url} />}
    </div>
  );
}
