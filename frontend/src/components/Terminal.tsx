import React from 'react';
import { Terminal as TerminalIcon } from 'lucide-react';

interface TerminalProps {
  logs: string[];
}

export function Terminal({ logs }: TerminalProps) {
  return (
    <div className="h-full bg-gray-950 rounded-lg border border-gray-700 overflow-hidden flex flex-col">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700 flex items-center gap-2">
        <TerminalIcon className="w-4 h-4 text-gray-400" />
        <span className="text-sm text-gray-300">Terminal</span>
      </div>
      <div className="flex-1 overflow-auto p-4 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="text-gray-500">Waiting for commands...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="text-gray-300 mb-1">
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

