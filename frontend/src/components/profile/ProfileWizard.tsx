import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { ApiError, describeError } from "../../api/client";
import type { InvestorProfileIn, ProfileOptions } from "../../api/types";
import { Notice } from "../Notice";
import {
  FORM_TO_API,
  STEPS,
  firstStepWithError,
  toPayload,
  validateAll,
  validateStep,
  type FieldErrors,
  type ProfileFormState,
} from "./formState";
import { StepMoney } from "./StepMoney";
import { StepWhat } from "./StepWhat";
import { StepWhere } from "./StepWhere";
import { LanguagePrefill } from "./LanguagePrefill";

export interface StepProps {
  form: ProfileFormState;
  update: (patch: Partial<ProfileFormState>) => void;
  errors: FieldErrors;
  options: ProfileOptions;
}

const STEP_COMPONENTS = [StepWhat, StepWhere, StepMoney];

interface ProfileWizardProps {
  options: ProfileOptions;
  initial: ProfileFormState;
  submitLabel: string;
  onSubmit: (payload: InvestorProfileIn) => Promise<unknown>;
}

/** Three steps (What → Where → Money); checks each step before moving on, saves at the end. */
export function ProfileWizard({ options, initial, submitLabel, onSubmit }: ProfileWizardProps) {
  const [form, setForm] = useState(initial);
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const isLast = step === STEPS.length - 1;

  const update = (patch: Partial<ProfileFormState>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors((current) => {
      const next = { ...current };
      for (const key of Object.keys(patch) as (keyof ProfileFormState)[]) delete next[FORM_TO_API[key]];
      return next;
    });
  };

  const showErrors = (found: FieldErrors) => {
    setErrors(found);
    const target = firstStepWithError(found);
    if (target !== -1) setStep(target);
  };

  const next = () => {
    const found = validateStep(step, form, options);
    if (Object.keys(found).length > 0) return setErrors(found);
    setStep(step + 1);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!isLast) return next();
    const found = validateAll(form, options);
    if (Object.keys(found).length > 0) return showErrors(found);
    setFormError(null);
    setSaving(true);
    try {
      await onSubmit(toPayload(form, options));
    } catch (error) {
      const fieldErrors = error instanceof ApiError ? (error.fieldErrors as FieldErrors) : {};
      if (Object.keys(fieldErrors).length > 0) showErrors(fieldErrors);
      else setFormError(describeError(error));
    } finally {
      setSaving(false);
    }
  };

  const CurrentStep = STEP_COMPONENTS[step];
  return (
    <form onSubmit={submit} noValidate className="space-y-6">
      <LanguagePrefill city={options.city} apply={update} />
      <WizardSteps current={step} errors={errors} onSelect={(target) => target < step && setStep(target)} />
      {formError && <Notice tone="error">{formError}</Notice>}
      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <CurrentStep form={form} update={update} errors={errors} options={options} />
      </section>
      <div className="flex items-center justify-between">
        <Link to="/" className="text-sm text-slate-600 hover:underline">
          Cancel
        </Link>
        <div className="flex gap-2">
          {step > 0 && (
            <button
              type="button"
              onClick={() => setStep(step - 1)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
            >
              Back
            </button>
          )}
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {isLast ? (saving ? "Saving…" : submitLabel) : "Next"}
          </button>
        </div>
      </div>
    </form>
  );
}

/** Step indicator. Earlier steps are clickable; steps with errors are marked. */
function WizardSteps(props: { current: number; errors: FieldErrors; onSelect: (step: number) => void }) {
  return (
    <ol className="flex gap-2">
      {STEPS.map((step, index) => {
        const hasError = step.fields.some((field) => props.errors[field]);
        const state =
          index === props.current
            ? "bg-slate-900 text-white"
            : index < props.current
              ? "bg-slate-200 text-slate-800"
              : "bg-slate-100 text-slate-400";
        return (
          <li key={step.title} className="flex-1">
            <button
              type="button"
              onClick={() => props.onSelect(index)}
              aria-current={index === props.current ? "step" : undefined}
              className={`w-full rounded-md px-3 py-2 text-left text-sm font-medium ${state} ${hasError ? "ring-2 ring-red-400" : ""}`}
            >
              {index + 1}. {step.title}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
