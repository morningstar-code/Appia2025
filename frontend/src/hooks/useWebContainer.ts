import { useEffect, useState } from "react";
import { WebContainer } from '@webcontainer/api';

export interface WebContainerState {
  instance?: WebContainer;
  error?: unknown;
  isBooting: boolean;
}

export function useWebContainer(): WebContainerState {
  const [state, setState] = useState<WebContainerState>({
    instance: undefined,
    error: undefined,
    isBooting: true,
  });

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      try {
        console.log('[WebContainer] booting');
        const instance = await WebContainer.boot();
        if (!cancelled) {
          console.log('[WebContainer] boot complete');
          setState({ instance, error: undefined, isBooting: false });
        }
      } catch (err) {
        console.error('[WebContainer] boot failed', err);
        if (!cancelled) {
          setState({ instance: undefined, error: err, isBooting: false });
        }
      }
    };
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
