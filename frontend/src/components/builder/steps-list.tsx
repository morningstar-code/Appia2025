'use client';

import { CheckCircle2, Loader2, PauseCircle, Sparkles } from "lucide-react";
import { Step, StepType } from "@/lib/builder/types";

interface StepsListProps {
  steps: Step[];
  currentStep: number | null;
  onStepClick?: (stepId: number) => void;
  collapsed?: boolean;
}

const stepTypeLabel: Record<StepType, string> = {
  [StepType.CreateFile]: "Create file",
  [StepType.CreateFolder]: "Create folder",
  [StepType.EditFile]: "Edit file",
  [StepType.DeleteFile]: "Remove file",
  [StepType.RunScript]: "Run command",
};

export function StepsList({ steps, currentStep, onStepClick, collapsed = false }: StepsListProps) {
  return (
    <section className="flex h-full flex-col gap-3">
      <header className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Plan
          </span>
          <h2 className="text-lg font-semibold">Build Timeline</h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          {steps.filter((step) => step.status === "completed").length}/{steps.length}
        </div>
      </header>
      {!collapsed && (
        <div className="flex-1 overflow-y-auto pr-1">
          <div className="space-y-2">
            {steps.map((step) => {
              const isActive = currentStep === step.id;
              const statusIcon =
                step.status === "completed" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : step.status === "in-progress" ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : (
                  <PauseCircle className="h-4 w-4 text-muted-foreground" />
                );

              return (
                <button
                  key={step.id}
                  type="button"
                  onClick={() => onStepClick?.(step.id)}
                  className={`w-full rounded-2xl border px-3 py-2 text-left transition ${
                    isActive
                      ? "border-primary/30 bg-primary/10 text-foreground shadow"
                      : "border-border bg-card text-foreground hover:border-primary/20 hover:bg-card/80"
                  }`}
                >
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {statusIcon}
                    <span className="truncate">{step.title}</span>
                  </div>
                  <div className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
                    {stepTypeLabel[step.type]}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
