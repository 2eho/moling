'use client';

import { useState, useCallback, type ReactNode } from 'react';
import styles from './ImportWizard.module.css';

/* ── Types ── */

export interface WizardStep {
  id: string;
  label: string;
  icon?: string;
  content: ReactNode;
  canProceed?: boolean;
  onNext?: () => Promise<void> | void;
  onBack?: () => void;
}

export interface ImportWizardProps {
  steps: WizardStep[];
  currentStep: number;
  onStepChange?: (stepIndex: number) => void;
  onComplete?: () => void;
  showStepIndicator?: boolean;
  showNavigation?: boolean;
  nextLabel?: string;
  backLabel?: string;
  completeLabel?: string;
}

/* ── Component ── */

export default function ImportWizard({
  steps,
  currentStep,
  onStepChange,
  onComplete,
  showStepIndicator = true,
  showNavigation = true,
  nextLabel = '下一步',
  backLabel = '上一步',
  completeLabel = '完成',
}: ImportWizardProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  const currentStepData = steps[currentStep];

  const canProceed = currentStepData?.canProceed ?? true;

  const goToNext = useCallback(async () => {
    if (isProcessing || !canProceed) return;

    setIsProcessing(true);
    try {
      if (currentStepData?.onNext) {
        await currentStepData.onNext();
      }

      if (currentStep < steps.length - 1) {
        const nextStep = currentStep + 1;
        onStepChange?.(nextStep);
      } else {
        onComplete?.();
      }
    } catch (err) {
      console.error('向导步骤执行失败:', err);
    } finally {
      setIsProcessing(false);
    }
  }, [isProcessing, canProceed, currentStepData, currentStep, steps.length, onStepChange, onComplete]);

  const goToPrev = useCallback(() => {
    if (isProcessing || currentStep === 0) return;

    if (currentStepData?.onBack) {
      currentStepData.onBack();
    }

    onStepChange?.(currentStep - 1);
  }, [isProcessing, currentStep, currentStepData, onStepChange]);

  const goToStep = useCallback((stepIndex: number) => {
    if (isProcessing || stepIndex === currentStep) return;
    onStepChange?.(stepIndex);
  }, [isProcessing, currentStep, onStepChange]);

  return (
    <div className={styles.wizardShell}>
      {/* Step Indicator */}
      {showStepIndicator && (
        <div className={styles.stepIndicator}>
          {steps.map((step, index) => (
            <span key={step.id} style={{ display: 'contents' }}>
              <div
                className={`${styles.stepNode} ${
                  index === currentStep ? styles.stepNodeActive : ''
                } ${index < currentStep ? styles.stepNodeDone : ''} ${index > currentStep ? styles.stepNodePending : ''}`}
                onClick={() => {
                  if (index < currentStep) goToStep(index);
                }}
              >
                <div className={styles.stepCircle}>
                  {index < currentStep ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </div>
                <span className={styles.stepLabel}>{step.label}</span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`${styles.stepConnector} ${
                    index < currentStep ? styles.stepConnectorDone : ''
                  }`}
                />
              )}
            </span>
          ))}
        </div>
      )}

      {/* Step Content */}
      <div className={styles.stepContent}>
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={`${styles.stepPanel} ${index === currentStep ? styles.stepPanelVisible : ''}`}
          >
            {step.content}
          </div>
        ))}
      </div>

      {/* Navigation */}
      {showNavigation && (
        <div className={styles.navigation}>
          <div className={styles.navLeft}>
            {currentStep > 0 && (
              <button
                className={styles.backButton}
                onClick={goToPrev}
                disabled={isProcessing}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
                {backLabel}
              </button>
            )}
          </div>
          <div className={styles.navRight}>
            <button
              className={styles.nextButton}
              onClick={goToNext}
              disabled={isProcessing || !canProceed}
            >
              {isProcessing ? (
                <>
                  <div className={styles.buttonSpinner} />
                  处理中...
                </>
              ) : currentStep < steps.length - 1 ? (
                <>
                  {nextLabel}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </>
              ) : (
                <>
                  {completeLabel}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
