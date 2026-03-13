import { motion } from "framer-motion";
import {
  AlertCircle,
  Clock,
  FileCode2,
  ArrowRight,
  Zap,
  ExternalLink,
} from "lucide-react";

const difficultyConfig = {
  easy: { color: "#10B981", bg: "#10B98118", label: "Easy" },
  medium: { color: "#F59E0B", bg: "#F59E0B18", label: "Medium" },
  hard: { color: "#EF4444", bg: "#EF444418", label: "Hard" },
};

function getScoreClass(score) {
  if (score >= 75) return "score-high";
  if (score >= 50) return "score-mid";
  return "score-low";
}

export default function IssueCard({ issue, index, onSelect }) {
  const diff = difficultyConfig[issue.difficulty] || difficultyConfig.medium;
  const files = issue.files_to_look_at || [];

  return (
    <motion.div
      className="issue-card"
      initial={{ opacity: 0, y: 20, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: 0.15 + index * 0.1, duration: 0.45 }}
      whileHover={{ y: -4 }}
      onClick={() => onSelect(issue)}
    >
      <motion.div
        className={`issue-match-badge ${getScoreClass(issue.match_score)}`}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.4 + index * 0.1, type: "spring" }}
      >
        <Zap size={12} />
        <span>{issue.match_score}%</span>
      </motion.div>

      <div className="issue-card-header">
        <div className="issue-id">
          <AlertCircle size={13} />
          <span>#{issue.issue_id}</span>
        </div>
        <div
          className="issue-difficulty"
          style={{ background: diff.bg, color: diff.color, border: `1px solid ${diff.color}30` }}
        >
          {diff.label}
        </div>
      </div>

      <h4 className="issue-title">{issue.title}</h4>
      <p className="issue-why">{issue.why_good_match}</p>

      <div className="issue-meta">
        <div className="issue-meta-item">
          <Clock size={13} />
          <span>{issue.estimated_time}</span>
        </div>
        {files.length > 0 && (
          <div className="issue-meta-item">
            <FileCode2 size={13} />
            <span>{files.length} file{files.length !== 1 ? "s" : ""}</span>
          </div>
        )}
      </div>

      {files.length > 0 && (
        <div className="issue-files">
          {files.slice(0, 3).map((file, i) => (
            <span key={i} className="issue-file-tag">
              {file.split("/").pop()}
            </span>
          ))}
          {files.length > 3 && (
            <span className="issue-file-tag more">
              +{files.length - 3}
            </span>
          )}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "2px" }}>
        <motion.div className="issue-cta" whileHover={{ x: 4 }}>
          <span>View contribution path</span>
          <ArrowRight size={15} />
        </motion.div>
        {issue.url && (
          <a
            href={issue.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{
              color: "#818cf8",
              fontSize: "12px",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              opacity: 0.8,
              transition: "opacity 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.8")}
          >
            <ExternalLink size={12} />
            GitHub
          </a>
        )}
      </div>
    </motion.div>
  );
}
