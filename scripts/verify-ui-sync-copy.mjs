import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const files = ["index.html", "project-flow.html"];

for (const file of files) {
  const html = readFileSync(new URL(`../${file}`, import.meta.url), "utf8");

  assert.ok(!html.includes("试用剩 ${entitlement.daysLeft} 天"), `${file}: top bar should not show trial days`);
  assert.ok(!html.includes("隐藏 Done"), `${file}: hide-done button should use Chinese copy`);
  assert.ok(!html.includes("显示 Done"), `${file}: show-done button should use Chinese copy`);
  assert.ok(!html.includes('title="自动整理">⊞ 整理</button>'), `${file}: arrange button should be removed from the top bar`);
  assert.match(html, /<button className="btn btn-ghost acct-btn"[\s\S]*?>\s*Update Pro\s*<\/button>/, `${file}: account button should read Update Pro`);

  assert.match(html, /const contentHash=workspaceHash\(currentWorkspace\(\{lastCloudSavedAt:null,clientUpdatedAt:null\}\)\)/, `${file}: sync should compare stable content hash`);
  assert.match(html, /workspaceHash:contentHash/, `${file}: payload should store stable workspace hash`);
  assert.ok(!html.includes("data.workspaceHash!==lastSyncedHashRef.current"), `${file}: local save effect should not compare metadata-changing hash`);

  for (const theme of ["neumorphism", "claymorphism", "flat", "micro", "swiss", "spatial", "chaos", "editorial"]) {
    assert.ok(html.includes(`body[data-theme="${theme}"]`), `${file}: missing ${theme} theme tokens`);
  }
  assert.match(html, /body:not\(\[data-theme="dark"\]\) \.nc\.s-done\{[\s\S]*?#dcfce7,#bbf7d0/, `${file}: light themes should render Done nodes with a light-green surface`);
  assert.match(html, /body:not\(\[data-theme="dark"\]\) \.nc\.s-done \.ntitle,[\s\S]*?color:#166534/, `${file}: Done node text should remain green and readable`);
}

console.log("UI/sync copy verification passed.");
