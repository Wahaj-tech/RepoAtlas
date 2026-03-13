import { motion } from "framer-motion";
import { GitBranch, Search, Cpu, Sparkles } from "lucide-react";

const steps = [
  { icon: GitBranch, label: "Cloning repository...", color: "#3B82F6" },
  { icon: Search, label: "Analyzing code structure...", color: "#8B5CF6" },
  { icon: Cpu, label: "Building knowledge graph...", color: "#EC4899" },
  { icon: Sparkles, label: "Finding perfect issues for you...", color: "#10B981" },
];

export default function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-orbs">
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            className="loading-orb"
            animate={{
              x: [0, Math.random() * 200 - 100, 0],
              y: [0, Math.random() * 200 - 100, 0],
              scale: [1, 1.3, 1],
              opacity: [0.15, 0.3, 0.15],
            }}
            transition={{
              duration: 6 + i * 1.2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{
              left: `${15 + i * 14}%`,
              top: `${20 + (i % 3) * 25}%`,
              background: steps[i % steps.length].color,
            }}
          />
        ))}
      </div>
      <motion.div
        className="loading-content"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <motion.div
          className="loading-logo"
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        >
          <div className="loading-logo-inner">
            <Cpu size={36} />
          </div>
        </motion.div>
        <motion.h2
          className="loading-title"
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          Analyzing Repository
        </motion.h2>
        <div className="loading-steps">
          {steps.map((step, index) => (
            <motion.div
              key={index}
              className="loading-step"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 8, duration: 0.5 }}
            >
              <motion.div
                className="loading-step-icon"
                style={{ background: `${step.color}20`, color: step.color }}
                animate={{
                  boxShadow: [
                    `0 0 0px ${step.color}00`,
                    `0 0 20px ${step.color}40`,
                    `0 0 0px ${step.color}00`,
                  ],
                }}
                transition={{
                  delay: index * 8,
                  duration: 2,
                  repeat: Infinity,
                }}
              >
                <step.icon size={18} />
              </motion.div>
              <motion.span
                className="loading-step-label"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{
                  delay: index * 8,
                  duration: 2,
                  repeat: Infinity,
                }}
              >
                {step.label}
              </motion.span>
            </motion.div>
          ))}
        </div>
        <div className="loading-progress-track">
          <motion.div
            className="loading-progress-bar"
            initial={{ width: "0%" }}
            animate={{ width: "90%" }}
            transition={{ duration: 80, ease: "easeInOut" }}
          />
        </div>
        <motion.p
          style={{ color: "#64748b", fontSize: "12px", marginTop: "12px" }}
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          This may take up to 90 seconds on first load...
        </motion.p>
      </motion.div>
    </div>
  );
}
