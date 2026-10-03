import { Placeholder } from "../components/Placeholder";

export function OnboardingPage() {
  return (
    <Placeholder title="New search" features={["F-01"]}>
      <p>
        Investor profile form: residential or commercial, property types, Bengaluru localities,
        budget (lakhs / crores), size, bedrooms, target yield, risk appetite, goal, and for
        commercial the business category used for competitor analysis.
      </p>
      <p>Submitting saves the profile and starts a pipeline run, then opens the run page.</p>
    </Placeholder>
  );
}
