import React from 'react';
import { CheckCircle2, Loader2, PauseCircle, Sparkles } from 'lucide-react';
import { Step, StepType } from '../types';

interface StepsListProps {
  steps: Step[];
  currentStep: number | null;
  onStepClick?: (stepId: number) => void;
  collapsed?: boolean;
}

const stepTypeLabel: Record<StepType, string> = {
  [StepType.CreateFile]: 'Create file',
  [StepType.CreateFolder]: 'Create folder',
  [StepType.EditFile]: 'Edit file',
  [StepType.DeleteFile]: 'Remove file',
  [StepType.RunScript]: 'Run command',
};

export function StepsList({
  steps,
  currentStep,
  onStepClick,
  collapsed = false,
}: StepsListProps) {
  return (
    <section className="flex flex-col gap-3 rounded-3xl border border-appia-border/70 bg-appia-surface/90 p-4 shadow-appia-card">
      <header className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-appia-muted">
            Plan
          </span>
          <h2 className="text-lg font-semibold text-appia-foreground">
            Build Timeline
          </h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-appia-border/80 bg-appia-surface px-3 py-1 text-xs text-appia-muted">
          <Sparkles className="h-3.5 w-3.5 text-appia-accent" />
          {steps.filter((step) => step.status === 'completed').length}/
          {steps.length}
        </div>
      </header>

      {!collapsed && (
        <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
          {steps.map((step) => {
            const isActive = currentStep === step.id;
            const statusIcon =
              step.status === 'completed' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : step.status === 'in-progress' ? (
                <Loader2 className="h-4 w-4 animate-spin text-appia-accent" />
              ) : (
                <PauseCircle className="h-4 w-4 text-appia-muted" />
              );

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => onStepClick?.(step.id)}
                className={`w-full rounded-2xl border px-3 py-2 text-left transition ${
                  isActive
                    ? 'border-appia-accent/30 bg-appia-accent-soft/80 text-appia-foreground shadow-appia-glow'
                    : 'border-appia-border/70 bg-appia-surface/70 text-appia-foreground/85 hover:border-appia-border hover:bg-appia-surface'
                }`}
              >
                <div className="flex items-center gap-2 text-sm font-medium">
                  {statusIcon}
                  <span className="truncate">{step.title}</span>
                </div>
                <div className="mt-1 text-xs uppercase tracking-wide text-appia-muted">
                  {stepTypeLabel[step.type]}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
