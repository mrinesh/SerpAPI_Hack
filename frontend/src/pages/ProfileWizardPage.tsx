import { useNavigate, useParams } from "react-router";

import { describeError } from "../api/client";
import {
  useCreateProfile,
  useProfile,
  useProfileOptions,
  useUpdateProfile,
} from "../api/hooks";
import type { InvestorProfileIn } from "../api/types";
import { Notice } from "../components/Notice";
import { ProfileWizard } from "../components/profile/ProfileWizard";
import { emptyForm, formFromProfile } from "../components/profile/formState";

/** Create (/profiles/new) or edit (/profiles/:profileId/edit) an investor profile (F-01). */
export function ProfileWizardPage() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const options = useProfileOptions();
  const profile = useProfile(profileId);
  const create = useCreateProfile();
  const update = useUpdateProfile(profileId ?? "");

  const editing = profileId !== undefined;
  const error = options.error ?? (editing ? profile.error : null);
  if (error) return <Notice tone="error">{describeError(error)}</Notice>;
  if (!options.data || (editing && !profile.data)) return <p className="text-sm text-slate-500">Loading…</p>;

  const save = async (payload: InvestorProfileIn) => {
    await (editing ? update : create).mutateAsync(payload);
    navigate("/");
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">{editing ? "Edit profile" : "New profile"}</h1>
      <ProfileWizard
        key={profileId ?? "new"}
        options={options.data}
        initial={profile.data ? formFromProfile(profile.data) : emptyForm()}
        submitLabel={editing ? "Save changes" : "Save profile"}
        onSubmit={save}
      />
    </div>
  );
}
