import assert from "node:assert/strict";
const base = process.env.TEST_SITE_URL || "http://127.0.0.1:3000";
if (!["127.0.0.1", "localhost"].includes(new URL(base).hostname))
  throw new Error("Smoke tests are local-only");
for (const [path, text] of [
  ["/", "Ваш сервер."],
  ["/dashboard", "Всё важное"],
  ["/privacy", "О ваших данных."],
]) {
  const response = await fetch(new URL(path, base));
  assert.equal(response.status, 200, path);
  assert.ok(
    (await response.text()).includes(text),
    `Expected content at ${path}`,
  );
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  console.log(`OK ${path}: server render + security headers`);
}
const guild = "123456789012345678";
for (const path of ["/api/guilds", `/api/guilds/${guild}/settings`]) {
  const response = await fetch(new URL(path, base));
  assert.equal(response.status, 401, path);
  assert.equal(response.headers.get("cache-control"), "no-store");
  console.log(`OK ${path}: no anonymous access`);
}
const csrf = await fetch(new URL(`/api/guilds/${guild}/settings`, base), {
  method: "PUT",
  headers: {
    "Content-Type": "application/json",
    Origin: "https://untrusted.example",
  },
  body: "{}",
});
assert.equal(csrf.status, 403);
console.log("OK settings: cross-origin mutation rejected");
const logout = await fetch(new URL("/api/auth/logout", base), {
  method: "POST",
  headers: { Origin: "https://untrusted.example" },
  redirect: "manual",
});
assert.equal(logout.status, 403);
console.log("OK logout: cross-origin mutation rejected");
const og = await fetch(new URL("/opengraph-image", base));
assert.equal(og.status, 200);
assert.ok(og.headers.get("content-type").includes("image/png"));
console.log("OK social preview image");
const robots = await fetch(new URL("/robots.txt", base));
assert.ok((await robots.text()).includes("Disallow: /dashboard"));
console.log("OK dashboard not indexed");
