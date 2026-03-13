import { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import { getImpact } from "../services/api";

const EXT_COLORS = {
  py: "#3572A5",
  js: "#F7DF1E",
  ts: "#3178C6",
  jsx: "#61DAFB",
  tsx: "#3178C6",
  rb: "#CC342D",
  go: "#00ADD8",
  rs: "#DEA584",
  java: "#ED8B00",
  cpp: "#00599C",
  css: "#563D7C",
  html: "#E34C26",
  md: "#083FA1",
};

function CustomNode({ data }) {
  const filename = data.label.split("/").pop();
  const ext = filename.split(".").pop();
  const isAffected = data.isAffected;
  const isSelected = data.isSelected;
  const color = isAffected ? "#EF4444" : isSelected ? "#F59E0B" : (EXT_COLORS[ext] || "#2563eb");

  return (
    <motion.div
      className="graph-node"
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.15, zIndex: 10 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      style={{
        borderColor: color,
        boxShadow: isAffected
          ? `0 0 20px rgba(239, 68, 68, 0.5)`
          : isSelected
          ? `0 0 20px rgba(245, 158, 11, 0.5)`
          : `0 0 16px ${color}40`,
      }}
    >
      <div className="graph-node-dot" style={{ background: color }} />
      <div className="graph-node-name">{filename}</div>
      <div className="graph-node-connections">
        {data.connections} connections
      </div>
      {isAffected && (
        <div style={{ fontSize: "9px", color: "#EF4444", marginTop: "2px", fontWeight: 600 }}>
          AFFECTED
        </div>
      )}
    </motion.div>
  );
}

const nodeTypes = { custom: CustomNode };

export default function GraphView({ graphData, githubUrl }) {
  const [affectedFiles, setAffectedFiles] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [riskLevel, setRiskLevel] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);

  const initialNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    const capped = graphData.nodes.slice(0, 40);
    const total = capped.length;
    const cols = Math.ceil(Math.sqrt(total));

    return capped.map((node, i) => {
      const row = Math.floor(i / cols);
      const col = i % cols;
      return {
        id: node.id,
        type: "custom",
        position: {
          x: col * 220,
          y: row * 140,
        },
        data: {
          label: node.id,
          connections: node.connections,
          extension: node.extension,
          isAffected: false,
          isSelected: false,
        },
      };
    });
  }, [graphData]);

  const initialEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    return graphData.edges.map((edge, i) => ({
      id: `e-${i}`,
      source: edge.source,
      target: edge.target,
      animated: true,
      style: {
        stroke: "#2563eb",
        strokeWidth: 2,
      },
    }));
  }, [graphData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(async (_event, node) => {
    if (!githubUrl) return;

    setSelectedNode(node.id);
    setImpactLoading(true);
    setRiskLevel(null);

    try {
      const data = await getImpact(githubUrl, node.id);
      const affected = new Set(data.affected_files || []);
      setAffectedFiles([...affected]);
      setRiskLevel(data.risk_level);

      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: {
            ...n.data,
            isAffected: affected.has(n.id),
            isSelected: n.id === node.id,
          },
        }))
      );

      setEdges((eds) =>
        eds.map((e) => ({
          ...e,
          style: {
            stroke: affected.has(e.source) || affected.has(e.target) ? "#EF4444" : "#2563eb",
            strokeWidth: affected.has(e.source) || affected.has(e.target) ? 3 : 2,
          },
          animated: true,
        }))
      );
    } catch (err) {
      console.error("Impact analysis failed:", err);
    } finally {
      setImpactLoading(false);
    }
  }, [githubUrl, setNodes, setEdges]);

  const riskColors = { high: "#EF4444", medium: "#F59E0B", low: "#10B981", unknown: "#6B7280" };

  return (
    <motion.div
      className="graph-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
    >
      <div className="graph-header">
        <h3>📊 Knowledge Graph</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {riskLevel && (
            <span
              style={{
                background: `${riskColors[riskLevel]}20`,
                color: riskColors[riskLevel],
                padding: "4px 10px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
                border: `1px solid ${riskColors[riskLevel]}40`,
              }}
            >
              Risk: {riskLevel}
            </span>
          )}
          {affectedFiles.length > 0 && (
            <span
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                color: "#EF4444",
                padding: "4px 10px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              {affectedFiles.length} affected
            </span>
          )}
          <span className="graph-badge">{nodes.length} files mapped</span>
        </div>
      </div>
      {impactLoading && (
        <div style={{ padding: "4px 12px", fontSize: "12px", color: "var(--text-muted)" }}>
          Analyzing impact...
        </div>
      )}
      <div className="graph-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#374151" gap={20} size={1} />
          <Controls />
        </ReactFlow>
      </div>
      <div
        style={{
          display: "flex",
          gap: "16px",
          padding: "8px 12px",
          fontSize: "12px",
          color: "var(--text-secondary)",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#3572A5" }}>● Python</span>
        <span style={{ color: "#F7DF1E" }}>● JavaScript</span>
        <span style={{ color: "#3178C6" }}>● TypeScript</span>
        <span style={{ color: "#00ADD8" }}>● Go</span>
        <span style={{ color: "#ED8B00" }}>● Java</span>
        <span style={{ color: "#DEA584" }}>● Rust</span>
        <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>
          Click a node to simulate impact · Larger = more connections
        </span>
      </div>
    </motion.div>
  );
}
