import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const output = fileURLToPath(new URL("../out/", import.meta.url));
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
for (const page of ["index.html", "dashboard/index.html", "invite/index.html", "privacy/index.html", "404.html"]) {
  const html = await readFile(resolve(output, page), "utf8");
  assert.match(html, /<html[^>]*lang="ru"/);
  assert.ok(!html.includes("/api/auth/login"), "Static pages must not offer a broken login");
  for (const match of html.matchAll(/(?:src|href)="([^"#?]+)(?:[?#][^"]*)?"/g)) {
    const url = match[1];
    if (!url.startsWith("/")) continue;
    assert.ok(url.startsWith(`${basePath}/`), `Missing basePath: ${url}`);
    const asset = decodeURIComponent(url.slice(basePath.length + 1));
    assert.ok((await stat(resolve(output, asset))).isFile() || (await stat(resolve(output, asset, "index.html"))).isFile(), `Missing asset: ${url}`);
  }
}
assert.match(await readFile(resolve(output, "dashboard/index.html"), "utf8"), /Панель — следующий шаг/);
await assert.rejects(stat(resolve(output, "api")), { code: "ENOENT" });
await assert.rejects(stat(resolve(output, ".env.local")), { code: "ENOENT" });
await stat(resolve(output, ".nojekyll"));
console.log("Pages smoke checks passed: pages, basePath, assets, no server API or .env");
