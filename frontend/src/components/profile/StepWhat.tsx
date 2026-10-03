import type { PropertyType, Segment } from "../../api/types";
import { ChoiceGroup, Field, FieldGroup, MultiChoice, inputClass } from "./fields";
import type { StepProps } from "./ProfileWizard";

export function StepWhat({ form, update, errors, options }: StepProps) {
  const segment = options.segments.find((s) => s.value === form.segment);
  const changeSegment = (value: Segment) => {
    // Property types and the business type belong to one segment, so they reset with it.
    if (value !== form.segment) update({ segment: value, propertyTypes: [], businessType: "" });
  };
  return (
    <div className="space-y-6">
      <Field id="name" label="Profile name" error={errors.name}>
        <input
          id="name"
          value={form.name}
          onChange={(e) => update({ name: e.target.value })}
          placeholder="e.g. Rental income, East Bengaluru"
          maxLength={80}
          aria-invalid={Boolean(errors.name)}
          aria-describedby="name-msg"
          className={inputClass(Boolean(errors.name))}
        />
      </Field>

      <FieldGroup id="segment" label="Residential or commercial?" error={errors.segment}>
        <ChoiceGroup
          name="segment"
          value={form.segment}
          choices={options.segments.map((s) => ({ value: s.value as Segment, label: s.label }))}
          onChange={changeSegment}
          columns="grid-cols-2"
        />
      </FieldGroup>

      <FieldGroup
        id="property_types"
        label="Property types"
        error={errors.property_types}
        hint={segment ? "Choose one or more." : "Choose residential or commercial first."}
      >
        {segment && (
          <MultiChoice
            values={form.propertyTypes}
            choices={segment.property_types.map((t) => ({
              value: t.value as PropertyType,
              label: t.label,
            }))}
            onChange={(propertyTypes) => update({ propertyTypes })}
          />
        )}
      </FieldGroup>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="size_min_sqft" label="Minimum size (sq ft)" optional error={errors.size_min_sqft}>
          <input
            id="size_min_sqft"
            inputMode="numeric"
            value={form.sizeMin}
            onChange={(e) => update({ sizeMin: e.target.value })}
            aria-invalid={Boolean(errors.size_min_sqft)}
            aria-describedby="size_min_sqft-msg"
            className={inputClass(Boolean(errors.size_min_sqft))}
          />
        </Field>
        <Field id="size_max_sqft" label="Maximum size (sq ft)" optional error={errors.size_max_sqft}>
          <input
            id="size_max_sqft"
            inputMode="numeric"
            value={form.sizeMax}
            onChange={(e) => update({ sizeMax: e.target.value })}
            aria-invalid={Boolean(errors.size_max_sqft)}
            aria-describedby="size_max_sqft-msg"
            className={inputClass(Boolean(errors.size_max_sqft))}
          />
        </Field>
      </div>

      {form.segment === "commercial" && (
        <Field
          id="business_type"
          label="Business type"
          error={errors.business_type}
          hint="Pick a suggestion or type your own. Used to find nearby competitors."
        >
          <input
            id="business_type"
            list="business-type-suggestions"
            value={form.businessType}
            onChange={(e) => update({ businessType: e.target.value })}
            maxLength={60}
            aria-invalid={Boolean(errors.business_type)}
            aria-describedby="business_type-msg"
            className={inputClass(Boolean(errors.business_type))}
          />
          <datalist id="business-type-suggestions">
            {options.business_type_suggestions.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </Field>
      )}
    </div>
  );
}
