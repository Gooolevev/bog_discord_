// Build an isolated public site, preserving the working server/OAuth application.
// Never copy .env files into the staging directory or the published artifact.
import { cp, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const staging = await mkdtemp(join(tmpdir(), "kontur-pages-"));
try {
  for (const name of ["app", "components", "lib", "public", "package.json", "tsconfig.json", "next.config.ts", "postcss.config.mjs"]) {
    await cp(join(root, name), join(staging, name), {
      recursive: true,
      filter: (source) => !["app/api", "app/dashboard", "app/invite"].some(
        (excluded) => source === join(root, excluded),
      ),
    });
  }
  await symlink(join(root, "node_modules"), join(staging, "node_modules"), "dir");
  for (const page of ["dashboard", "invite", "privacy"]) {
    await mkdir(join(staging, "app", page), { recursive: true });
    await cp(join(root, "static-pages", `${page}.tsx`), join(staging, "app", page, "page.tsx"));
  }
  // Metadata routes must explicitly opt into prerendering with output: export.
  for (const route of ["robots.ts", "opengraph-image.tsx"]) {
    const path = join(staging, "app", route);
    await writeFile(path, `export const dynamic = "force-static";\n${await readFile(path, "utf8")}`);
  }
  const result = spawnSync(process.execPath, [join(root, "node_modules/next/dist/bin/next"), "build", "--webpack"], {
    cwd: staging,
    stdio: "inherit",
    env: { ...process.env, STATIC_SITE: "1", NEXT_TELEMETRY_DISABLED: "1" },
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Static build failed (${result.status})`);
  // Replace the previous export only after a successful build.
  await rm(join(root, "out"), { recursive: true, force: true });
  await cp(join(staging, "out"), join(root, "out"), { recursive: true });
  await writeFile(join(root, "out", ".nojekyll"), "");
  console.log("GitHub Pages site exported to website/out");
} finally {
  await rm(staging, { recursive: true, force: true });
}
