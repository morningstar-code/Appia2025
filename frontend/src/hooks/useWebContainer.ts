import { useEffect, useState } from "react";
import { WebContainer } from '@webcontainer/api';

export function useWebContainer() {
  const [webcontainer, setWebcontainer] = useState<WebContainer>();
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      try {
        console.log('[WebContainer] booting');
        const instance = await WebContainer.boot();
        if (!cancelled) {
          console.log('[WebContainer] boot complete');
          setWebcontainer(instance);
        }
      } catch (err) {
        console.error('[WebContainer] boot failed', err);
        if (!cancelled) {
          setError(err);
        }
      }
    };
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    console.error('[WebContainer] unavailable, returning undefined');
  }

  return webcontainer;
}
