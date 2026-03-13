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
  { id: "python", label: "Python", icon: "/icons/python.png" },
  { id: "javascript", label: "JavaScript", icon: "/icons/javascript.png" },
  { id: "typescript", label: "TypeScript", icon: "/icons/typescript.png" },
  { id: "java", label: "Java", icon: "/icons/java.png" },
  { id: "go", label: "Go", icon: "/icons/go.png" },
  { id: "rust", label: "Rust", icon: "/icons/rust.png" },
  { id: "cpp", label: "C++", icon: "/icons/cpp.png" },
  { id: "ruby", label: "Ruby", icon: "/icons/ruby.png" },
  { id: "swift", label: "Swift", icon: "/icons/swift.png" },
  { id: "php", label: "PHP", icon: "/icons/php.png" },
  { id: "kotlin", label: "Kotlin", icon: "/icons/kotlin.png" },
  { id: "csharp", label: "C#", icon: "/icons/csharp.png" },
  { id: "scala", label: "Scala", icon: "/icons/scala.png" },
  { id: "dart", label: "Dart", icon: "/icons/dart.png" },
  { id: "haskell", label: "Haskell", icon: "/icons/haskell.png" },
  { id: "lua", label: "Lua", icon: "/icons/lua.png" },
  { id: "perl", label: "Perl", icon: "/icons/perl.png" },
  { id: "r", label: "R", icon: "/icons/r.png" },
  { id: "julia", label: "Julia", icon: "/icons/julia.png" },
  { id: "html", label: "HTML", icon: "/icons/html.png" },
  { id: "css", label: "CSS", icon: "/icons/css.png" },
  { id: "sql", label: "SQL", icon: "/icons/sql.png" },
  { id: "shell", label: "Shell", icon: "/icons/shell.png" },
];

const experienceLevels = [
  { id: "beginner", label: "Beginner", desc: "New to open source", icon: "/icons/beginner.png" },
  { id: "intermediate", label: "Intermediate", desc: "Some contributions", icon: "/icons/intermediate.png" },
  { id: "advanced", label: "Advanced", desc: "Regular contributor", icon: "/icons/advanced.png" },
];

const timeOptions = [
  { id: "1h", label: "1 hour", icon: "/icons/time_1h.png", value: "< 2 hours" },
  { id: "3h", label: "3 hours", icon: "/icons/time_3h.png", value: "half day" },
  { id: "1d", label: "1 day", icon: "/icons/time_1d.png", value: "full day" },
  { id: "1w", label: "1 week", icon: "/icons/time_1w.png", value: "full day" },
];

const langLabelMap = Object.fromEntries(languages.map((l) => [l.id, l.label]));

const floatingIcons = [Star, GitFork, Code2, Zap, Sparkles, Github, Globe, Rocket];

export default function Landing({ onAnalyze, error, externalStep, onStepChange }) {
  const [url, setUrl] = useState("");
  const [selectedLangs, setSelectedLangs] = useState([]);
  const [experience, setExperience] = useState("");
  const [timeAvailable, setTimeAvailable] = useState("");
  const [internalStep, setInternalStep] = useState(0);

  const step = externalStep !== undefined ? externalStep : internalStep;
  const setStep = onStepChange || setInternalStep;

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
              <div className="lang-scroll-box">
                <div className="lang-grid">
                  {languages.map((lang) => (
                    <motion.button
                      key={lang.id}
                      className={`lang-btn ${selectedLangs.includes(lang.id) ? "selected" : ""
                        }`}
                      onClick={() => toggleLang(lang.id)}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <span className="lang-icon">
                        {lang.icon.startsWith("/") ? (
                          <img src={lang.icon} alt={lang.label} style={{ width: "32px", height: "32px", objectFit: "contain" }} />
                        ) : (
                          lang.icon
                        )}
                      </span>
                      <span className="lang-label">{lang.label}</span>
                    </motion.button>
                  ))}
                </div>
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
                <img src="/icons/profile_step.png" alt="Profile" style={{ width: "32px", height: "32px", objectFit: "contain" }} />
                Your Profile
              </h2>
              <p className="step-desc">
                Tell us about yourself so we can find the best issues
              </p>

              <div className="profile-grid">
                {/* Experience Section */}
                <div className="profile-section">
                  <h3 className="profile-section-title">
                    <img src="/icons/experience.png" alt="Experience" style={{ width: "28px", height: "28px", objectFit: "contain" }} />
                    Experience Level
                  </h3>
                  <div className="experience-grid">
                    {experienceLevels.map((level) => (
                      <motion.button
                        key={level.id}
                        className={`exp-btn ${experience === level.id ? "selected" : ""
                          }`}
                        onClick={() => setExperience(level.id)}
                        whileHover={{ scale: 1.03, y: -4 }}
                        whileTap={{ scale: 0.97 }}
                      >
                        <span className="exp-icon">
                          {level.icon.startsWith("/") ? (
                            <img src={level.icon} alt={level.label} style={{ width: "40px", height: "40px", objectFit: "contain" }} />
                          ) : (
                            level.icon
                          )}
                        </span>
                        <span className="exp-label">{level.label}</span>
                        <span className="exp-desc">{level.desc}</span>
                      </motion.button>
                    ))}
                  </div>
                </div>

                {/* Time Section */}
                <div className="profile-section">
                  <h3 className="profile-section-title">
                    <img src="/icons/time.png" alt="Time" style={{ width: "28px", height: "28px", objectFit: "contain" }} />
                    Time Available
                  </h3>
                  <div className="time-grid">
                    {timeOptions.map((opt) => (
                      <motion.button
                        key={opt.id}
                        className={`time-btn ${timeAvailable === opt.id ? "selected" : ""
                          }`}
                        onClick={() => setTimeAvailable(opt.id)}
                        whileHover={{ scale: 1.05, y: -4 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <span className="time-icon">
                          {opt.icon.startsWith("/") ? (
                            <img src={opt.icon} alt={opt.label} style={{ width: "32px", height: "32px", objectFit: "contain" }} />
                          ) : (
                            opt.icon
                          )}
                        </span>
                        <span className="time-label">{opt.label}</span>
                      </motion.button>
                    ))}
                  </div>
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

        {/* Step Progress Indicator */}
        <div className="landing-progress">
          {[0, 1, 2].map((s) => (
            <motion.div
              key={s}
              className={`progress-dot ${step >= s ? "active" : ""} ${step === s ? "current" : ""
                }`}
              animate={step === s ? { scale: [1, 1.2, 1] } : {}}
              transition={{ duration: 1, repeat: Infinity }}
            />
          ))}
        </div>
      </motion.div>
    </div>
  );
}
