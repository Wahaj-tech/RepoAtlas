import { motion } from "framer-motion";
import {
  Star,
  Code2,
  Globe,
  ArrowLeft,
  Sparkles,
} from "lucide-react";
import GraphView from "../components/GraphView";
import IssueCard from "../components/IssueCard";

export default function Dashboard({ data, matches, githubUrl, userProfile, onSelectIssue, onBack }) {
  const { metadata, graph } = data;
  const recommendations = matches?.matches || data.recommendations || [];

  return (
    <div className="dashboard-page">
      <div className="dashboard-glow" />

      {/* Top bar */}
      <motion.div
        className="dashboard-topbar"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <motion.button
          className="back-btn"
          onClick={onBack}
          whileHover={{ x: -4 }}
          whileTap={{ scale: 0.95 }}
        >
          <ArrowLeft size={18} />
          <span>New Search</span>
        </motion.button>
        <div className="topbar-brand">
          <Globe size={20} />
          <span>
            Repo<span className="accent">Atlas</span>
          </span>
        </div>
      </motion.div>

      {/* Repository Header */}
      <motion.div
        className="repo-header"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
      >
        <div className="repo-header-content">
          <div className="repo-info">
            <motion.h1
              className="repo-name"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              {metadata.name}
            </motion.h1>
            <motion.p
              className="repo-desc"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              {metadata.description}
            </motion.p>
          </div>
          <motion.div
            className="repo-stats"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
          >
            <div className="repo-stat">
              <Star size={16} className="stat-icon star" />
              <span className="stat-value">
                {metadata.stars?.toLocaleString()}
              </span>
              <span className="stat-label">stars</span>
            </div>
            <div className="repo-stat">
              <Code2 size={16} className="stat-icon lang" />
              <span className="stat-value">{metadata.language}</span>
              <span className="stat-label">language</span>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* Main content grid */}
      <div className="dashboard-grid">
        <div className="dashboard-graph-section">
          <GraphView graphData={graph} githubUrl={githubUrl} />
        </div>

        <motion.div
          className="dashboard-issues-section"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <div className="issues-header">
            <h3>
              <Sparkles size={20} className="issues-icon" />
              Recommended Issues
            </h3>
            <span className="issues-count">
              {recommendations.length} matches found
            </span>
          </div>
          <div className="issues-list">
            {recommendations.map((issue, index) => (
              <IssueCard
                key={issue.issue_id}
                issue={issue}
                index={index}
                onSelect={onSelectIssue}
              />
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
