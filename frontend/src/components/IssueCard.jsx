import { motion } from "framer-motion";
import {
  AlertCircle,
  Clock,
  FileCode2,
  ArrowRight,
  Zap,
} from "lucide-react";

const difficultyConfig = {
  easy: { color: "#10B981", bg: "#10B98115", label: "Easy", icon: "🟢" },
  medium: { color: "#F59E0B", bg: "#F59E0B15", label: "Medium", icon: "🟡" },
  hard: { color: "#EF4444", bg: "#EF444415", label: "Hard", icon: "🔴" },
};

export default function IssueCard({ issue, index, onSelect }) {
  const diff = difficultyConfig[issue.difficulty] || difficultyConfig.medium;

  return (
    <motion.div
      className="issue-card"
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: 0.2 + index * 0.15, duration: 0.5 }}
      whileHover={{ y: -6, scale: 1.02 }}
      onClick={() => onSelect(issue)}
    >
      <motion.div
        className="issue-match-badge"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.5 + index * 0.15, type: "spring" }}
      >
        <Zap size={14} />
        <span>{issue.match_score}% match</span>
      </motion.div>

      <div className="issue-card-header">
        <div className="issue-id">
          <AlertCircle size={14} />
          <span>#{issue.issue_id}</span>
        </div>
        <div
          className="issue-difficulty"
          style={{ background: diff.bg, color: diff.color }}
        >
          {diff.icon} {diff.label}
        </div>
      </div>

      <h4 className="issue-title">{issue.title}</h4>
      <p className="issue-why">{issue.why_good_match}</p>

      <div className="issue-meta">
        <div className="issue-meta-item">
          <Clock size={14} />
          <span>{issue.estimated_time}</span>
        </div>
        <div className="issue-meta-item">
          <FileCode2 size={14} />
          <span>{issue.files_to_look_at.length} files</span>
        </div>
      </div>

      <div className="issue-files">
        {issue.files_to_look_at.slice(0, 2).map((file, i) => (
          <span key={i} className="issue-file-tag">
            {file.split("/").pop()}
          </span>
        ))}
        {issue.files_to_look_at.length > 2 && (
          <span className="issue-file-tag more">
            +{issue.files_to_look_at.length - 2} more
          </span>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "4px" }}>
        <motion.div className="issue-cta" whileHover={{ x: 5 }}>
          <span>View contribution path</span>
          <ArrowRight size={16} />
        </motion.div>
        {issue.url && (
          <a
            href={issue.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{
              color: "#60A5FA",
              fontSize: "12px",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            View on GitHub →
          </a>
        )}
      </div>
    </motion.div>
  );
}
