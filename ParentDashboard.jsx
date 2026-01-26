import React, { useState, useEffect } from "react";

// Mock data simulating API response
const mockDashboardData = {
  student: {
    id: 1,
    name: "Aarav Sharma",
    age: 10,
    grade: 5,
    current_subject: "math",
    current_topic: "fractions"
  },
  dashboard: {
    total_study_time_minutes: 245,
    average_accuracy: 78.5,
    sessions_completed: 12,
    subjects_time: [
      { subject: "math", time: 4500 },
      { subject: "science", time: 3200 },
      { subject: "english", time: 2100 },
      { subject: "hindi", time: 1800 }
    ],
    topics_mastered: [
      { subject: "math", topic: "addition", mastery_level: 95 },
      { subject: "math", topic: "subtraction", mastery_level: 88 },
      { subject: "science", topic: "plants", mastery_level: 82 }
    ],
    topics_needing_attention: [
      { subject: "math", topic: "fractions", mastery_level: 45 },
      { subject: "english", topic: "grammar", mastery_level: 38 }
    ],
    recent_achievements: [
      { achievement_name: "7-Day Streak!", description: "Studied for 7 days in a row", points: 50, earned_at: "2026-01-20" },
      { achievement_name: "Quick Thinker", description: "Answered 10 questions fast", points: 30, earned_at: "2026-01-18" }
    ],
    daily_activity: [
      { date: "2026-01-16", sessions: 2, duration: 1800 },
      { date: "2026-01-17", sessions: 1, duration: 900 },
      { date: "2026-01-18", sessions: 3, duration: 2700 },
      { date: "2026-01-19", sessions: 2, duration: 2100 },
      { date: "2026-01-20", sessions: 2, duration: 1500 },
      { date: "2026-01-21", sessions: 1, duration: 1200 },
      { date: "2026-01-22", sessions: 2, duration: 1800 }
    ]
  },
  voice_message: "Namaste! I'm so happy to share that Aarav is doing wonderfully! This week, they studied for 245 minutes and achieved 78.5% accuracy. They've mastered 3 topics! You should be very proud of their progress."
};

// Subject icons and colors
const subjectConfig = {
  math: { icon: "📐", color: "#4F46E5", bgColor: "#EEF2FF", label: "गणित" },
  science: { icon: "🔬", color: "#059669", bgColor: "#ECFDF5", label: "विज्ञान" },
  english: { icon: "📚", color: "#DC2626", bgColor: "#FEF2F2", label: "English" },
  hindi: { icon: "📖", color: "#D97706", bgColor: "#FFFBEB", label: "हिंदी" },
  evs: { icon: "🌿", color: "#16A34A", bgColor: "#F0FDF4", label: "EVS" },
  social_studies: { icon: "🗺️", color: "#7C3AED", bgColor: "#F5F3FF", label: "Social" }
};

// Achievement badge colors
const achievementColors = {
  streak: "#F59E0B",
  mastery: "#8B5CF6",
  speed: "#3B82F6",
  accuracy: "#10B981"
};

export default function ParentDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [isPlaying, setIsPlaying] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setData(mockDashboardData);
      setLoading(false);
      // Show celebration if accuracy is good
      if (mockDashboardData.dashboard.average_accuracy >= 70) {
        setTimeout(() => setShowCelebration(true), 500);
        setTimeout(() => setShowCelebration(false), 3000);
      }
    }, 800);
  }, []);

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins} min`;
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return `${hours}h ${remainingMins}m`;
  };

  const getProgressColor = (value) => {
    if (value >= 80) return "#10B981";
    if (value >= 60) return "#F59E0B";
    return "#EF4444";
  };

  const getEmotionalGradient = (accuracy) => {
    if (accuracy >= 80) return "linear-gradient(135deg, #10B981 0%, #059669 100%)";
    if (accuracy >= 60) return "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)";
    return "linear-gradient(135deg, #F87171 0%, #DC2626 100%)";
  };

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.loadingSpinner}>
          <div style={styles.spinnerRing}></div>
          <div style={styles.loadingText}>Loading your child's journey...</div>
        </div>
      </div>
    );
  }

  const { student, dashboard, voice_message } = data;
  const maxDuration = Math.max(...dashboard.daily_activity.map(d => d.duration));

  return (
    <div style={styles.container}>
      {/* Celebration Overlay */}
      {showCelebration && (
        <div style={styles.celebrationOverlay}>
          <div style={styles.celebrationContent}>
            🎉 Great Progress! 🎉
          </div>
        </div>
      )}

      {/* Header with emotional gradient */}
      <header style={{...styles.header, background: getEmotionalGradient(dashboard.average_accuracy)}}>
        <div style={styles.headerContent}>
          <div style={styles.studentAvatar}>
            {student.name.charAt(0)}
          </div>
          <div style={styles.headerInfo}>
            <h1 style={styles.studentName}>{student.name}</h1>
            <p style={styles.studentMeta}>
              Class {student.grade} • Age {student.age} • {subjectConfig[student.current_subject]?.label || student.current_subject}
            </p>
          </div>
          <div style={styles.streakBadge}>
            🔥 7 Day Streak
          </div>
        </div>
      </header>

      {/* Voice Message Card - Emotional Connection */}
      <div style={styles.voiceCard}>
        <div style={styles.voiceHeader}>
          <span style={styles.voiceIcon}>🎧</span>
          <span style={styles.voiceTitle}>आज की Progress Update</span>
        </div>
        <p style={styles.voiceText}>{voice_message}</p>
        <button 
          style={{...styles.playButton, ...(isPlaying ? styles.playButtonActive : {})}}
          onClick={() => setIsPlaying(!isPlaying)}
        >
          {isPlaying ? "⏸️ Pause" : "▶️ Play Voice Message"}
        </button>
      </div>

      {/* Quick Stats Grid */}
      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>⏱️</div>
          <div style={styles.statValue}>{dashboard.total_study_time_minutes}</div>
          <div style={styles.statLabel}>Minutes This Week</div>
          <div style={styles.statTrend}>↑ 15% from last week</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>🎯</div>
          <div style={{...styles.statValue, color: getProgressColor(dashboard.average_accuracy)}}>
            {dashboard.average_accuracy}%
          </div>
          <div style={styles.statLabel}>Accuracy</div>
          <div style={styles.statTrend}>Great improvement!</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>📚</div>
          <div style={styles.statValue}>{dashboard.sessions_completed}</div>
          <div style={styles.statLabel}>Sessions</div>
          <div style={styles.statTrend}>{Math.round(dashboard.sessions_completed / 7)} per day avg</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>⭐</div>
          <div style={styles.statValue}>{dashboard.topics_mastered.length}</div>
          <div style={styles.statLabel}>Topics Mastered</div>
          <div style={styles.statTrend}>+2 this week!</div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={styles.tabContainer}>
        {["overview", "subjects", "achievements"].map(tab => (
          <button
            key={tab}
            style={{...styles.tab, ...(activeTab === tab ? styles.tabActive : {})}}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "overview" && "📊 "}
            {tab === "subjects" && "📘 "}
            {tab === "achievements" && "🏆 "}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={styles.tabContent}>
        {activeTab === "overview" && (
          <>
            {/* Weekly Activity Chart */}
            <div style={styles.section}>
              <h2 style={styles.sectionTitle}>📅 Weekly Activity</h2>
              <div style={styles.activityChart}>
                {dashboard.daily_activity.map((day, idx) => (
                  <div key={idx} style={styles.activityDay}>
                    <div style={styles.activityBarContainer}>
                      <div 
                        style={{
                          ...styles.activityBar,
                          height: `${(day.duration / maxDuration) * 100}%`,
                          background: day.sessions > 0 ? 
                            `linear-gradient(180deg, #4F46E5 0%, #818CF8 100%)` : 
                            "#E5E7EB"
                        }}
                      >
                        <span style={styles.activityValue}>{formatDuration(day.duration)}</span>
                      </div>
                    </div>
                    <span style={styles.activityLabel}>
                      {new Date(day.date).toLocaleDateString('en-IN', { weekday: 'short' })}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Topics Progress */}
            <div style={styles.section}>
              <h2 style={styles.sectionTitle}>✅ Mastered Topics</h2>
              <div style={styles.topicsList}>
                {dashboard.topics_mastered.map((topic, idx) => (
                  <div key={idx} style={styles.topicCard}>
                    <span style={styles.topicIcon}>{subjectConfig[topic.subject]?.icon || "📚"}</span>
                    <div style={styles.topicInfo}>
                      <span style={styles.topicName}>{topic.topic.replace(/_/g, ' ')}</span>
                      <div style={styles.progressBar}>
                        <div style={{
                          ...styles.progressFill,
                          width: `${topic.mastery_level}%`,
                          background: getProgressColor(topic.mastery_level)
                        }}></div>
                      </div>
                    </div>
                    <span style={{...styles.masteryBadge, background: getProgressColor(topic.mastery_level)}}>
                      {topic.mastery_level}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Needs Attention */}
            {dashboard.topics_needing_attention.length > 0 && (
              <div style={styles.section}>
                <h2 style={styles.sectionTitle}>🎯 Focus Areas</h2>
                <p style={styles.focusSubtext}>These topics need a little more practice</p>
                <div style={styles.topicsList}>
                  {dashboard.topics_needing_attention.map((topic, idx) => (
                    <div key={idx} style={{...styles.topicCard, borderLeft: "4px solid #F59E0B"}}>
                      <span style={styles.topicIcon}>{subjectConfig[topic.subject]?.icon || "📚"}</span>
                      <div style={styles.topicInfo}>
                        <span style={styles.topicName}>{topic.topic.replace(/_/g, ' ')}</span>
                        <div style={styles.progressBar}>
                          <div style={{
                            ...styles.progressFill,
                            width: `${topic.mastery_level}%`,
                            background: "#F59E0B"
                          }}></div>
                        </div>
                      </div>
                      <button style={styles.practiceButton}>Practice Now</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === "subjects" && (
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>📘 Subject-wise Time</h2>
            <div style={styles.subjectGrid}>
              {dashboard.subjects_time.map((subj, idx) => {
                const config = subjectConfig[subj.subject] || { icon: "📚", color: "#6B7280", bgColor: "#F3F4F6", label: subj.subject };
                const percentage = (subj.time / dashboard.subjects_time.reduce((a, b) => a + b.time, 0)) * 100;
                return (
                  <div key={idx} style={{...styles.subjectCard, background: config.bgColor}}>
                    <div style={{...styles.subjectIcon, background: config.color}}>{config.icon}</div>
                    <div style={styles.subjectInfo}>
                      <span style={styles.subjectName}>{config.label}</span>
                      <span style={styles.subjectTime}>{formatDuration(subj.time)}</span>
                    </div>
                    <div style={styles.subjectPercentage}>
                      <div style={{...styles.subjectRing, background: `conic-gradient(${config.color} ${percentage}%, #E5E7EB ${percentage}%)`}}>
                        <span style={styles.subjectPercText}>{Math.round(percentage)}%</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === "achievements" && (
          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>🏆 Recent Achievements</h2>
            <div style={styles.achievementsList}>
              {dashboard.recent_achievements.map((ach, idx) => (
                <div key={idx} style={styles.achievementCard}>
                  <div style={{...styles.achievementBadge, background: achievementColors[ach.achievement_name.includes("Streak") ? "streak" : "mastery"] || "#6B7280"}}>
                    {ach.achievement_name.includes("Streak") ? "🔥" : 
                     ach.achievement_name.includes("Quick") ? "⚡" : 
                     ach.achievement_name.includes("Perfect") ? "💯" : "⭐"}
                  </div>
                  <div style={styles.achievementInfo}>
                    <span style={styles.achievementName}>{ach.achievement_name}</span>
                    <span style={styles.achievementDesc}>{ach.description}</span>
                    <span style={styles.achievementDate}>
                      {new Date(ach.earned_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </span>
                  </div>
                  <div style={styles.achievementPoints}>
                    <span style={styles.pointsValue}>+{ach.points}</span>
                    <span style={styles.pointsLabel}>pts</span>
                  </div>
                </div>
              ))}
            </div>
            <div style={styles.totalPoints}>
              <span>Total Points Earned</span>
              <span style={styles.totalPointsValue}>
                {dashboard.recent_achievements.reduce((sum, a) => sum + a.points, 0)} ⭐
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div style={styles.footer}>
        <button style={styles.primaryButton}>
          📞 Talk to Teacher
        </button>
        <button style={styles.secondaryButton}>
          📊 Full Report
        </button>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes celebration {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  );
}

const styles = {
  container: {
    fontFamily: "'Poppins', 'Noto Sans Devanagari', sans-serif",
    background: "linear-gradient(180deg, #F8FAFC 0%, #EEF2FF 100%)",
    minHeight: "100vh",
    maxWidth: "480px",
    margin: "0 auto",
    position: "relative",
    paddingBottom: "100px"
  },
  loadingContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    background: "#F8FAFC"
  },
  loadingSpinner: {
    textAlign: "center"
  },
  spinnerRing: {
    width: "50px",
    height: "50px",
    border: "4px solid #E5E7EB",
    borderTop: "4px solid #4F46E5",
    borderRadius: "50%",
    margin: "0 auto 16px",
    animation: "spin 1s linear infinite"
  },
  loadingText: {
    color: "#6B7280",
    fontSize: "14px"
  },
  celebrationOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: "rgba(0,0,0,0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000
  },
  celebrationContent: {
    background: "white",
    padding: "32px 48px",
    borderRadius: "24px",
    fontSize: "28px",
    fontWeight: "700",
    animation: "celebration 0.5s ease-in-out infinite",
    boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)"
  },
  header: {
    padding: "24px 20px",
    borderRadius: "0 0 32px 32px",
    color: "white",
    boxShadow: "0 10px 40px -10px rgba(0,0,0,0.2)"
  },
  headerContent: {
    display: "flex",
    alignItems: "center",
    gap: "16px"
  },
  studentAvatar: {
    width: "56px",
    height: "56px",
    borderRadius: "16px",
    background: "rgba(255,255,255,0.25)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "24px",
    fontWeight: "700",
    backdropFilter: "blur(10px)"
  },
  headerInfo: {
    flex: 1
  },
  studentName: {
    fontSize: "22px",
    fontWeight: "700",
    margin: 0
  },
  studentMeta: {
    fontSize: "13px",
    opacity: 0.9,
    margin: "4px 0 0"
  },
  streakBadge: {
    background: "rgba(255,255,255,0.2)",
    padding: "8px 12px",
    borderRadius: "20px",
    fontSize: "13px",
    fontWeight: "600",
    backdropFilter: "blur(10px)"
  },
  voiceCard: {
    margin: "20px",
    padding: "20px",
    background: "white",
    borderRadius: "20px",
    boxShadow: "0 4px 20px rgba(0,0,0,0.06)",
    animation: "fadeIn 0.5s ease-out"
  },
  voiceHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "12px"
  },
  voiceIcon: {
    fontSize: "20px"
  },
  voiceTitle: {
    fontSize: "15px",
    fontWeight: "600",
    color: "#1F2937"
  },
  voiceText: {
    fontSize: "14px",
    color: "#4B5563",
    lineHeight: 1.6,
    marginBottom: "16px"
  },
  playButton: {
    width: "100%",
    padding: "14px",
    background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
    color: "white",
    border: "none",
    borderRadius: "12px",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s"
  },
  playButtonActive: {
    background: "linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)"
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: "12px",
    padding: "0 20px",
    marginBottom: "24px"
  },
  statCard: {
    background: "white",
    padding: "16px",
    borderRadius: "16px",
    textAlign: "center",
    boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
    animation: "fadeIn 0.5s ease-out"
  },
  statIcon: {
    fontSize: "24px",
    marginBottom: "8px"
  },
  statValue: {
    fontSize: "28px",
    fontWeight: "700",
    color: "#1F2937"
  },
  statLabel: {
    fontSize: "12px",
    color: "#6B7280",
    marginTop: "4px"
  },
  statTrend: {
    fontSize: "11px",
    color: "#10B981",
    marginTop: "8px",
    fontWeight: "500"
  },
  tabContainer: {
    display: "flex",
    gap: "8px",
    padding: "0 20px",
    marginBottom: "20px"
  },
  tab: {
    flex: 1,
    padding: "12px 8px",
    border: "none",
    borderRadius: "12px",
    fontSize: "13px",
    fontWeight: "600",
    cursor: "pointer",
    background: "white",
    color: "#6B7280",
    transition: "all 0.2s"
  },
  tabActive: {
    background: "#4F46E5",
    color: "white"
  },
  tabContent: {
    padding: "0 20px"
  },
  section: {
    background: "white",
    borderRadius: "20px",
    padding: "20px",
    marginBottom: "16px",
    boxShadow: "0 2px 12px rgba(0,0,0,0.04)"
  },
  sectionTitle: {
    fontSize: "16px",
    fontWeight: "700",
    color: "#1F2937",
    margin: "0 0 16px"
  },
  activityChart: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-end",
    height: "140px",
    gap: "8px"
  },
  activityDay: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px"
  },
  activityBarContainer: {
    height: "100px",
    width: "100%",
    display: "flex",
    alignItems: "flex-end",
    justifyContent: "center"
  },
  activityBar: {
    width: "100%",
    maxWidth: "36px",
    borderRadius: "8px 8px 4px 4px",
    minHeight: "8px",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "center",
    paddingTop: "4px",
    transition: "height 0.5s ease-out"
  },
  activityValue: {
    fontSize: "9px",
    color: "white",
    fontWeight: "600",
    whiteSpace: "nowrap"
  },
  activityLabel: {
    fontSize: "11px",
    color: "#6B7280",
    fontWeight: "500"
  },
  topicsList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  topicCard: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px",
    background: "#F8FAFC",
    borderRadius: "12px"
  },
  topicIcon: {
    fontSize: "24px"
  },
  topicInfo: {
    flex: 1
  },
  topicName: {
    display: "block",
    fontSize: "14px",
    fontWeight: "600",
    color: "#1F2937",
    textTransform: "capitalize",
    marginBottom: "6px"
  },
  progressBar: {
    height: "6px",
    background: "#E5E7EB",
    borderRadius: "3px",
    overflow: "hidden"
  },
  progressFill: {
    height: "100%",
    borderRadius: "3px",
    transition: "width 0.5s ease-out"
  },
  masteryBadge: {
    padding: "4px 10px",
    borderRadius: "12px",
    color: "white",
    fontSize: "12px",
    fontWeight: "600"
  },
  focusSubtext: {
    fontSize: "13px",
    color: "#6B7280",
    margin: "-8px 0 16px"
  },
  practiceButton: {
    padding: "8px 14px",
    background: "#F59E0B",
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer"
  },
  subjectGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  subjectCard: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    padding: "16px",
    borderRadius: "16px"
  },
  subjectIcon: {
    width: "48px",
    height: "48px",
    borderRadius: "12px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "24px",
    color: "white"
  },
  subjectInfo: {
    flex: 1
  },
  subjectName: {
    display: "block",
    fontSize: "15px",
    fontWeight: "600",
    color: "#1F2937"
  },
  subjectTime: {
    fontSize: "13px",
    color: "#6B7280"
  },
  subjectPercentage: {
    width: "50px",
    height: "50px"
  },
  subjectRing: {
    width: "50px",
    height: "50px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center"
  },
  subjectPercText: {
    fontSize: "12px",
    fontWeight: "700",
    color: "#1F2937",
    background: "white",
    padding: "8px",
    borderRadius: "50%"
  },
  achievementsList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  achievementCard: {
    display: "flex",
    alignItems: "center",
    gap: "14px",
    padding: "14px",
    background: "#F8FAFC",
    borderRadius: "14px"
  },
  achievementBadge: {
    width: "48px",
    height: "48px",
    borderRadius: "12px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "24px"
  },
  achievementInfo: {
    flex: 1
  },
  achievementName: {
    display: "block",
    fontSize: "14px",
    fontWeight: "600",
    color: "#1F2937"
  },
  achievementDesc: {
    display: "block",
    fontSize: "12px",
    color: "#6B7280",
    margin: "2px 0"
  },
  achievementDate: {
    fontSize: "11px",
    color: "#9CA3AF"
  },
  achievementPoints: {
    textAlign: "center"
  },
  pointsValue: {
    display: "block",
    fontSize: "18px",
    fontWeight: "700",
    color: "#F59E0B"
  },
  pointsLabel: {
    fontSize: "11px",
    color: "#9CA3AF"
  },
  totalPoints: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: "16px",
    padding: "16px",
    background: "linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)",
    borderRadius: "12px",
    fontWeight: "600"
  },
  totalPointsValue: {
    fontSize: "20px",
    color: "#D97706"
  },
  footer: {
    position: "fixed",
    bottom: 0,
    left: "50%",
    transform: "translateX(-50%)",
    width: "100%",
    maxWidth: "480px",
    display: "flex",
    gap: "12px",
    padding: "16px 20px",
    background: "white",
    boxShadow: "0 -4px 20px rgba(0,0,0,0.08)",
    borderRadius: "24px 24px 0 0"
  },
  primaryButton: {
    flex: 1,
    padding: "16px",
    background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
    color: "white",
    border: "none",
    borderRadius: "14px",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "pointer"
  },
  secondaryButton: {
    flex: 1,
    padding: "16px",
    background: "#F3F4F6",
    color: "#4B5563",
    border: "none",
    borderRadius: "14px",
    fontSize: "15px",
    fontWeight: "600",
    cursor: "pointer"
  }
};
