import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError, describeError } from "../api/client";
import type { components } from "../api/schema";
import { Notice } from "./Notice";

type State = components["schemas"]["AuthState"];
export function useAccount() {
  return useQuery({ queryKey: ["auth"], queryFn: () => apiFetch<State>("/auth/state"), retry: false, refetchInterval: 60_000 });
}

export function AccountGate({ children }: { children: ReactNode }) {
  const query = useAccount();
  const cache = useQueryClient();
  const identity = query.data ? (query.data.enabled ? query.data.user?.id ?? "signed-out" : "local") : undefined;
  const [acceptedIdentity, setAcceptedIdentity] = useState<string | null>(null);
  useEffect(() => {
    if (identity === undefined) return;
    const privateQueries = { predicate: (q: { queryKey: readonly unknown[] }) => q.queryKey[0] !== "auth" };
    let active = true;
    void cache.cancelQueries(privateQueries).then(() => {
      if (!active) return;
      cache.removeQueries(privateQueries);
      setAcceptedIdentity(identity);
    });
    return () => { active = false; };
  }, [cache, identity]);
  useEffect(() => {
    const expire = () => { cache.removeQueries({ predicate: q => q.queryKey[0] !== "auth" }); cache.setQueryData<State>(["auth"], { enabled: true, user: null }); };
    window.addEventListener("realty-auth-expired", expire);
    return () => window.removeEventListener("realty-auth-expired", expire);
  }, [cache]);
  if (query.error) return <div className="m-8"><Notice tone="error">{describeError(query.error)}</Notice></div>;
  if (!query.data) return <p className="m-8 text-sm text-slate-500">Connecting…</p>;
  if (query.data.enabled && !query.data.user) return <AccountForm />;
  if (acceptedIdentity !== identity) return <p className="m-8 text-sm text-slate-500">Loading your workspace…</p>;
  return children;
}

export function AccountForm() {
  const cache = useQueryClient();
  const [register, setRegister] = useState(false);
  const action = useMutation({ mutationFn: (data: { username: string; password: string }) => apiFetch<State>(register ? "/auth/register" : "/auth/login", {
    method: "POST", body: JSON.stringify(data),
  }), onSuccess: state => { cache.clear(); cache.setQueryData(["auth"], state); } });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    action.mutate({ username: String(data.get("username")), password: String(data.get("password")) });
  }
  return <main className="mx-auto mt-16 max-w-md space-y-5 rounded-xl border bg-white p-6">
    <h1 className="text-2xl font-semibold">Realty Intel · {register ? "Create account" : "Sign in"}</h1>
    <p className="text-sm text-slate-600">Your profiles, saved notes, alerts and portfolio belong to your account.</p>
    <form onSubmit={submit} className="space-y-4">
      <label className="block text-sm">Username<input name="username" required minLength={3} maxLength={40} pattern="[a-zA-Z0-9_]+" autoComplete="username" className="mt-1 w-full rounded-md border p-2" /></label>
      <label className="block text-sm">Password (12–128 characters)<input name="password" type="password" required minLength={12} maxLength={128} autoComplete={register ? "new-password" : "current-password"} className="mt-1 w-full rounded-md border p-2" /></label>
      {action.error && <Notice tone="error">{action.error instanceof ApiError ? Object.values(action.error.fieldErrors).join("; ") || action.error.message : describeError(action.error)}</Notice>}
      <button disabled={action.isPending} className="w-full rounded-md bg-slate-900 p-2 text-sm text-white">{action.isPending ? "Please wait…" : register ? "Create account" : "Sign in"}</button>
    </form>
    <button className="text-sm underline" onClick={() => { setRegister(v => !v); action.reset(); }}>{register ? "Already registered? Sign in" : "Create a new account"}</button>
  </main>;
}

export function AccountMenu() {
  const account = useAccount();
  const cache = useQueryClient();
  const logout = useMutation({ mutationFn: () => apiFetch<State>("/auth/logout", { method: "POST" }),
    onSuccess: state => { cache.clear(); cache.setQueryData(["auth"], state); } });
  if (!account.data?.enabled || !account.data.user) return null;
  return <div className="text-xs"><span>{account.data.user.username}</span> <button disabled={logout.isPending} className="underline" onClick={() => logout.mutate()}>Sign out</button>
    {logout.error && <span className="text-red-700">{describeError(logout.error)}</span>}
  </div>;
}
