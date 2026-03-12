import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Github,
  Globe,
  Rocket,
  Clock,
  Code2,
  ChevronRight,
  Sparkles,
  Star,
  Zap,
  GitFork,
} from "lucide-react";

const languages = [
  { id: "python", label: "Python", icon: "🐍" },
  { id: "javascript", label: "JavaScript", icon: "⚡" },
  { id: "typescript", label: "TypeScript", icon: "🔷" },
  { id: "java", label: "Java", icon: "☕" },
  { id: "go", label: "Go", icon: "🐹" },
  { id: "rust", label: "Rust", icon: "🦀" },
  { id: "cpp", label: "C++", icon: "⚙️" },
  { id: "ruby", label: "Ruby", icon: "💎" },
];

const experienceLevels = [
  { id: "beginner", label: "Beginner", desc: "New to open source", icon: "🌱" },
  { id: "intermediate", label: "Intermediate", desc: "Some contributions", icon: "🌿" },
  { id: "advanced", label: "Advanced", desc: "Regular contributor", icon: "🌳" },
];

const timeOptions = [
  { id: "1h", label: "1 hour", icon: "⏱️", value: "< 2 hours" },
  { id: "3h", label: "3 hours", icon: "🕐", value: "half day" },
  { id: "1d", label: "1 day", icon: "📅", value: "full day" },
  { id: "1w", label: "1 week", icon: "📆", value: "full day" },
];

const langLabelMap = Object.fromEntries(languages.map((l) => [l.id, l.label]));

const floatingIcons = [Star, GitFork, Code2, Zap, Sparkles, Github, Globe, Rocket];

export default function Landing({ onAnalyze, error }) {
  const [url, setUrl] = useState("");
  const [selectedLangs, setSelectedLangs] = useState([]);
  const [experience, setExperience] = useState("");
  const [timeAvailable, setTimeAvailable] = useState("");
  const [step, setStep] = useState(0);

  const toggleLang = (id) => {
    setSelectedLangs((prev) =>
      prev.includes(id) ? prev.filter((l) => l !== id) : [...prev, id]
    );
  };

  const canProceed = () => {
    if (step === 0) return url.trim().length > 0;
    if (step === 1) return selectedLangs.length > 0;
    if (step === 2) return experience !== "" && timeAvailable !== "";
    return false;
  };

  const handleNext = () => {
    if (step < 2) {
      setStep(step + 1);
    } else {
      const timeValue = timeOptions.find((t) => t.id === timeAvailable)?.value || timeAvailable;
      onAnalyze(url, {
        languages: selectedLangs.map((id) => langLabelMap[id] || id),
        experience,
        time_available: timeValue,
      });
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && canProceed()) handleNext();
  };

  return (
    <div className="landing-page">
      {/* Floating animated particles */}
      <div className="landing-particles">
        {floatingIcons.map((Icon, i) => (
          <motion.div
            key={i}
            className="landing-particle"
            initial={{
              x: Math.random() * (typeof window !== "undefined" ? window.innerWidth : 1200),
              y: Math.random() * (typeof window !== "undefined" ? window.innerHeight : 800),
              opacity: 0,
            }}
            animate={{
              y: [null, -900],
              opacity: [0, 0.15, 0.15, 0],
              rotate: [0, 360],
            }}
            transition={{
              duration: 12 + Math.random() * 8,
              repeat: Infinity,
              delay: i * 1.5,
              ease: "linear",
            }}
          >
            <Icon size={20 + Math.random() * 16} />
          </motion.div>
        ))}
      </div>

      {/* Gradient mesh background */}
      <div className="landing-mesh" />

      <motion.div
        className="landing-container"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
      >
        {/* Logo & Title */}
        <motion.div
          className="landing-hero"
          initial={{ y: -30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          <motion.div
            className="landing-logo"
            animate={{ rotateY: [0, 360] }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
              repeatDelay: 3,
            }}
          >
            <Globe size={44} />
          </motion.div>
          <h1 className="landing-title">
            Repo<span className="accent">Atlas</span>
          </h1>
          <p className="landing-subtitle">
            Your AI-powered guide to open source contribution
          </p>
        </motion.div>

        {/* Step Progress Indicator */}
        <div className="landing-progress">
          {[0, 1, 2].map((s) => (
            <motion.div
              key={s}
              className={`progress-dot ${step >= s ? "active" : ""} ${
                step === s ? "current" : ""
              }`}
              animate={step === s ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 1, repeat: Infinity }}
            />
          ))}
        </div>

        {error && (
          <motion.div
            className="landing-error"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "12px",
              padding: "12px 20px",
              color: "#f87171",
              textAlign: "center",
              marginBottom: "1rem",
              fontSize: "14px",
            }}
          >
            {error}
          </motion.div>
        )}

        {/* Step Content with Animations */}
        <AnimatePresence mode="wait">
          {step === 0 && (
            <motion.div
              key="step0"
              className="landing-step"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="step-title">
                <Github size={24} /> Enter a GitHub Repository
              </h2>
              <p className="step-desc">
                Paste the URL of any public GitHub repository you want to
                contribute to
              </p>
              <div className="url-input-wrapper">
                <Github size={20} className="url-icon" />
                <input
                  id="github-url-input"
                  type="text"
                  placeholder="https://github.com/user/repo"
                  className="url-input"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoFocus
                />
                {url && (
                  <motion.div
                    className="url-check"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                  >
                    ✓
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}

          {step === 1 && (
            <motion.div
              key="step1"
              className="landing-step"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="step-title">
                <Code2 size={24} /> Your Languages
              </h2>
              <p className="step-desc">
                Select the languages you're comfortable with
              </p>
              <div className="lang-grid">
                {languages.map((lang) => (
                  <motion.button
                    key={lang.id}
                    className={`lang-btn ${
                      selectedLangs.includes(lang.id) ? "selected" : ""
                    }`}
                    onClick={() => toggleLang(lang.id)}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <span className="lang-icon">{lang.icon}</span>
                    <span className="lang-label">{lang.label}</span>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              className="landing-step"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="step-title">
                <Rocket size={24} /> Your Profile
              </h2>
              <p className="step-desc">
                Tell us about yourself so we can find the best issues
              </p>

              {/* Experience Section */}
              <div style={{ marginBottom: "24px" }}>
                <h3 style={{ color: "var(--text-primary)", fontSize: "14px", fontWeight: 600, marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                  🚀 Experience Level
                </h3>
                <div className="experience-grid">
                  {experienceLevels.map((level) => (
                    <motion.button
                      key={level.id}
                      className={`exp-btn ${
                        experience === level.id ? "selected" : ""
                      }`}
                      onClick={() => setExperience(level.id)}
                      whileHover={{ scale: 1.03, y: -4 }}
                      whileTap={{ scale: 0.97 }}
                    >
                      <span className="exp-icon">{level.icon}</span>
                      <span className="exp-label">{level.label}</span>
                      <span className="exp-desc">{level.desc}</span>
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Divider */}
              <div style={{ height: "1px", background: "var(--border)", margin: "20px 0" }} />

              {/* Time Section */}
              <div>
                <h3 style={{ color: "var(--text-primary)", fontSize: "14px", fontWeight: 600, marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Clock size={16} /> Time Available
                </h3>
                <div className="time-grid">
                  {timeOptions.map((opt) => (
                    <motion.button
                      key={opt.id}
                      className={`time-btn ${
                        timeAvailable === opt.id ? "selected" : ""
                      }`}
                      onClick={() => setTimeAvailable(opt.id)}
                      whileHover={{ scale: 1.05, y: -4 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <span className="time-icon">{opt.icon}</span>
                      <span className="time-label">{opt.label}</span>
                    </motion.button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Navigation Buttons */}
        <div className="landing-nav">
          {step > 0 && (
            <motion.button
              className="nav-back"
              onClick={() => setStep(step - 1)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              whileHover={{ x: -3 }}
            >
              ← Back
            </motion.button>
          )}
          <motion.button
            className={`nav-next ${canProceed() ? "active" : "disabled"}`}
            onClick={handleNext}
            disabled={!canProceed()}
            whileHover={canProceed() ? { scale: 1.05 } : {}}
            whileTap={canProceed() ? { scale: 0.95 } : {}}
          >
            {step === 2 ? (
              <>
                <Sparkles size={18} />
                Analyze Repository
              </>
            ) : (
              <>
                Continue
                <ChevronRight size={18} />
              </>
            )}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
