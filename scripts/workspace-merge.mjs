function normalizeTitle(value) {
  return String(value || "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

function nodeStamp(node) {
  return Number(node?.updatedAt || node?.completedAt || node?.createdAt || 0);
}

function mergeNode(localNode, cloudNode, id, parentId) {
  const cloudIsNewer = nodeStamp(cloudNode) > nodeStamp(localNode);
  const newer = cloudIsNewer ? cloudNode : localNode;
  const older = cloudIsNewer ? localNode : cloudNode;
  const completedAt = Math.max(Number(localNode?.completedAt || 0), Number(cloudNode?.completedAt || 0)) || null;
  return {
    ...older,
    ...newer,
    id,
    parentId,
    status: localNode?.status === "done" || cloudNode?.status === "done" ? "done" : (newer?.status || "active"),
    completedAt,
    updatedAt: Math.max(nodeStamp(localNode), nodeStamp(cloudNode)),
  };
}

function nodeDepth(node, nodes, seen = new Set()) {
  if (!node?.parentId || seen.has(node.id)) return 0;
  seen.add(node.id);
  return 1 + nodeDepth(nodes[node.parentId], nodes, seen);
}

function semanticKey(parentId, title) {
  return `${parentId || "root"}|${normalizeTitle(title)}`;
}

export function mergeWorkspaceData(local = {}, cloud = {}) {
  const localNodes = local.nodes || {};
  const cloudNodes = cloud.nodes || {};
  const mergedNodes = Object.fromEntries(
    Object.entries(localNodes).map(([id, node]) => [id, { ...node, id }]),
  );
  const usedIds = new Set(Object.keys(mergedNodes));
  const localIds = new Set(Object.keys(mergedNodes));
  const matchedLocalIds = new Set();
  const cloudIdMap = new Map();
  const semanticIndex = new Map();

  for (const node of Object.values(mergedNodes)) {
    semanticIndex.set(semanticKey(node.parentId || null, node.title), node.id);
  }

  let nextNumericId = Math.max(
    0,
    ...Array.from(usedIds, (id) => Number(String(id).replace(/^n/, "")) || 0),
    ...Object.keys(cloudNodes).map((id) => Number(String(id).replace(/^n/, "")) || 0),
  ) + 1;
  const allocateId = () => {
    let id;
    do id = `n${nextNumericId++}`; while (usedIds.has(id));
    usedIds.add(id);
    return id;
  };

  let cloudAdded = 0;
  let mergedCount = 0;
  const orderedCloudNodes = Object.values(cloudNodes)
    .map((node) => ({ ...node, id: node.id || "" }))
    .sort((a, b) => nodeDepth(a, cloudNodes) - nodeDepth(b, cloudNodes));

  for (const cloudNode of orderedCloudNodes) {
    const mappedParent = cloudNode.parentId ? cloudIdMap.get(cloudNode.parentId) || null : null;
    const key = semanticKey(mappedParent, cloudNode.title);
    const semanticMatch = semanticIndex.get(key);
    const exactNode = mergedNodes[cloudNode.id];
    const exactMatches = exactNode
      && (
        semanticKey(exactNode.parentId || null, exactNode.title) === key
        || (exactNode.createdAt && cloudNode.createdAt && Number(exactNode.createdAt) === Number(cloudNode.createdAt))
      );

    if (semanticMatch || exactMatches) {
      const canonicalId = semanticMatch || cloudNode.id;
      mergedNodes[canonicalId] = mergeNode(mergedNodes[canonicalId], cloudNode, canonicalId, mappedParent);
      cloudIdMap.set(cloudNode.id, canonicalId);
      if (localIds.has(canonicalId)) matchedLocalIds.add(canonicalId);
      semanticIndex.set(key, canonicalId);
      mergedCount += 1;
      continue;
    }

    const canonicalId = usedIds.has(cloudNode.id) || !cloudNode.id ? allocateId() : cloudNode.id;
    usedIds.add(canonicalId);
    mergedNodes[canonicalId] = {
      ...cloudNode,
      id: canonicalId,
      parentId: mappedParent,
    };
    cloudIdMap.set(cloudNode.id, canonicalId);
    semanticIndex.set(key, canonicalId);
    cloudAdded += 1;
  }

  const mergeMappedValues = (localValues = {}, cloudValues = {}) => {
    const result = { ...localValues };
    for (const [cloudId, value] of Object.entries(cloudValues)) {
      const canonicalId = cloudIdMap.get(cloudId) || cloudId;
      if (result[canonicalId] === undefined) result[canonicalId] = value;
    }
    return result;
  };

  const localUpdatedAt = Number(local.clientUpdatedAt || 0);
  const cloudUpdatedAt = Number(cloud.clientUpdatedAt || cloud.lastCloudSavedAt || 0);
  const newestWorkspace = cloudUpdatedAt > localUpdatedAt ? cloud : local;
  const localOnly = Array.from(localIds).filter((id) => !matchedLocalIds.has(id)).length;
  const now = Date.now();
  const data = {
    ...newestWorkspace,
    nodes: mergedNodes,
    manPos: mergeMappedValues(local.manPos, cloud.manPos),
    laneOffsets: mergeMappedValues(local.laneOffsets, cloud.laneOffsets),
    selRoot: cloudIdMap.get(newestWorkspace.selRoot) || newestWorkspace.selRoot,
    clientUpdatedAt: now,
    workspaceHash: null,
  };

  if (!data.selRoot || !mergedNodes[data.selRoot]) {
    data.selRoot = Object.values(mergedNodes).find((node) => !node.parentId)?.id || null;
  }

  let message;
  if (cloudAdded && localOnly) {
    message = `已自动合并：从云端加入 ${cloudAdded} 项，并将本地 ${localOnly} 项更新同步到云端`;
  } else if (cloudAdded) {
    message = `已从云端更新 ${cloudAdded} 项`;
  } else if (localOnly) {
    message = `已将本地 ${localOnly} 项更新到云端`;
  } else {
    message = `已自动同步 ${mergedCount} 项更新`;
  }

  return {
    data,
    message,
    summary: { cloudAdded, localOnly, mergedCount },
  };
}
