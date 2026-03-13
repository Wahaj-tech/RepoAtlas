import axios from "axios";

const BASE = "http://localhost:8000/api";

const api = axios.create({
  baseURL: BASE,
  timeout: 120000,
});

export const analyzeRepo = async (githubUrl, userProfile) => {
  const response = await api.post("/analyze", {
    github_url: githubUrl,
    user_profile: userProfile,
  });
  return response.data;
};

export const matchIssues = async (githubUrl, userProfile) => {
  const response = await api.post("/match-issues", {
    github_url: githubUrl,
    user_profile: {
      ...userProfile,
      interests: userProfile.interests || ["backend"],
    },
    max_results: 5,
    label_filter: [],
  });
  return response.data;
};

export const getContributionPath = async (githubUrl, issueNumber, userProfile) => {
  const response = await api.post("/contribution-path", {
    github_url: githubUrl,
    issue_number: issueNumber,
    user_profile: {
      ...userProfile,
      interests: userProfile.interests || ["backend"],
    },
  });
  return response.data;
};

export const getImpact = async (githubUrl, filePath) => {
  const response = await api.post("/impact", {
    github_url: githubUrl,
    file_path: filePath,
  });
  return response.data;
};
