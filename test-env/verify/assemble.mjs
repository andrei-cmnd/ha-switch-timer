// Combine <REPORT_DIR>/<mode>.json files into <REPORT_DIR>/report.md.
import fs from "node:fs";

const OUT = process.env.REPORT_DIR ?? "/report";
const MODES = [
  ["first-install", "First install (you add the hub and the cards)"],
  ["provisioned", "Provisioned (hub and dashboard added on first start)"],
];

const runs = MODES.filter(([mode]) => fs.existsSync(`${OUT}/${mode}.json`)).map(([mode, title]) => ({
  title,
  ...JSON.parse(fs.readFileSync(`${OUT}/${mode}.json`, "utf8")),
}));
const all = runs.flatMap((r) => r.results);
const passed = all.filter((r) => r.ok).length;
const esc = (s) => String(s).replace(/\|/g, "\\|");

let md = `# Switch Timer — test environment verification\n\n`;
md += `**${passed === all.length ? "PASS" : "FAIL"}**: ${passed}/${all.length} checks passed`;
md += ` · generated ${new Date().toISOString()}\n\n`;
md += `Environment: \`scripts/test-env\` (official \`ghcr.io/home-assistant/home-assistant\` image with the integration and built card), `;
md += `checked with Playwright ${process.env.PLAYWRIGHT_VERSION ?? ""} / Firefox from the official Playwright image.\n`;
for (const run of runs) {
  const ok = run.results.filter((r) => r.ok).length;
  md += `\n## ${run.title}\n\n`;
  md += `Home Assistant ${run.haVersion ?? "?"} · card \`${run.cardUrl ? new URL(run.cardUrl).pathname + new URL(run.cardUrl).search : "not loaded on the last page"}\` · ${ok}/${run.results.length} passed\n\n`;
  md += `| | Check | Details |\n|---|---|---|\n`;
  for (const r of run.results) md += `| ${r.ok ? "✅" : "❌"} | ${esc(r.title)} | ${esc(r.detail)} |\n`;
  if (run.shots.length) {
    md += `\n### Screenshots\n\n`;
    for (const s of run.shots) md += `**${esc(s.caption)}**\n\n![${esc(s.caption)}](${s.file})\n\n`;
  }
}
fs.writeFileSync(`${OUT}/report.md`, md);
console.log(`report: ${OUT}/report.md (${passed}/${all.length} passed)`);
