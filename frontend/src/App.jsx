import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Globe, User } from "lucide-react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import IssuePage from "./pages/IssuePage";
import LoadingScreen from "./components/LoadingScreen";
import { analyzeRepo, matchIssues } from "./services/api";
import "./App.css";

const STORE_KEYS = {
  repoData: "repoatlas:repoData",
  matchesData: "repoatlas:matchesData",
  githubUrl: "repoatlas:githubUrl",
  userProfile: "repoatlas:userProfile",
  selectedIssue: "repoatlas:selectedIssue",
};

const readJson = (key, fallback = null) => {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
};

const writeJson = (key, value) => {
  if (value === null || value === undefined) {
    sessionStorage.removeItem(key);
    return;
  }
  sessionStorage.setItem(key, JSON.stringify(value));
};

const readText = (key, fallback = "") => sessionStorage.getItem(key) || fallback;
const writeText = (key, value) => {
  if (!value) {
    sessionStorage.removeItem(key);
    return;
  }
  sessionStorage.setItem(key, value);
};

// Global in-memory state to keep flow snappy between routes.
let globalRepoData = readJson(STORE_KEYS.repoData);
let globalMatchesData = readJson(STORE_KEYS.matchesData);
let globalGithubUrl = readText(STORE_KEYS.githubUrl);
let globalUserProfile = readJson(STORE_KEYS.userProfile);

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState(null);
  const [appContext, setAppContext] = useState(() => ({
    repoData: globalRepoData,
    matchesData: globalMatchesData,
    githubUrl: globalGithubUrl,
    userProfile: globalUserProfile,
    selectedIssue: readJson(STORE_KEYS.selectedIssue),
  }));

  const hasDashboardData = useMemo(
    () => Boolean(appContext.repoData && appContext.githubUrl),
    [location.pathname, appContext.repoData, appContext.githubUrl]
  );

  const persistBaseContext = (url, profile) => {
    globalGithubUrl = url;
    globalUserProfile = profile;
    writeText(STORE_KEYS.githubUrl, url);
    writeJson(STORE_KEYS.userProfile, profile);
    setAppContext((prev) => ({
      ...prev,
      githubUrl: url,
      userProfile: profile,
    }));
  };

  const persistAnalyzeData = (analyzeResult) => {
    globalRepoData = analyzeResult;
    writeJson(STORE_KEYS.repoData, analyzeResult);
    setAppContext((prev) => ({ ...prev, repoData: analyzeResult }));
  };

  const persistMatchesData = (matchResult) => {
    globalMatchesData = matchResult;
    writeJson(STORE_KEYS.matchesData, matchResult);
    setAppContext((prev) => ({ ...prev, matchesData: matchResult }));
  };

  const clearSessionContext = () => {
    globalRepoData = null;
    globalMatchesData = null;
    globalGithubUrl = "";
    globalUserProfile = null;

    writeJson(STORE_KEYS.repoData, null);
    writeJson(STORE_KEYS.matchesData, null);
    writeText(STORE_KEYS.githubUrl, "");
    writeJson(STORE_KEYS.userProfile, null);
    writeJson(STORE_KEYS.selectedIssue, null);
    setAppContext({
      repoData: null,
      matchesData: null,
      githubUrl: "",
      userProfile: null,
      selectedIssue: null,
    });
  };

  const handleAnalyze = async (url, profile) => {
    persistBaseContext(url, profile);
    setError(null);
    navigate("/loading");

    try {
      const analyzeResult = await analyzeRepo(url, profile);
      persistAnalyzeData(analyzeResult);
      navigate("/dashboard");

      try {
        const matchResult = await matchIssues(url, profile);
        persistMatchesData(matchResult);
      } catch (matchErr) {
        console.warn("Match issues failed:", matchErr.message);
        persistMatchesData(null);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to analyze repository. Please check the URL and try again.");
      clearSessionContext();
      navigate("/");
    }
  };

  const handleSelectIssue = (issue) => {
    const issueId = issue.issue_id || issue.number || 0;
    writeJson(STORE_KEYS.selectedIssue, issue);
    setAppContext((prev) => ({ ...prev, selectedIssue: issue }));
    navigate(`/issue/${issueId}`);
  };

  const handleBackToDashboard = () => {
    navigate("/dashboard");
  };

  const handleBackToLanding = () => {
    clearSessionContext();
    setError(null);
    navigate("/");
  };

  return (
    <div className="app">
      <div className="global-navbar">
        <div className="navbar-left">
          <div
            className="navbar-brand"
            onClick={handleBackToLanding}
            style={{ cursor: "pointer" }}
          >
            <img src="/icons/image.png" alt="Logo" className="navbar-logo" style={{ width: "24px", height: "24px", filter: "brightness(0) invert(1)" }} />
            <span>
              Repo<span className="navbar-accent">Atlas</span>
            </span>
          </div>
        </div>
        <div className="navbar-right">
          <button className="navbar-auth-btn">Signup / Login</button>
          <button className="navbar-profile-btn">
            <User size={20} />
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route
            path="/"
            element={
              <motion.div
                key="landing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Landing onAnalyze={handleAnalyze} error={error} />
              </motion.div>
            }
          />

          <Route
            path="/loading"
            element={
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <LoadingScreen />
              </motion.div>
            }
          />

          <Route
            path="/dashboard"
            element={
              hasDashboardData ? (
                <motion.div
                  key="dashboard"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <Dashboard
                    data={appContext.repoData}
                    matches={appContext.matchesData}
                    githubUrl={appContext.githubUrl}
                    userProfile={appContext.userProfile}
                    onSelectIssue={handleSelectIssue}
                    onBack={handleBackToLanding}
                  />
                </motion.div>
              ) : (
                <Navigate to="/" replace />
              )
            }
          />

          <Route
            path="/issue/:issueId"
            element={
              <motion.div
                key="issue"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <IssuePageWrapper
                  githubUrl={appContext.githubUrl}
                  userProfile={appContext.userProfile}
                  selectedIssue={appContext.selectedIssue}
                  onBack={handleBackToDashboard}
                />
              </motion.div>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </div>
  );
}

function IssuePageWrapper({ githubUrl, userProfile, selectedIssue, onBack }) {
  const navigate = useNavigate();
  const { issueId } = useParams();
  const issue = selectedIssue || readJson(STORE_KEYS.selectedIssue);

  if (!issue || !githubUrl || !userProfile) {
    return <Navigate to="/dashboard" replace />;
  }

  const currentId = String(issue.issue_id || issue.number || "");
  if (issueId && currentId && issueId !== currentId) {
    writeJson(STORE_KEYS.selectedIssue, issue);
    navigate(`/issue/${currentId}`, { replace: true });
    return null;
  }

  return (
    <IssuePage
      issue={issue}
      githubUrl={githubUrl}
      userProfile={userProfile}
      onBack={onBack}
    />
  );
}

export default App;
