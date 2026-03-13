import { useMemo, useState, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { motion } from "framer-motion";
import { getImpact } from "../services/api";

const EXT_COLORS = {
  py: "#3572A5", js: "#F7DF1E", ts: "#3178C6",
  jsx: "#61DAFB", tsx: "#3178C6", rb: "#CC342D",
  go: "#00ADD8", rs: "#DEA584", java: "#ED8B00",
};

const EXT_BG = {
  py: "rgba(53,114,165,0.18)", js: "rgba(247,223,30,0.12)",
  ts: "rgba(49,120,198,0.18)", jsx: "rgba(97,218,251,0.12)",
  tsx: "rgba(49,120,198,0.18)", rb: "rgba(204,52,45,0.18)",
  go: "rgba(0,173,216,0.12)", rs: "rgba(222,165,132,0.12)",
  java: "rgba(237,139,0,0.12)",
};

const EXT_LABELS = {
  py: "Python", js: "JavaScript", ts: "TypeScript",
  jsx: "React JSX", tsx: "React TSX", rb: "Ruby",
  go: "Go", rs: "Rust", java: "Java",
};

/* ──────── Node Component ──────── */
function CustomNode({ data }) {
  const fullPath = data.label;
  const filename = fullPath.split("/").pop();
  const ext = filename.split(".").pop();
  const isAffected = data.isAffected;
  const isSelected = data.isSelected;
  const connections = data.connections || 0;
  const isCore = connections >= 3;

  const color = isAffected ? "#EF4444" : isSelected ? "#F59E0B" : (EXT_COLORS[ext] || "#6366f1");
  const bg = isAffected ? "rgba(239,68,68,0.15)" : isSelected ? "rgba(245,158,11,0.15)" : (EXT_BG[ext] || "rgba(17,24,39,0.95)");
  const langLabel = EXT_LABELS[ext] || ext;

  // Scale node size based on connections (responsive)
  const scale = Math.min(1 + connections * 0.04, 1.4);
  const basePad = 8 + Math.min(connections, 10);

  return (
    <div
      title={fullPath}
      style={{
        minWidth: "110px",
        maxWidth: "180px",
        borderRadius: "10px",
        padding: `${basePad}px ${basePad + 4}px`,
        textAlign: "center",
        background: bg,
        border: isCore ? `2px solid ${color}` : `1.5px solid ${color}80`,
        boxShadow: isSelected
          ? `0 0 24px ${color}60`
          : isCore
            ? `0 0 16px ${color}30`
            : "0 2px 6px rgba(0,0,0,0.25)",
        cursor: "pointer",
        transform: `scale(${scale})`,
        transition: "box-shadow 0.25s ease, transform 0.25s ease, border-color 0.25s ease",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color, width: 6, height: 6, border: "none" }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "5px", marginBottom: "3px" }}>
        <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: color, flexShrink: 0 }} />
        {isCore && (
          <span style={{
            fontSize: "7px", background: `${color}25`, color,
            padding: "1px 5px", borderRadius: "3px", fontWeight: 700,
            letterSpacing: "0.04em", border: `1px solid ${color}40`,
          }}>CORE</span>
        )}
      </div>
      <div style={{
        fontSize: "11px", fontWeight: 700, color: "#f1f5f9",
        wordBreak: "break-word", lineHeight: 1.25,
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        {filename}
      </div>
      <div style={{ fontSize: "9px", color: "#64748b", marginTop: "2px" }}>
        {langLabel} · {connections} conn.
      </div>
      {isAffected && (
        <div style={{
          fontSize: "7px", color: "#EF4444", fontWeight: 700, marginTop: "2px",
          background: "rgba(239,68,68,0.12)", padding: "1px 5px", borderRadius: "3px",
          display: "inline-block",
        }}>AFFECTED</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 6, height: 6, border: "none" }} />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

/* ──────── Layout: proper hierarchy with most-connected at top ──────── */
function computeLayout(nodes, edges) {
  const inDegree = {};
  const outEdges = {};
  const inEdges = {};
  nodes.forEach(n => {
    inDegree[n.id] = 0;
    outEdges[n.id] = [];
    inEdges[n.id] = [];
  });
  edges.forEach(e => {
    if (inDegree[e.target] !== undefined) inDegree[e.target]++;
    if (outEdges[e.source]) outEdges[e.source].push(e.target);
    if (inEdges[e.target]) inEdges[e.target].push(e.source);
  });

  // Find roots: nodes with 0 in-degree
  // Sort roots by total connections (degree) descending so the most connected is first
  const roots = nodes
    .filter(n => inDegree[n.id] === 0)
    .sort((a, b) => (b.connections || 0) - (a.connections || 0))
    .map(n => n.id);

  // If no roots (circular deps), pick the node with highest connections as root
  if (roots.length === 0) {
    const top = [...nodes].sort((a, b) => (b.connections || 0) - (a.connections || 0));
    if (top.length > 0) roots.push(top[0].id);
  }

  // BFS to assign layers
  const layer = {};
  roots.forEach(id => { layer[id] = 0; });
  const queue = [...roots];
  let i = 0;
  while (i < queue.length) {
    const cur = queue[i++];
    (outEdges[cur] || []).forEach(child => {
      layer[child] = Math.max(layer[child] || 0, (layer[cur] || 0) + 1);
      if (!queue.includes(child)) queue.push(child);
    });
  }

  // Assign orphans to a separate bottom layer
  const maxLayer = Math.max(0, ...Object.values(layer));
  nodes.forEach(n => {
    if (layer[n.id] === undefined) layer[n.id] = maxLayer + 1;
  });

  // Group by layer
  const byLayer = {};
  nodes.forEach(n => {
    const l = layer[n.id];
    if (!byLayer[l]) byLayer[l] = [];
    byLayer[l].push(n);
  });

  // Sort nodes within each layer by connections (high→low) for a clean look
  Object.values(byLayer).forEach(arr => {
    arr.sort((a, b) => (b.connections || 0) - (a.connections || 0));
  });

  // Determine max nodes per row based on total count
  const totalNodes = nodes.length;
  const MAX_PER_ROW = totalNodes > 30 ? 7 : totalNodes > 20 ? 6 : 5;
  const H_GAP = totalNodes > 30 ? 190 : 210;
  const V_GAP = totalNodes > 30 ? 120 : 135;

  const positioned = {};
  let currentY = 0;
  const layerKeys = Object.keys(byLayer).map(Number).sort((a, b) => a - b);

  for (const lk of layerKeys) {
    const layerNodes = byLayer[lk];
    const ids = layerNodes.map(n => n.id);

    // Sub-row wrapping
    const subRows = [];
    for (let s = 0; s < ids.length; s += MAX_PER_ROW) {
      subRows.push(ids.slice(s, s + MAX_PER_ROW));
    }

    for (const row of subRows) {
      const totalWidth = row.length * H_GAP;
      row.forEach((id, idx) => {
        positioned[id] = {
          x: -(totalWidth / 2) + idx * H_GAP + H_GAP / 2,
          y: currentY,
        };
      });
      currentY += V_GAP;
    }
    // Extra gap between hierarchy levels
    currentY += 20;
  }

  return positioned;
}

/* ──────── Edge filter: keep ALL edges between visible nodes ──────── */
function filterEdges(edges, nodes) {
  const nodeIds = new Set(nodes.map(n => n.id));
  return edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
}

/* ──────── Impact trace: only use visible edges ──────── */
function findReachableAncestors(selectedId, edges) {
  // Build reverse adjacency: target -> [sources]
  const reverseAdj = {};
  for (const e of edges) {
    if (!reverseAdj[e.target]) reverseAdj[e.target] = [];
    reverseAdj[e.target].push(e.source);
  }
  // BFS backwards from selectedId
  const visited = new Set();
  const bfsQueue = [selectedId];
  while (bfsQueue.length > 0) {
    const current = bfsQueue.shift();
    if (visited.has(current)) continue;
    visited.add(current);
    for (const parent of (reverseAdj[current] || [])) {
      if (!visited.has(parent)) {
        bfsQueue.push(parent);
      }
    }
  }
  visited.delete(selectedId);
  return visited;
}

/* ──────── Build set of edges on impact path ──────── */
function findImpactEdges(selectedId, affectedSet, edges) {
  // Only highlight edges where BOTH ends are in (affected ∪ selected)
  const impactNodes = new Set([...affectedSet, selectedId]);
  const impactEdgeIds = new Set();
  edges.forEach((e, i) => {
    if (impactNodes.has(e.source) && impactNodes.has(e.target)) {
      impactEdgeIds.add("e-" + i);
    }
  });
  return impactEdgeIds;
}

/* ──────── Legend ──────── */
function Legend({ presentExts }) {
  return (
    <div style={{
      position: "absolute", bottom: "60px", left: "12px", zIndex: 10,
      background: "rgba(10,15,30,0.95)", border: "1px solid #1e293b",
      borderRadius: "10px", padding: "10px 14px", minWidth: "140px",
      backdropFilter: "blur(8px)",
    }}>
      <div style={{ fontSize: "9px", fontWeight: 700, color: "#94a3b8", marginBottom: "7px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Legend</div>
      {presentExts.map(ext => (
        <div key={ext} style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
          <div style={{ width: "9px", height: "9px", borderRadius: "50%", background: EXT_COLORS[ext] || "#6366f1", flexShrink: 0 }} />
          <span style={{ fontSize: "9.5px", color: "#e2e8f0" }}>{EXT_LABELS[ext] || ext}</span>
        </div>
      ))}
      <div style={{ borderTop: "1px solid #1e293b", marginTop: "6px", paddingTop: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
          <div style={{ width: "9px", height: "9px", borderRadius: "2px", border: "2px solid #3572A5", background: "rgba(53,114,165,0.2)" }} />
          <span style={{ fontSize: "9.5px", color: "#e2e8f0" }}>Core file (≥3 conn.)</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
          <div style={{ width: "9px", height: "9px", borderRadius: "2px", border: "2px solid #EF4444", background: "rgba(239,68,68,0.2)" }} />
          <span style={{ fontSize: "9.5px", color: "#e2e8f0" }}>Affected by change</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <div style={{ width: "9px", height: "9px", borderRadius: "2px", border: "2px solid #F59E0B", background: "rgba(245,158,11,0.2)" }} />
          <span style={{ fontSize: "9.5px", color: "#e2e8f0" }}>Selected file</span>
        </div>
        <div style={{ borderTop: "1px solid #1e293b", marginTop: "5px", paddingTop: "4px", fontSize: "8px", color: "#475569", lineHeight: 1.4 }}>
          A → B means "A imports B"<br />
          Bigger node = more connections
        </div>
      </div>
    </div>
  );
}

/* ──────── Main Component ──────── */
export default function GraphView({ graphData, githubUrl }) {
  const [affectedFiles, setAffectedFiles] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [riskLevel, setRiskLevel] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);

  // Dynamic node limit: scale with repo size (min 20, max 40)
  const nodeLimit = useMemo(() => {
    if (!graphData?.nodes) return 20;
    const total = graphData.nodes.length;
    if (total <= 20) return total;
    if (total <= 30) return Math.min(total, 25);
    return Math.min(total, 40);
  }, [graphData]);

  const topNodes = useMemo(() => {
    if (!graphData?.nodes || graphData.nodes.length === 0) return [];
    return [...graphData.nodes]
      .sort((a, b) => b.connections - a.connections)
      .slice(0, nodeLimit);
  }, [graphData, nodeLimit]);

  const cleanEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    return filterEdges(graphData.edges, topNodes);
  }, [graphData, topNodes]);

  const presentExts = useMemo(() => {
    const exts = new Set(topNodes.map(n => n.id.split(".").pop()));
    return [...exts].filter(e => EXT_COLORS[e]);
  }, [topNodes]);

  const initialNodes = useMemo(() => {
    if (topNodes.length === 0) return [];
    const positions = computeLayout(topNodes, cleanEdges);
    return topNodes.map((node) => ({
      id: node.id,
      type: "custom",
      position: positions[node.id] || { x: 0, y: 0 },
      data: {
        label: node.id,
        connections: node.connections || 0,
        extension: node.extension,
        isAffected: false,
        isSelected: false,
      },
    }));
  }, [topNodes, cleanEdges]);

  const initialEdges = useMemo(() => {
    return cleanEdges.map((edge, i) => {
      const ext = edge.source.split(".").pop();
      const color = EXT_COLORS[ext] || "#6366f1";
      return {
        id: "e-" + i,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: false,
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 12, height: 12 },
        style: { stroke: color, strokeWidth: 1.2, opacity: 0.4 },
      };
    });
  }, [cleanEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(async (_event, node) => {
    if (!githubUrl) return;
    setImpactLoading(true);
    setSelectedNode(node.id);

    // Immediately mark selected, reset all affected
    setNodes((nds) => nds.map((n) => ({
      ...n,
      data: { ...n.data, isAffected: false, isSelected: n.id === node.id },
    })));
    // Reset edges — highlight selected node edges amber
    setEdges((eds) => eds.map((e) => {
      const ext = e.source.split(".").pop();
      const baseColor = EXT_COLORS[ext] || "#6366f1";
      const isSelectedEdge = e.source === node.id || e.target === node.id;
      return {
        ...e,
        animated: false,
        markerEnd: { type: MarkerType.ArrowClosed, color: isSelectedEdge ? "#F59E0B" : baseColor, width: 12, height: 12 },
        style: {
          stroke: isSelectedEdge ? "#F59E0B" : baseColor,
          strokeWidth: isSelectedEdge ? 2 : 1.2,
          opacity: isSelectedEdge ? 0.85 : 0.25,
        },
      };
    }));

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      const data = await getImpact(githubUrl, node.id);
      clearTimeout(timeout);

      // Use the backend's affected files DIRECTLY — no frontend filtering
      const backendAffected = new Set(data.affected_files || []);
      const visibleNodeIds = new Set(topNodes.map(n => n.id));

      // Show affected nodes that are visible in the graph
      const visibleAffected = new Set(
        [...backendAffected].filter(f => visibleNodeIds.has(f))
      );

      // If backend returned nothing, do a LOCAL forward+backward trace as fallback
      if (visibleAffected.size === 0 && backendAffected.size === 0) {
        // Local trace: find all ancestors (who imports this file) through visible edges
        const localAncestors = findReachableAncestors(node.id, cleanEdges);
        localAncestors.forEach(a => {
          if (visibleNodeIds.has(a)) visibleAffected.add(a);
        });
      }

      setAffectedFiles([...visibleAffected]);
      // Use backend risk level directly
      setRiskLevel(data.risk_level || (visibleAffected.size > 3 ? "high" : visibleAffected.size > 0 ? "medium" : "low"));

      // Build set of ALL impacted nodes (affected + selected)
      const impactNodes = new Set([...visibleAffected, node.id]);

      // Update nodes with affected status
      setNodes((nds) => nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isAffected: visibleAffected.has(n.id),
          isSelected: n.id === node.id,
        },
      })));

      // Update edges — red dashed lines ONLY where BOTH ends are on impact chain
      setEdges((eds) => eds.map((e) => {
        // Edge is on impact path only if BOTH source AND target are in (affected ∪ selected)
        const isImpactEdge = impactNodes.has(e.source) && impactNodes.has(e.target);
        const isSelectedEdge = e.source === node.id || e.target === node.id;
        const ext = e.source.split(".").pop();
        const baseColor = EXT_COLORS[ext] || "#6366f1";

        if (isImpactEdge) {
          // Red ANIMATED dashed lines — only on the actual impact chain
          return {
            ...e,
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed, color: "#EF4444", width: 14, height: 14 },
            style: { stroke: "#EF4444", strokeWidth: 2.5, opacity: 0.9 },
          };
        }
        if (isSelectedEdge) {
          // Amber solid lines for selected node's other direct edges
          return {
            ...e,
            animated: false,
            markerEnd: { type: MarkerType.ArrowClosed, color: "#F59E0B", width: 13, height: 13 },
            style: { stroke: "#F59E0B", strokeWidth: 2, opacity: 0.8 },
          };
        }
        // Faded default for everything else
        return {
          ...e,
          animated: false,
          markerEnd: { type: MarkerType.ArrowClosed, color: baseColor, width: 12, height: 12 },
          style: { stroke: baseColor, strokeWidth: 1.2, opacity: 0.15 },
        };
      }));
    } catch (err) {
      console.error("Impact failed:", err);
      setRiskLevel("unknown");
    } finally {
      setImpactLoading(false);
    }
  }, [githubUrl, setNodes, setEdges, cleanEdges]);

  const riskColors = { high: "#EF4444", medium: "#F59E0B", low: "#10B981", unknown: "#6B7280" };

  const connectedCount = useMemo(() => {
    const connected = new Set();
    cleanEdges.forEach(e => { connected.add(e.source); connected.add(e.target); });
    return connected.size;
  }, [cleanEdges]);

  return (
    <motion.div className="graph-container" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} style={{ position: "relative" }}>
      <div className="graph-header">
        <h3>Knowledge Graph</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {riskLevel && (
            <span style={{
              background: riskColors[riskLevel] + "20",
              color: riskColors[riskLevel],
              padding: "4px 10px", borderRadius: "8px", fontSize: "11px",
              fontWeight: 600, border: `1px solid ${riskColors[riskLevel]}40`,
            }}>
              Risk: {riskLevel}
            </span>
          )}
          {affectedFiles.length > 0 && (
            <span style={{
              background: "rgba(239,68,68,0.1)", color: "#EF4444",
              padding: "4px 10px", borderRadius: "8px", fontSize: "11px", fontWeight: 600,
            }}>
              {affectedFiles.length} affected
            </span>
          )}
          <span className="graph-badge">
            {connectedCount} connected · {nodes.length} files
          </span>
        </div>
      </div>

      {impactLoading && (
        <div style={{ padding: "4px 12px", fontSize: "11px", color: "#64748b", fontStyle: "italic" }}>
          Analyzing impact…
        </div>
      )}
      {selectedNode && !impactLoading && riskLevel === "low" && affectedFiles.length === 0 && (
        <div style={{ padding: "4px 12px", fontSize: "11px", color: "#10B981", fontStyle: "italic" }}>
          ✓ This file has no reverse dependencies — safe to modify
        </div>
      )}

      <div className="graph-canvas" style={{ position: "relative" }}>
        <Legend presentExts={presentExts} />
        <ReactFlow
          nodes={nodes} edges={edges}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick} nodeTypes={nodeTypes}
          fitView fitViewOptions={{ padding: 0.3 }} minZoom={0.1} maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          selectNodesOnDrag={false}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Background color="#1e293b" gap={24} size={1} variant="dots" />
          <Controls />
          <MiniMap
            nodeColor={(n) => EXT_COLORS[n.id.split(".").pop()] || "#6366f1"}
            style={{ background: "#0a0f1e", border: "1px solid #1e293b", borderRadius: "8px" }}
          />
        </ReactFlow>
      </div>

      <div style={{
        display: "flex", gap: "12px", padding: "7px 12px", fontSize: "10px",
        color: "#475569", flexWrap: "wrap", alignItems: "center",
        borderTop: "1px solid #1e293b",
      }}>
        <span>🖱️ Click file → impact</span>
        <span>📌 CORE = ≥3 connections</span>
        <span>🔗 Arrows = import direction</span>
        <span>📏 Bigger node = more connections</span>
        <span style={{ marginLeft: "auto", color: "#334155" }}>
          {cleanEdges.length} relationships
        </span>
      </div>
    </motion.div>
  );
}
