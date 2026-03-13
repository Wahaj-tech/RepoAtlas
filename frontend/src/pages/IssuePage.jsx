import ImpactPanel from "../components/ImpactPanel";

export default function IssuePage({ issue, githubUrl, userProfile, onBack }) {
  return (
    <div className="issue-page" style={{ background: "#0a0f1e", minHeight: "100vh" }}>
      <div className="issue-page-glow" />
      <ImpactPanel issue={issue} githubUrl={githubUrl} userProfile={userProfile} onBack={onBack} />
    </div>
  );
}
