// Improved PreviewFrame.tsx to enhance this component with more informative loading states.
import { WebContainer } from '@webcontainer/api';
import React, { useEffect, useState } from 'react';
import { Loader } from './Loader';

interface PreviewFrameProps {
  files: any[];
  webContainer: WebContainer;
}

export function PreviewFrame({ files, webContainer }: PreviewFrameProps) {
  const [url, setUrl] = useState("");
  const [loadingState, setLoadingState] = useState<'installing' | 'starting' | 'ready' | null>('installing');
  const [loadingLog, setLoadingLog] = useState<string[]>([]);

  async function main() {
    if (!webContainer) return;
    
    setLoadingState('installing');
    const installProcess = await webContainer.spawn('npm', ['install']);

    // Capture installation logs
    installProcess.output.pipeTo(new WritableStream({
      write(data) {
        console.log(data);
        setLoadingLog(prev => [...prev, data].slice(-5)); // Keep last 5 log entries
      }
    }));

    await installProcess.exit;
    
    setLoadingState('starting');
    await webContainer.spawn('npm', ['run', 'dev']);

    // Wait for `server-ready` event
    webContainer.on('server-ready', (port, url) => {
      console.log(url);
      console.log(port);
      setUrl(url);
      setLoadingState('ready');
    });
  }

  useEffect(() => {
    if (webContainer) {
      main();
    }
  }, [webContainer]);

  if (!url) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-900 rounded-lg p-6 text-gray-300">
        <Loader />
        <div className="mt-4 text-center">
          <p className="text-lg font-medium mb-2">
            {loadingState === 'installing' && 'Installing dependencies...'}
            {loadingState === 'starting' && 'Starting development server...'}
          </p>
          <div className="mt-4 max-w-md mx-auto">
            <div className="bg-gray-800 rounded-md p-3 text-left overflow-auto max-h-32 text-xs font-mono">
              {loadingLog.length > 0 ? (
                loadingLog.map((log, i) => <div key={i} className="mb-1">{log}</div>)
              ) : (
                <div className="text-gray-500">Waiting for output...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <iframe className="w-full h-full rounded-md border border-gray-700" src={url} />;
}
