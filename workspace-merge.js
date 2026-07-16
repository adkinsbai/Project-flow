(function (root) {
  function normalizeTitle(value) {
    return String(value || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
  }
  function stamp(node) {
    return Number(node && (node.updatedAt || node.completedAt || node.createdAt) || 0);
  }
  function key(parentId, title) {
    return (parentId || 'root') + '|' + normalizeTitle(title);
  }
  function mergeNode(localNode, cloudNode, id, parentId) {
    var cloudNewer = stamp(cloudNode) > stamp(localNode);
    var newer = cloudNewer ? cloudNode : localNode;
    var older = cloudNewer ? localNode : cloudNode;
    var completedAt = Math.max(Number(localNode && localNode.completedAt || 0), Number(cloudNode && cloudNode.completedAt || 0)) || null;
    return Object.assign({}, older, newer, {
      id: id,
      parentId: parentId,
      status: (localNode && localNode.status === 'done') || (cloudNode && cloudNode.status === 'done') ? 'done' : (newer && newer.status || 'active'),
      completedAt: completedAt,
      updatedAt: Math.max(stamp(localNode), stamp(cloudNode))
    });
  }
  function depth(node, nodes, seen) {
    seen = seen || {};
    if (!node || !node.parentId || seen[node.id]) return 0;
    seen[node.id] = true;
    return 1 + depth(nodes[node.parentId], nodes, seen);
  }
  function mergeWorkspaceData(local, cloud) {
    local = local || {}; cloud = cloud || {};
    var localNodes = local.nodes || {}, cloudNodes = cloud.nodes || {};
    var merged = {};
    Object.keys(localNodes).forEach(function (id) { merged[id] = Object.assign({}, localNodes[id], { id: id }); });
    var used = {}, localIds = {}, matched = {}, semantic = {}, cloudMap = {};
    Object.keys(merged).forEach(function (id) { used[id] = true; localIds[id] = true; semantic[key(merged[id].parentId || null, merged[id].title)] = id; });
    var nextId = 1;
    Object.keys(used).concat(Object.keys(cloudNodes)).forEach(function (id) {
      var n = Number(String(id).replace(/^n/, '')); if (n >= nextId) nextId = n + 1;
    });
    function allocate() { var id; do { id = 'n' + nextId++; } while (used[id]); used[id] = true; return id; }
    var cloudList = Object.keys(cloudNodes).map(function (id) { return Object.assign({}, cloudNodes[id], { id: cloudNodes[id].id || id }); });
    cloudList.sort(function (a, b) { return depth(a, cloudNodes) - depth(b, cloudNodes); });
    var cloudAdded = 0, mergedCount = 0;
    cloudList.forEach(function (node) {
      var parentId = node.parentId ? (cloudMap[node.parentId] || null) : null;
      var semanticMatch = semantic[key(parentId, node.title)];
      var exactNode = merged[node.id];
      var exact = exactNode && (key(exactNode.parentId || null, exactNode.title) === key(parentId, node.title)
        || (exactNode.createdAt && node.createdAt && Number(exactNode.createdAt) === Number(node.createdAt)));
      if (semanticMatch || exact) {
        var canonical = semanticMatch || node.id;
        merged[canonical] = mergeNode(merged[canonical], node, canonical, parentId);
        cloudMap[node.id] = canonical; semantic[key(parentId, node.title)] = canonical;
        if (localIds[canonical]) matched[canonical] = true;
        mergedCount++; return;
      }
      var id = used[node.id] ? allocate() : node.id; used[id] = true;
      merged[id] = Object.assign({}, node, { id: id, parentId: parentId });
      cloudMap[node.id] = id; semantic[key(parentId, node.title)] = id; cloudAdded++;
    });
    function mappedValues(localValues, cloudValues) {
      var out = Object.assign({}, localValues || {});
      Object.keys(cloudValues || {}).forEach(function (id) { var mapped = cloudMap[id] || id; if (out[mapped] === undefined) out[mapped] = cloudValues[id]; });
      return out;
    }
    var newest = Number(cloud.clientUpdatedAt || cloud.lastCloudSavedAt || 0) > Number(local.clientUpdatedAt || 0) ? cloud : local;
    var localOnly = Object.keys(localIds).filter(function (id) { return !matched[id]; }).length;
    var data = Object.assign({}, newest, {
      nodes: merged,
      manPos: mappedValues(local.manPos, cloud.manPos),
      laneOffsets: mappedValues(local.laneOffsets, cloud.laneOffsets),
      selRoot: cloudMap[newest.selRoot] || newest.selRoot || null,
      clientUpdatedAt: Date.now(),
      workspaceHash: null
    });
    if (!data.selRoot || !merged[data.selRoot]) {
      var roots = Object.keys(merged).filter(function (id) { return !merged[id].parentId; });
      data.selRoot = roots[0] || null;
    }
    var message;
    if (cloudAdded && localOnly) message = '已自动合并：从云端加入 ' + cloudAdded + ' 项，并将本地 ' + localOnly + ' 项更新同步到云端';
    else if (cloudAdded) message = '已从云端更新 ' + cloudAdded + ' 项';
    else if (localOnly) message = '已将本地 ' + localOnly + ' 项更新到云端';
    else message = '已自动同步 ' + mergedCount + ' 项更新';
    return { data: data, message: message, summary: { cloudAdded: cloudAdded, localOnly: localOnly, mergedCount: mergedCount } };
  }
  root.mergeWorkspaceData = mergeWorkspaceData;
})(window);
