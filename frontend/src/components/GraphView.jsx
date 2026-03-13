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
  py: "rgba(53,114,165,0.2)", js: "rgba(247,223,30,0.15)",
  ts: "rgba(49,120,198,0.2)", jsx: "rgba(97,218,251,0.15)",
  tsx: "rgba(49,120,198,0.2)", rb: "rgba(204,52,45,0.2)",
  go: "rgba(0,173,216,0.15)", rs: "rgba(222,165,132,0.15)",
  java: "rgba(237,139,0,0.15)",
};

const EXT_LABELS = {
  py: "Python", js: "JavaScript", ts: "TypeScript",
  jsx: "React JSX", tsx: "React TSX", rb: "Ruby",
  go: "Go", rs: "Rust", java: "Java",
};

function CustomNode({ data }) {
  const fullPath = data.label;
  const filename = fullPath.split("/").pop();
  const ext = filename.split(".").pop();
  const isAffected = data.isAffected;
  const isSelected = data.isSelected;
  const isCore = data.connections >= 3;
  const color = isAffected ? "#EF4444" : isSelected ? "#F59E0B" : (EXT_COLORS[ext] || "#6366f1");
  const bg = isAffected ? "rgba(239,68,68,0.15)" : isSelected ? "rgba(245,158,11,0.15)" : (EXT_BG[ext] || "rgba(17,24,39,0.95)");
  const langLabel = EXT_LABELS[ext] || ext;

  return (
    <div
      title={fullPath}
      style={{
        minWidth: "140px", maxWidth: "200px", borderRadius: "12px",
        padding: "12px 16px", textAlign: "center",
        background: bg,
        border: isCore ? "2px solid " + color : "1.5px solid " + color + "80",
        boxShadow: isCore ? "0 0 20px " + color + "40" : "0 2px 8px rgba(0,0,0,0.3)",
        cursor: "pointer",
        backdropFilter: "blur(8px)",
        transition: "box-shadow 0.2s ease, border-color 0.2s ease",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color, width: 7, height: 7, border: "none" }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", marginBottom: "6px" }}>
        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: color, flexShrink: 0 }} />
        {isCore && (
          <span style={{
            fontSize: "8px", background: color + "25", color: color,
            padding: "2px 6px", borderRadius: "4px", fontWeight: 700,
            letterSpacing: "0.05em", border: "1px solid " + color + "40",
          }}>CORE</span>
        )}
      </div>
      <div style={{
        fontSize: "12.5px", fontWeight: 700, color: "#f1f5f9",
        wordBreak: "break-word", lineHeight: 1.3,
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        {filename}
      </div>
      <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>
        {langLabel} · {data.connections} import{data.connections !== 1 ? "s" : ""}
      </div>
      {isAffected && (
        <div style={{
          fontSize: "9px", color: "#EF4444", fontWeight: 700, marginTop: "3px",
          background: "rgba(239,68,68,0.12)", padding: "1px 6px", borderRadius: "3px",
          display: "inline-block",
        }}>AFFECTED</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 7, height: 7, border: "none" }} />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

function computeLayout(nodes, edges) {
  const inDegree = {};
  const outEdges = {};
  nodes.forEach(n => { inDegree[n.id] = 0; outEdges[n.id] = []; });
  edges.forEach(e => {
    if (inDegree[e.target] !== undefined) inDegree[e.target]++;
    if (outEdges[e.source]) outEdges[e.source].push(e.target);
  });
  const layer = {};
  const roots = nodes.filter(n => inDegree[n.id] === 0).map(n => n.id);
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
  nodes.forEach(n => { if (layer[n.id] === undefined) layer[n.id] = 1; });
  const byLayer = {};
  nodes.forEach(n => {
    const l = layer[n.id];
    if (!byLayer[l]) byLayer[l] = [];
    byLayer[l].push(n.id);
  });
  const H_GAP = 260;
  const V_GAP = 200;
  const positioned = {};
  Object.entries(byLayer).forEach(([l, ids]) => {
    const total = ids.length * H_GAP;
    ids.forEach((id, idx) => {
      positioned[id] = {
        x: -(total / 2) + idx * H_GAP + H_GAP / 2,
        y: parseInt(l) * V_GAP,
      };
    });
  });
  return positioned;
}

function filterEdges(edges, nodes) {
  const nodeIds = new Set(nodes.map(n => n.id));
  const sourceCount = {};
  const filtered = [];
  edges.forEach(e => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return;
    if (!sourceCount[e.source]) sourceCount[e.source] = 0;
    if (sourceCount[e.source] < 3) {
      filtered.push(e);
      sourceCount[e.source]++;
    }
  });
  return filtered;
}

function Legend({ presentExts }) {
  return (
    <div style={{
      position: "absolute", bottom: "60px", left: "12px", zIndex: 10,
      background: "rgba(15,23,42,0.95)", border: "1px solid #1e293b",
      borderRadius: "10px", padding: "10px 14px", minWidth: "140px",
    }}>
      <div style={{ fontSize: "10px", fontWeight: 700, color: "#94a3b8", marginBottom: "8px", textTransform: "uppercase" }}>Legend</div>
      {presentExts.map(ext => (
        <div key={ext} style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "5px" }}>
          <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: EXT_COLORS[ext] || "#3B82F6", flexShrink: 0 }} />
          <span style={{ fontSize: "10px", color: "#e2e8f0" }}>{EXT_LABELS[ext] || ext}</span>
        </div>
      ))}
      <div style={{ borderTop: "1px solid #1e293b", marginTop: "7px", paddingTop: "7px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "5px" }}>
          <div style={{ width: "10px", height: "10px", borderRadius: "2px", border: "2px solid #3572A5", background: "rgba(53,114,165,0.2)" }} />
          <span style={{ fontSize: "10px", color: "#e2e8f0" }}>Core file</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "5px" }}>
          <div style={{ width: "10px", height: "10px", borderRadius: "2px", border: "2px solid #EF4444", background: "rgba(239,68,68,0.2)" }} />
          <span style={{ fontSize: "10px", color: "#e2e8f0" }}>Affected</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
          <div style={{ width: "10px", height: "10px", borderRadius: "2px", border: "2px solid #F59E0B", background: "rgba(245,158,11,0.2)" }} />
          <span style={{ fontSize: "10px", color: "#e2e8f0" }}>Selected</span>
        </div>
      </div>
    </div>
  );
}

export default function GraphView({ graphData, githubUrl }) {
  const [affectedFiles, setAffectedFiles] = useState([]);
  const [riskLevel, setRiskLevel] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);

  const topNodes = useMemo(() => {
    if (!graphData?.nodes || graphData.nodes.length === 0) return [];
    return [...graphData.nodes].sort((a, b) => b.connections - a.connections).slice(0, 20);
  }, [graphData]);

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
      const color = EXT_COLORS[ext] || "#3B82F6";
      return {
        id: "e-" + i,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: false,
        markerEnd: { type: MarkerType.ArrowClosed, color: color, width: 16, height: 16 },
        style: { stroke: color, strokeWidth: 1.5, opacity: 0.55 },
      };
    });
  }, [cleanEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(async (_event, node) => {
    if (!githubUrl) return;
    setImpactLoading(true);
    setRiskLevel(null);

    // Always mark selected node immediately
    setNodes((nds) => nds.map((n) => ({
      ...n,
      data: { ...n.data, isAffected: false, isSelected: n.id === node.id },
    })));

    try {
      // Add 8 second timeout so it never gets stuck
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      const data = await getImpact(githubUrl, node.id);
      clearTimeout(timeout);

      const affected = new Set(data.affected_files || []);
      setAffectedFiles([...affected]);
      setRiskLevel(data.risk_level || "low");

      // Only update affected nodes if there are any
      if (affected.size > 0) {
        setNodes((nds) => nds.map((n) => ({
          ...n,
          data: { ...n.data, isAffected: affected.has(n.id), isSelected: n.id === node.id },
        })));
        setEdges((eds) => eds.map((e) => ({
          ...e,
          animated: affected.has(e.source) || affected.has(e.target),
          markerEnd: { type: MarkerType.ArrowClosed, color: affected.has(e.source) || affected.has(e.target) ? "#EF4444" : (EXT_COLORS[e.source.split(".").pop()] || "#3B82F6"), width: 16, height: 16 },
          style: { stroke: affected.has(e.source) || affected.has(e.target) ? "#EF4444" : (EXT_COLORS[e.source.split(".").pop()] || "#3B82F6"), strokeWidth: affected.has(e.source) || affected.has(e.target) ? 2.5 : 1.5, opacity: 0.8 },
        })));
      } else {
        // No affected files - show low risk
        setRiskLevel("low");
      }
    } catch (err) {
      console.error("Impact failed:", err);
      setRiskLevel("unknown");
    } finally {
      setImpactLoading(false);
    }
  }, [githubUrl, setNodes, setEdges]);

  const riskColors = { high: "#EF4444", medium: "#F59E0B", low: "#10B981", unknown: "#6B7280" };

  return (
    <motion.div className="graph-container" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} style={{ position: "relative" }}>
      <div className="graph-header">
        <h3>Knowledge Graph</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {riskLevel && <span style={{ background: riskColors[riskLevel] + "20", color: riskColors[riskLevel], padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 600, border: "1px solid " + riskColors[riskLevel] + "40" }}>Risk: {riskLevel}</span>}
          {affectedFiles.length > 0 && <span style={{ background: "rgba(239,68,68,0.1)", color: "#EF4444", padding: "4px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 600 }}>{affectedFiles.length} affected</span>}
          <span className="graph-badge">{nodes.length} files mapped</span>
        </div>
      </div>
      {impactLoading && <div style={{ padding: "4px 12px", fontSize: "12px", color: "var(--text-muted)" }}>Analyzing impact...</div>}
      <div className="graph-canvas" style={{ position: "relative" }}>
        <Legend presentExts={presentExts} />
        <ReactFlow
          nodes={nodes} edges={edges}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick} nodeTypes={nodeTypes}
          fitView fitViewOptions={{ padding: 0.3 }} minZoom={0.2} maxZoom={2}
          proOptions={{ hideAttribution: true }}
          selectNodesOnDrag={false}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Background color="#1e293b" gap={24} size={1} variant="dots" />
          <Controls />
          <MiniMap nodeColor={(n) => EXT_COLORS[n.id.split(".").pop()] || "#6366f1"} style={{ background: "#0a0f1e", border: "1px solid #1e293b", borderRadius: "8px" }} />
        </ReactFlow>
      </div>
      <div style={{ display: "flex", gap: "16px", padding: "8px 12px", fontSize: "12px", color: "#64748b", flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: "#475569", marginLeft: "auto" }}>Click any file to see impact · CORE = most imported files</span>
      </div>
    </motion.div>
  );
}




