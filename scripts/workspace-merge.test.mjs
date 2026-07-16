import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { mergeWorkspaceData } from "./workspace-merge.mjs";

const local = {
  clientUpdatedAt: 200,
  nodes: {
    n1: { id: "n1", title: "Launch", parentId: null, status: "active", createdAt: 1 },
    n2: { id: "n2", title: "Write copy", parentId: "n1", status: "active", createdAt: 2 },
  },
};

const cloud = {
  clientUpdatedAt: 100,
  nodes: {
    n1: { id: "n1", title: "Launch", parentId: null, status: "active", createdAt: 1 },
    n5: { id: "n5", title: "Write copy", parentId: "n1", status: "done", completedAt: 300, createdAt: 2 },
    n3: { id: "n3", title: "Publish", parentId: "n1", status: "active", createdAt: 3 },
    n2: { id: "n2", title: "Research", parentId: null, status: "active", createdAt: 4 },
  },
};

const result = mergeWorkspaceData(local, cloud);
const merged = result.data.nodes;

assert.equal(Object.values(merged).filter((node) => node.parentId === null && node.title === "Launch").length, 1);
assert.equal(Object.values(merged).find((node) => node.title === "Write copy").status, "done");
assert.equal(Object.values(merged).some((node) => node.title === "Publish"), true);
assert.equal(Object.values(merged).filter((node) => node.title === "Research").length, 1);
assert.equal(new Set(Object.keys(merged)).size, Object.keys(merged).length);
assert.match(result.message, /云端/);

const renamed = mergeWorkspaceData(
  { clientUpdatedAt: 300, nodes: { n1: { id: "n1", title: "Launch v2", parentId: null, createdAt: 1, updatedAt: 300 } } },
  { clientUpdatedAt: 100, nodes: { n1: { id: "n1", title: "Launch", parentId: null, createdAt: 1, updatedAt: 100 } } },
);
assert.equal(Object.keys(renamed.data.nodes).length, 1);
assert.equal(renamed.data.nodes.n1.title, "Launch v2");

const browserContext = { window: {} };
vm.runInNewContext(readFileSync(new URL("../workspace-merge.js", import.meta.url), "utf8"), browserContext);
const browserResult = browserContext.window.mergeWorkspaceData(local, cloud);
assert.deepEqual(
  JSON.parse(JSON.stringify(browserResult.summary)),
  result.summary,
  "browser merge implementation should match the tested module",
);
assert.deepEqual(
  Object.values(browserResult.data.nodes).map((node) => [node.title, node.parentId, node.status]).sort(),
  Object.values(result.data.nodes).map((node) => [node.title, node.parentId, node.status]).sort(),
);

console.log("Workspace merge verification passed.");
