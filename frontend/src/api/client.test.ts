import { afterEach, expect, it, vi } from "vitest";
import { apiFetch } from "./client";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it("sends cookie-based CSRF and same-origin credentials for writes", async () => {
  vi.stubGlobal("document", { cookie: "realty_csrf=signed-csrf-token" });
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  await apiFetch("/profiles", { method: "POST", body: "{}" });
  expect(fetch).toHaveBeenCalledWith("/api/profiles", expect.objectContaining({ credentials: "same-origin",
    headers: expect.objectContaining({ "X-CSRF-Token": "signed-csrf-token" }) }));
});

it("notifies the account gate when a private session expires", async () => {
  const dispatchEvent = vi.fn();
  vi.stubGlobal("window", { dispatchEvent });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "unauthorized", message: "Sign in" } }), { status: 401 })));
  await expect(apiFetch("/profiles")).rejects.toMatchObject({ code: "unauthorized" });
  expect(dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({ type: "realty-auth-expired" }));
});
