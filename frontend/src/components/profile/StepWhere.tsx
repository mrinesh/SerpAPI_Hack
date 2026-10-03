import { ChipInput, Field, FieldGroup, MultiChoice } from "./fields";
import type { StepProps } from "./ProfileWizard";

const MAX_MUST_HAVES = 10; // matches the API limit

export function StepWhere({ form, update, errors, options }: StepProps) {
  const max = options.max_localities;
  return (
    <div className="space-y-6">
      <FieldGroup
        id="localities"
        label={`Localities in ${options.city}`}
        error={errors.localities ?? errors.city}
        hint={`${form.localities.length} of ${max} selected. Each new locality costs searches for area data, so pick the ones you'd really buy in.`}
      >
        <MultiChoice
          values={form.localities}
          choices={options.localities.map((l) => ({ value: l.slug, label: l.name }))}
          onChange={(localities) => update({ localities })}
          max={max}
          columns="grid-cols-2 sm:grid-cols-3"
        />
        <p className="text-xs text-slate-400">Source: {options.locality_source}</p>
      </FieldGroup>

      <Field
        id="must_haves"
        label="Must-haves"
        optional
        error={errors.must_haves}
        hint="Things a property must have, e.g. near metro, gated community. The AI checks each listing against them."
      >
        <ChipInput
          id="must_haves"
          values={form.mustHaves}
          onChange={(mustHaves) => update({ mustHaves })}
          placeholder="Type one and press Enter"
          max={MAX_MUST_HAVES}
          invalid={Boolean(errors.must_haves)}
        />
      </Field>
    </div>
  );
}
