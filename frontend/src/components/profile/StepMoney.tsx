import type { InvestmentGoal, RiskAppetite } from "../../api/types";
import { goalUsesGrowth } from "./formState";
import { ChoiceGroup, Field, FieldGroup, MoneyInput, inputClass } from "./fields";
import type { StepProps } from "./ProfileWizard";

export function StepMoney({ form, update, errors, options }: StepProps) {
  const goal = options.goals.find((g) => g.value === form.goal);
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="budget_min_inr" label="Minimum budget" optional error={errors.budget_min_inr}>
          <MoneyInput
            id="budget_min_inr"
            value={form.budgetMin}
            onChange={(budgetMin) => update({ budgetMin })}
            invalid={Boolean(errors.budget_min_inr)}
          />
        </Field>
        <Field id="budget_max_inr" label="Maximum budget" error={errors.budget_max_inr}>
          <MoneyInput
            id="budget_max_inr"
            value={form.budgetMax}
            onChange={(budgetMax) => update({ budgetMax })}
            invalid={Boolean(errors.budget_max_inr)}
            placeholder="e.g. 80"
          />
        </Field>
      </div>

      <FieldGroup id="goal" label="Investment goal" error={errors.goal}>
        <ChoiceGroup
          name="goal"
          value={form.goal}
          choices={options.goals.map((g) => ({
            value: g.value as InvestmentGoal,
            label: g.label,
            description: `Target compared with ${g.measure_label.charAt(0).toLowerCase()}${g.measure_label.slice(1)}`,
          }))}
          onChange={(value) => update({ goal: value })}
        />
      </FieldGroup>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="target_roi_pct"
          label="Target ROI (% a year)"
          error={errors.target_roi_pct}
          hint={goal ? `Compared with ${goal.measure_label.toLowerCase()}.` : "Choose a goal first."}
        >
          <input
            id="target_roi_pct"
            inputMode="decimal"
            value={form.targetRoi}
            onChange={(e) => update({ targetRoi: e.target.value })}
            aria-invalid={Boolean(errors.target_roi_pct)}
            aria-describedby="target_roi_pct-msg"
            className={inputClass(Boolean(errors.target_roi_pct))}
          />
        </Field>
        {goalUsesGrowth(form.goal, options) && (
          <Field
            id="expected_growth_pct"
            label="Expected price growth (% a year)"
            optional
            error={errors.expected_growth_pct}
            hint="Leave blank to use the locality's past 12-month price change, when search results provide it."
          >
            <input
              id="expected_growth_pct"
              inputMode="decimal"
              value={form.expectedGrowth}
              onChange={(e) => update({ expectedGrowth: e.target.value })}
              aria-invalid={Boolean(errors.expected_growth_pct)}
              aria-describedby="expected_growth_pct-msg"
              className={inputClass(Boolean(errors.expected_growth_pct))}
            />
          </Field>
        )}
      </div>

      <FieldGroup id="risk_appetite" label="Risk appetite" error={errors.risk_appetite}>
        <ChoiceGroup
          name="risk_appetite"
          value={form.riskAppetite}
          choices={options.risk_levels.map((r) => ({ value: r.value as RiskAppetite, label: r.label }))}
          onChange={(value) => update({ riskAppetite: value })}
        />
      </FieldGroup>
    </div>
  );
}
