import { Check } from 'lucide-react';
import { Step } from '../types';

interface StepIndicatorProps {
  currentStep: Step;
}

const STEPS = [
  { num: 1, label: 'Upload Image' },
  { num: 2, label: 'Upload Audio' },
  { num: 3, label: 'Adjust' },
  { num: 4, label: 'Export' },
] as const;

export default function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2">
      {STEPS.map((step, index) => {
        const isComplete = step.num < currentStep;
        const isCurrent = step.num === currentStep;
        
        return (
          <div key={step.num} className="flex items-center">
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                  isComplete
                    ? 'bg-accent text-white'
                    : isCurrent
                    ? 'bg-accent text-white'
                    : 'bg-surface-200 text-surface-500'
                }`}
              >
                {isComplete ? (
                  <Check className="w-4 h-4" />
                ) : (
                  step.num
                )}
              </div>
              <span
                className={`text-sm hidden sm:block ${
                  isCurrent ? 'text-surface-900 font-medium' : 'text-surface-500'
                }`}
              >
                {step.label}
              </span>
            </div>
            
            {index < STEPS.length - 1 && (
              <div
                className={`w-12 h-0.5 mx-3 ${
                  step.num < currentStep ? 'bg-accent' : 'bg-surface-200'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

