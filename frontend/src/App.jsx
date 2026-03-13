import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Globe, User } from "lucide-react";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import IssuePage from "./pages/IssuePage";
import LoadingScreen from "./components/LoadingScreen";
import { analyzeRepo, matchIssues } from "./services/api";
import "./App.css";

function App() {
  const [page, setPage] = useState("landing");
  const [repoData, setRepoData] = useState(null);
  const [matchesData, setMatchesData] = useState(null);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [userProfile, setUserProfile] = useState(null);
  const [error, setError] = useState(null);
  const [landingStep, setLandingStep] = useState(0);

  const handleAnalyze = async (url, profile) => {
    setPage("loading");
    setGithubUrl(url);
    setUserProfile(profile);
    setError(null);
    try {
      const [analyzeResult, matchResult] = await Promise.all([
        analyzeRepo(url, profile),
        matchIssues(url, profile),
      ]);
      setRepoData(analyzeResult);
      setMatchesData(matchResult);
      setPage("dashboard");
    } catch (err) {
      console.error(err);
      setError("Failed to analyze repository. Please check the URL and try again.");
      setPage("landing");
    }
  };

  const handleSelectIssue = (issue) => {
    setSelectedIssue(issue);
    setPage("issue");
  };

  const handleBackToDashboard = () => {
    setSelectedIssue(null);
    setPage("dashboard");
  };

  const handleBackToLanding = () => {
    setRepoData(null);
    setMatchesData(null);
    setSelectedIssue(null);
    setError(null);
    setPage("landing");
  };

  const navigateTo = (destination, targetStep = 0) => {
    if (destination === "landing") {
      if (page !== "landing") {
        handleBackToLanding();
      }
      setLandingStep(targetStep);
    } else if (destination === "dashboard" && repoData) {
      setPage("dashboard");
    }
    setIsSidebarOpen(false);
  };

  return (
    <div className="app">
      <div className="global-navbar">
        <div className="navbar-left">
          <div className="navbar-brand">
            <Globe size={20} className="navbar-logo" />
            <span>Repo<span className="navbar-accent">Atlas</span></span>
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
        {page === "landing" && (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Landing 
              onAnalyze={handleAnalyze} 
              error={error} 
              externalStep={landingStep}
              onStepChange={setLandingStep}
            />
          </motion.div>
        )}

        {page === "loading" && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <LoadingScreen />
          </motion.div>
        )}

        {page === "dashboard" && repoData && (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Dashboard
              data={repoData}
              matches={matchesData}
              githubUrl={githubUrl}
              userProfile={userProfile}
              onSelectIssue={handleSelectIssue}
              onBack={handleBackToLanding}
            />
          </motion.div>
        )}

        {page === "issue" && selectedIssue && (
          <motion.div
            key="issue"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <IssuePage
              issue={selectedIssue}
              githubUrl={githubUrl}
              userProfile={userProfile}
              onBack={handleBackToDashboard}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
