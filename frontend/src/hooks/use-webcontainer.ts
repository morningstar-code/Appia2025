'use client';

import { useEffect, useState } from "react";
import { WebContainer } from "@webcontainer/api";

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
        const instance = await WebContainer.boot();
        if (!cancelled) {
          setState({ instance, error: undefined, isBooting: false });
        }
      } catch (err) {
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
