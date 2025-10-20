'use client';

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BuilderRoot } from "@/components/builder/builder-root";

function BuilderPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const prompt = searchParams.get('prompt');

  useEffect(() => {
    if (!prompt) {
      router.replace('/');
    }
  }, [prompt, router]);

  if (!prompt) {
    return null;
  }

  return (
    <div className="px-6 py-6">
      <BuilderRoot prompt={prompt} />
    </div>
  );
}

export default function BuilderPage() {
  return (
    <Suspense fallback={<div className="px-6 py-6 text-muted-foreground">Loading builder…</div>}>
      <BuilderPageInner />
    </Suspense>
  );
}
