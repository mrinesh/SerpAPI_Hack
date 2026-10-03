/** Form controls for the profile wizard. Labels, hints and errors are wired for screen readers. */

import { useState, type KeyboardEvent, type ReactNode } from "react";

import { UNIT_LABEL, type MoneyUnit } from "../../lib/money";
import type { MoneyValue } from "./formState";

export const inputClass = (invalid: boolean) =>
  `w-full rounded-md border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 ${
    invalid ? "border-red-500 focus:ring-red-200" : "border-slate-300 focus:ring-slate-300"
  }`;

interface FieldProps {
  id: string;
  label: string;
  hint?: ReactNode;
  error?: string;
  optional?: boolean;
  children: ReactNode;
}

/** One labelled control. The control inside must use `id`. */
export function Field({ id, label, hint, error, optional, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-800">
        {label} {optional && <span className="font-normal text-slate-400">(optional)</span>}
      </label>
      {children}
      <FieldMessage id={id} hint={hint} error={error} />
    </div>
  );
}

/** A group of choices (radios or checkboxes) with a legend. */
export function FieldGroup({ id, label, hint, error, optional, children }: FieldProps) {
  return (
    <fieldset className="space-y-1.5" aria-describedby={`${id}-msg`}>
      <legend className="text-sm font-medium text-slate-800">
        {label} {optional && <span className="font-normal text-slate-400">(optional)</span>}
      </legend>
      {children}
      <FieldMessage id={id} hint={hint} error={error} />
    </fieldset>
  );
}

function FieldMessage({ id, hint, error }: { id: string; hint?: ReactNode; error?: string }) {
  if (error)
    return (
      <p id={`${id}-msg`} role="alert" className="text-xs text-red-600">
        {error}
      </p>
    );
  if (hint)
    return (
      <p id={`${id}-msg`} className="text-xs text-slate-500">
        {hint}
      </p>
    );
  return null;
}

interface Choice<T extends string> {
  value: T;
  label: string;
  description?: string;
}

const choiceClass = (selected: boolean, disabled = false) =>
  `flex cursor-pointer flex-col rounded-lg border p-3 text-sm transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-slate-400 ${
    selected
      ? "border-slate-900 bg-slate-900 text-white"
      : disabled
        ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
        : "border-slate-300 bg-white hover:border-slate-500"
  }`;

/** Pick exactly one. */
export function ChoiceGroup<T extends string>(props: {
  name: string;
  value: T | "";
  choices: Choice<T>[];
  onChange: (value: T) => void;
  columns?: string;
}) {
  return (
    <div className={`grid gap-2 ${props.columns ?? "sm:grid-cols-3"}`}>
      {props.choices.map((choice) => (
        <label key={choice.value} className={choiceClass(props.value === choice.value)}>
          <input
            type="radio"
            name={props.name}
            value={choice.value}
            checked={props.value === choice.value}
            onChange={() => props.onChange(choice.value)}
            className="sr-only"
          />
          <span className="font-medium">{choice.label}</span>
          {choice.description && (
            <span className="mt-1 text-xs opacity-80">{choice.description}</span>
          )}
        </label>
      ))}
    </div>
  );
}

/** Pick any number, up to `max`. */
export function MultiChoice<T extends string>(props: {
  values: T[];
  choices: Choice<T>[];
  onChange: (values: T[]) => void;
  max?: number;
  columns?: string;
}) {
  const full = props.max !== undefined && props.values.length >= props.max;
  const toggle = (value: T) =>
    props.onChange(
      props.values.includes(value)
        ? props.values.filter((v) => v !== value)
        : [...props.values, value],
    );
  return (
    <div className={`grid gap-2 ${props.columns ?? "sm:grid-cols-2"}`}>
      {props.choices.map((choice) => {
        const selected = props.values.includes(choice.value);
        const disabled = full && !selected;
        return (
          <label key={choice.value} className={choiceClass(selected, disabled)}>
            <input
              type="checkbox"
              checked={selected}
              disabled={disabled}
              onChange={() => toggle(choice.value)}
              className="sr-only"
            />
            <span className="font-medium">{choice.label}</span>
          </label>
        );
      })}
    </div>
  );
}

/** An amount plus a Lakh / Crore unit. */
export function MoneyInput(props: {
  id: string;
  value: MoneyValue;
  onChange: (value: MoneyValue) => void;
  invalid: boolean;
  placeholder?: string;
}) {
  return (
    <div className="flex gap-2">
      <span className="flex items-center text-sm text-slate-500">₹</span>
      <input
        id={props.id}
        inputMode="decimal"
        value={props.value.amount}
        placeholder={props.placeholder}
        onChange={(e) => props.onChange({ ...props.value, amount: e.target.value })}
        aria-invalid={props.invalid}
        aria-describedby={`${props.id}-msg`}
        className={inputClass(props.invalid)}
      />
      <select
        aria-label="Unit"
        value={props.value.unit}
        onChange={(e) => props.onChange({ ...props.value, unit: e.target.value as MoneyUnit })}
        className="rounded-md border border-slate-300 bg-white px-2 text-sm"
      >
        {(Object.keys(UNIT_LABEL) as MoneyUnit[]).map((unit) => (
          <option key={unit} value={unit}>
            {UNIT_LABEL[unit]}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Free-text tags: type, press Enter (or Add), remove with ×. */
export function ChipInput(props: {
  id: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  max: number;
  invalid: boolean;
}) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const text = draft.trim();
    const duplicate = props.values.some((v) => v.toLowerCase() === text.toLowerCase());
    if (text && !duplicate && props.values.length < props.max) props.onChange([...props.values, text]);
    setDraft("");
  };
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    }
  };
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          id={props.id}
          value={draft}
          placeholder={props.placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={props.values.length >= props.max}
          aria-invalid={props.invalid}
          aria-describedby={`${props.id}-msg`}
          className={inputClass(props.invalid)}
        />
        <button
          type="button"
          onClick={add}
          className="rounded-md border border-slate-300 px-3 text-sm hover:bg-slate-100"
        >
          Add
        </button>
      </div>
      {props.values.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {props.values.map((value) => (
            <li
              key={value}
              className="flex items-center gap-1 rounded-full bg-slate-100 py-1 pr-1 pl-3 text-sm"
            >
              {value}
              <button
                type="button"
                aria-label={`Remove ${value}`}
                onClick={() => props.onChange(props.values.filter((v) => v !== value))}
                className="rounded-full px-1.5 text-slate-500 hover:bg-slate-200"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
