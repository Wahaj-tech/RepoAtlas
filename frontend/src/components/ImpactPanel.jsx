import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  FileCode2,
  Lightbulb,
  CheckCircle2,
  ExternalLink,
  Clock,
  Target,
  BookOpen,
  GitPullRequest,
  Loader2,
} from "lucide-react";
import { getContributionPath } from "../services/api";



const defaultTips = [
  "Read the CONTRIBUTING.md file first — it has project-specific guidelines.",
  "Look at recent merged PRs for similar issues to understand the expected format.",
  "Run the test suite before making changes to ensure you start from a clean state.",
  "Make small, focused commits with clear messages.",
  "Don't hesitate to ask questions on the issue thread — maintainers appreciate engaged contributors!",
  "Use the project's linting and formatting tools before submitting.",
];

const stepColors = ["#2563eb", "#1e40af", "#3b82f6", "#F59E0B", "#10B981", "#06B6D4", "#F472B6"];
const stepIcons = [BookOpen, FileCode2, Target, GitPullRequest, CheckCircle2, Lightbulb, BookOpen];

export default function ImpactPanel({ issue, githubUrl, userProfile, onBack }) {
  const [pathData, setPathData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPath = () => {
    if (!issue?.issue_id || !githubUrl || !userProfile) return;
    setLoading(true);
    setError(null);

    getContributionPath(githubUrl, issue.issue_id, userProfile)
      .then((data) => setPathData(data))
      .catch((err) => {
        console.error("Failed to load contribution path:", err);
        setError("Could not load AI contribution path.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPath();
  }, [issue?.issue_id, githubUrl, userProfile]);

  if (!issue) return null;

  const apiSteps = pathData?.contribution_path?.steps;
  const tips = pathData?.contribution_path?.tips
    ? [pathData.contribution_path.tips]
    : defaultTips;
  const issueUrl = pathData?.issue?.url || issue.url || `https://github.com/issue/${issue.issue_id}`;

  return (
    <motion.div
      className="impact-panel"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      style={{ color: "#94a3b8" }}
    >
      <motion.button
        className="back-btn"
        onClick={onBack}
        whileHover={{ x: -4 }}
        whileTap={{ scale: 0.95 }}
        style={{
          background: "#1e293b",
          color: "#ffffff",
          border: "1px solid #334155",
        }}
      >
        <ArrowLeft size={18} />
        <span>Back to Dashboard</span>
      </motion.button>

      <motion.div
        className="impact-header"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        style={{
          background: "linear-gradient(135deg, #0f172a, #1e293b)",
          border: "1px solid #1e3a5f",
          color: "#ffffff",
        }}
      >
        <div className="impact-header-top">
          <span className="impact-issue-id">#{issue.issue_id}</span>
          <a
            href={issueUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="impact-github-link"
            style={{ color: "#60a5fa" }}
          >
            <ExternalLink size={14} />
            View on GitHub
          </a>
        </div>
        <h1
          className="impact-title"
          style={{
            color: "#ffffff",
            fontSize: "22px",
            fontWeight: 700,
            margin: "0 0 12px 0",
          }}
        >
          {issue.title}
        </h1>
        <div className="impact-meta">
          <span className="impact-tag">
            <Clock size={14} /> {issue.estimated_time}
          </span>
          <span className="impact-tag difficulty">{issue.difficulty}</span>
          <span className="impact-tag match">
            <Target size={14} /> {issue.match_score}% match
          </span>
        </div>
      </motion.div>

      {/* Loading state */}
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "24px",
            justifyContent: "center",
            color: "var(--text-secondary)",
          }}
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 size={20} />
          </motion.div>
          <span>Generating AI contribution path...</span>
        </motion.div>
      )}

      {/* Error with retry */}
      {error && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "12px",
            padding: "20px",
            color: "#f87171",
            fontSize: "13px",
            margin: "0 0 16px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <span>{error}</span>
          <button
            onClick={fetchPath}
            style={{
              background: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              padding: "8px 20px",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            Try Again
          </button>
        </motion.div>
      )}

      {/* Steps section — AI data only */}
      {apiSteps && (
        <motion.div
          className="impact-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          style={{ background: "#0f172a", border: "1px solid #1e293b" }}
        >
          <h3 className="impact-section-title" style={{ color: "#ffffff" }}>🗺️ Step-by-Step Guide</h3>
          <div className="impact-steps">
            {apiSteps.map((step, index) => {
              const color = stepColors[index % stepColors.length];
              const Icon = stepIcons[index % stepIcons.length];
              return (
                <motion.div
                  key={index}
                  className="impact-step"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + index * 0.1 }}
                >
                  <div
                    className="impact-step-number"
                    style={{
                      background: `${color}20`,
                      color: color,
                      borderColor: color,
                    }}
                  >
                    <Icon size={18} />
                  </div>
                  <div className="impact-step-connector" />
                  <div className="impact-step-content">
                    <h4 style={{ color: "#ffffff" }}>{step.title}</h4>
                    <p style={{ color: "#94a3b8" }}>{step.action}</p>
                    {step.file && (
                      <span
                        style={{
                          display: "inline-block",
                          background: "#1e293b",
                          padding: "2px 10px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          color: "#94a3b8",
                          marginTop: "6px",
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {step.file}
                      </span>
                    )}
                    {step.why && (
                      <p
                        style={{
                          fontSize: "12px",
                          color: "#64748b",
                          marginTop: "4px",
                          fontStyle: "italic",
                        }}
                      >
                        {step.why}
                      </p>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}

      <motion.div
        className="impact-section"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        style={{ background: "#0f172a", border: "1px solid #1e293b" }}
      >
        <h3 className="impact-section-title" style={{ color: "#f59e0b" }}>📁 Files to Explore</h3>
        <div className="impact-files">
          {(pathData?.contribution_path?.key_files || issue.files_to_look_at || []).map((file, i) => (
            <motion.div
              key={i}
              className="impact-file"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 + i * 0.1 }}
              whileHover={{ scale: 1.03, x: 4 }}
              style={{ background: "#1e293b", border: "1px solid #1e293b" }}
            >
              <FileCode2 size={16} className="impact-file-icon" />
              <span className="impact-file-path" style={{ color: "#94a3b8" }}>{file}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <motion.div
        className="impact-section"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        style={{
          background: "#0f172a",
          border: "1px solid #1e3a5f",
          color: "#94a3b8",
        }}
      >
        <h3 className="impact-section-title" style={{ color: "#ffffff" }}>💡 Pro Tips</h3>
        <div className="impact-tips">
          {tips.map((tip, i) => (
            <motion.div
              key={i}
              className="impact-tip"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + i * 0.08 }}
            >
              <Lightbulb size={14} className="tip-icon" />
              <span style={{ color: "#94a3b8" }}>{tip}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Setup commands if available */}
      {pathData?.contribution_path?.setup_commands?.length > 0 && (
        <motion.div
          className="impact-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <h3 className="impact-section-title">⚙️ Setup Commands</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {pathData.contribution_path.setup_commands.map((cmd, i) => (
              <div
                key={i}
                style={{
                  background: "var(--bg-elevated)",
                  padding: "10px 16px",
                  borderRadius: "8px",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "13px",
                  color: "var(--accent-light)",
                }}
              >
                $ {cmd}
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
