import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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

  const handleAnalyze = async (url, profile) => {
    setPage("loading");
    setGithubUrl(url);
    setUserProfile(profile);
    setError(null);
    try {
      const analyzeResult = await analyzeRepo(url, profile);
      setRepoData(analyzeResult);
      setPage("dashboard");
      try {
        const matchResult = await matchIssues(url, profile);
        setMatchesData(matchResult);
      } catch (matchErr) {
        console.warn("Match issues failed:", matchErr.message);
        setMatchesData(null);
      }
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

  return (
    <div className="app">
      <AnimatePresence mode="wait">
        {page === "landing" && (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Landing onAnalyze={handleAnalyze} error={error} />
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


