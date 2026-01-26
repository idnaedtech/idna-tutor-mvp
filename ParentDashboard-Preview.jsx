import React, { useState, useEffect } from "react";

const mockDashboardData = {
  student: { id: 1, name: "Aarav Sharma", age: 10, grade: 5, current_subject: "math", current_topic: "fractions" },
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

const subjectConfig = {
  math: { icon: "📐", color: "#4F46E5", bgColor: "#EEF2FF", label: "गणित" },
  science: { icon: "🔬", color: "#059669", bgColor: "#ECFDF5", label: "विज्ञान" },
  english: { icon: "📚", color: "#DC2626", bgColor: "#FEF2F2", label: "English" },
  hindi: { icon: "📖", color: "#D97706", bgColor: "#FFFBEB", label: "हिंदी" },
  evs: { icon: "🌿", color: "#16A34A", bgColor: "#F0FDF4", label: "EVS" }
};

export default function ParentDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [isPlaying, setIsPlaying] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);

  useEffect(() => {
    setTimeout(() => {
      setData(mockDashboardData);
      setLoading(false);
      if (mockDashboardData.dashboard.average_accuracy >= 70) {
        setTimeout(() => setShowCelebration(true), 500);
        setTimeout(() => setShowCelebration(false), 3000);
      }
    }, 800);
  }, []);

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  };

  const getProgressColor = (value) => value >= 80 ? "#10B981" : value >= 60 ? "#F59E0B" : "#EF4444";
  const getEmotionalGradient = (accuracy) => accuracy >= 80 ? "linear-gradient(135deg, #10B981 0%, #059669 100%)" : accuracy >= 60 ? "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)" : "linear-gradient(135deg, #F87171 0%, #DC2626 100%)";

  if (loading) return (
    <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",background:"#F8FAFC",fontFamily:"system-ui"}}>
      <div style={{textAlign:"center"}}>
        <div style={{width:50,height:50,border:"4px solid #E5E7EB",borderTop:"4px solid #4F46E5",borderRadius:"50%",margin:"0 auto 16px",animation:"spin 1s linear infinite"}}></div>
        <div style={{color:"#6B7280",fontSize:14}}>Loading your child's journey...</div>
      </div>
      <style>{`@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}`}</style>
    </div>
  );

  const { student, dashboard, voice_message } = data;
  const maxDuration = Math.max(...dashboard.daily_activity.map(d => d.duration));

  return (
    <div style={{fontFamily:"'Segoe UI',system-ui,sans-serif",background:"linear-gradient(180deg,#F8FAFC 0%,#EEF2FF 100%)",minHeight:"100vh",maxWidth:480,margin:"0 auto",position:"relative",paddingBottom:100}}>
      {showCelebration && (
        <div style={{position:"fixed",top:0,left:0,right:0,bottom:0,background:"rgba(0,0,0,0.3)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000}}>
          <div style={{background:"white",padding:"32px 48px",borderRadius:24,fontSize:28,fontWeight:700,animation:"celebration 0.5s ease-in-out infinite",boxShadow:"0 25px 50px -12px rgba(0,0,0,0.25)"}}>🎉 Great Progress! 🎉</div>
        </div>
      )}
      
      <header style={{padding:"24px 20px",borderRadius:"0 0 32px 32px",color:"white",boxShadow:"0 10px 40px -10px rgba(0,0,0,0.2)",background:getEmotionalGradient(dashboard.average_accuracy)}}>
        <div style={{display:"flex",alignItems:"center",gap:16}}>
          <div style={{width:56,height:56,borderRadius:16,background:"rgba(255,255,255,0.25)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:24,fontWeight:700}}>{student.name.charAt(0)}</div>
          <div style={{flex:1}}>
            <h1 style={{fontSize:22,fontWeight:700,margin:0}}>{student.name}</h1>
            <p style={{fontSize:13,opacity:0.9,margin:"4px 0 0"}}>Class {student.grade} • Age {student.age} • {subjectConfig[student.current_subject]?.label}</p>
          </div>
          <div style={{background:"rgba(255,255,255,0.2)",padding:"8px 12px",borderRadius:20,fontSize:13,fontWeight:600}}>🔥 7 Day</div>
        </div>
      </header>

      <div style={{margin:20,padding:20,background:"white",borderRadius:20,boxShadow:"0 4px 20px rgba(0,0,0,0.06)"}}>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:12}}>
          <span style={{fontSize:20}}>🎧</span>
          <span style={{fontSize:15,fontWeight:600,color:"#1F2937"}}>आज की Progress Update</span>
        </div>
        <p style={{fontSize:14,color:"#4B5563",lineHeight:1.6,marginBottom:16}}>{voice_message}</p>
        <button onClick={() => setIsPlaying(!isPlaying)} style={{width:"100%",padding:14,background:"linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)",color:"white",border:"none",borderRadius:12,fontSize:15,fontWeight:600,cursor:"pointer"}}>
          {isPlaying ? "⏸️ Pause" : "▶️ Play Voice Message"}
        </button>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:12,padding:"0 20px",marginBottom:24}}>
        {[
          {icon:"⏱️",value:dashboard.total_study_time_minutes,label:"Minutes This Week",trend:"↑ 15%"},
          {icon:"🎯",value:`${dashboard.average_accuracy}%`,label:"Accuracy",trend:"Great!",color:getProgressColor(dashboard.average_accuracy)},
          {icon:"📚",value:dashboard.sessions_completed,label:"Sessions",trend:`${Math.round(dashboard.sessions_completed/7)}/day`},
          {icon:"⭐",value:dashboard.topics_mastered.length,label:"Mastered",trend:"+2 this week!"}
        ].map((stat,i) => (
          <div key={i} style={{background:"white",padding:16,borderRadius:16,textAlign:"center",boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
            <div style={{fontSize:24,marginBottom:8}}>{stat.icon}</div>
            <div style={{fontSize:28,fontWeight:700,color:stat.color||"#1F2937"}}>{stat.value}</div>
            <div style={{fontSize:12,color:"#6B7280",marginTop:4}}>{stat.label}</div>
            <div style={{fontSize:11,color:"#10B981",marginTop:8,fontWeight:500}}>{stat.trend}</div>
          </div>
        ))}
      </div>

      <div style={{display:"flex",gap:8,padding:"0 20px",marginBottom:20}}>
        {["overview","subjects","achievements"].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{flex:1,padding:"12px 8px",border:"none",borderRadius:12,fontSize:13,fontWeight:600,cursor:"pointer",background:activeTab===tab?"#4F46E5":"white",color:activeTab===tab?"white":"#6B7280"}}>
            {tab==="overview"?"📊 ":tab==="subjects"?"📘 ":"🏆 "}{tab.charAt(0).toUpperCase()+tab.slice(1)}
          </button>
        ))}
      </div>

      <div style={{padding:"0 20px"}}>
        {activeTab === "overview" && (
          <>
            <div style={{background:"white",borderRadius:20,padding:20,marginBottom:16,boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
              <h2 style={{fontSize:16,fontWeight:700,color:"#1F2937",margin:"0 0 16px"}}>📅 Weekly Activity</h2>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-end",height:140,gap:8}}>
                {dashboard.daily_activity.map((day,idx) => (
                  <div key={idx} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:8}}>
                    <div style={{height:100,width:"100%",display:"flex",alignItems:"flex-end",justifyContent:"center"}}>
                      <div style={{width:"100%",maxWidth:36,borderRadius:"8px 8px 4px 4px",minHeight:8,height:`${(day.duration/maxDuration)*100}%`,background:day.sessions>0?"linear-gradient(180deg,#4F46E5 0%,#818CF8 100%)":"#E5E7EB",display:"flex",alignItems:"flex-start",justifyContent:"center",paddingTop:4}}>
                        <span style={{fontSize:9,color:"white",fontWeight:600}}>{formatDuration(day.duration)}</span>
                      </div>
                    </div>
                    <span style={{fontSize:11,color:"#6B7280",fontWeight:500}}>{new Date(day.date).toLocaleDateString('en-IN',{weekday:'short'})}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{background:"white",borderRadius:20,padding:20,marginBottom:16,boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
              <h2 style={{fontSize:16,fontWeight:700,color:"#1F2937",margin:"0 0 16px"}}>✅ Mastered Topics</h2>
              {dashboard.topics_mastered.map((topic,idx) => (
                <div key={idx} style={{display:"flex",alignItems:"center",gap:12,padding:12,background:"#F8FAFC",borderRadius:12,marginBottom:8}}>
                  <span style={{fontSize:24}}>{subjectConfig[topic.subject]?.icon||"📚"}</span>
                  <div style={{flex:1}}>
                    <span style={{display:"block",fontSize:14,fontWeight:600,color:"#1F2937",textTransform:"capitalize",marginBottom:6}}>{topic.topic.replace(/_/g,' ')}</span>
                    <div style={{height:6,background:"#E5E7EB",borderRadius:3,overflow:"hidden"}}>
                      <div style={{height:"100%",borderRadius:3,width:`${topic.mastery_level}%`,background:getProgressColor(topic.mastery_level)}}></div>
                    </div>
                  </div>
                  <span style={{padding:"4px 10px",borderRadius:12,color:"white",fontSize:12,fontWeight:600,background:getProgressColor(topic.mastery_level)}}>{topic.mastery_level}%</span>
                </div>
              ))}
            </div>

            {dashboard.topics_needing_attention.length > 0 && (
              <div style={{background:"white",borderRadius:20,padding:20,marginBottom:16,boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
                <h2 style={{fontSize:16,fontWeight:700,color:"#1F2937",margin:"0 0 8px"}}>🎯 Focus Areas</h2>
                <p style={{fontSize:13,color:"#6B7280",margin:"0 0 16px"}}>These topics need more practice</p>
                {dashboard.topics_needing_attention.map((topic,idx) => (
                  <div key={idx} style={{display:"flex",alignItems:"center",gap:12,padding:12,background:"#F8FAFC",borderRadius:12,marginBottom:8,borderLeft:"4px solid #F59E0B"}}>
                    <span style={{fontSize:24}}>{subjectConfig[topic.subject]?.icon||"📚"}</span>
                    <div style={{flex:1}}>
                      <span style={{display:"block",fontSize:14,fontWeight:600,color:"#1F2937",textTransform:"capitalize",marginBottom:6}}>{topic.topic.replace(/_/g,' ')}</span>
                      <div style={{height:6,background:"#E5E7EB",borderRadius:3,overflow:"hidden"}}>
                        <div style={{height:"100%",borderRadius:3,width:`${topic.mastery_level}%`,background:"#F59E0B"}}></div>
                      </div>
                    </div>
                    <button style={{padding:"8px 14px",background:"#F59E0B",color:"white",border:"none",borderRadius:8,fontSize:12,fontWeight:600,cursor:"pointer"}}>Practice</button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {activeTab === "subjects" && (
          <div style={{background:"white",borderRadius:20,padding:20,boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
            <h2 style={{fontSize:16,fontWeight:700,color:"#1F2937",margin:"0 0 16px"}}>📘 Subject-wise Time</h2>
            {dashboard.subjects_time.map((subj,idx) => {
              const config = subjectConfig[subj.subject]||{icon:"📚",color:"#6B7280",bgColor:"#F3F4F6",label:subj.subject};
              const percentage = (subj.time/dashboard.subjects_time.reduce((a,b) => a+b.time,0))*100;
              return (
                <div key={idx} style={{display:"flex",alignItems:"center",gap:16,padding:16,borderRadius:16,marginBottom:12,background:config.bgColor}}>
                  <div style={{width:48,height:48,borderRadius:12,display:"flex",alignItems:"center",justifyContent:"center",fontSize:24,color:"white",background:config.color}}>{config.icon}</div>
                  <div style={{flex:1}}>
                    <span style={{display:"block",fontSize:15,fontWeight:600,color:"#1F2937"}}>{config.label}</span>
                    <span style={{fontSize:13,color:"#6B7280"}}>{formatDuration(subj.time)}</span>
                  </div>
                  <div style={{width:50,height:50,borderRadius:"50%",display:"flex",alignItems:"center",justifyContent:"center",background:`conic-gradient(${config.color} ${percentage}%, #E5E7EB ${percentage}%)`}}>
                    <span style={{fontSize:12,fontWeight:700,color:"#1F2937",background:"white",padding:8,borderRadius:"50%"}}>{Math.round(percentage)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "achievements" && (
          <div style={{background:"white",borderRadius:20,padding:20,boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
            <h2 style={{fontSize:16,fontWeight:700,color:"#1F2937",margin:"0 0 16px"}}>🏆 Recent Achievements</h2>
            {dashboard.recent_achievements.map((ach,idx) => (
              <div key={idx} style={{display:"flex",alignItems:"center",gap:14,padding:14,background:"#F8FAFC",borderRadius:14,marginBottom:12}}>
                <div style={{width:48,height:48,borderRadius:12,display:"flex",alignItems:"center",justifyContent:"center",fontSize:24,background:ach.achievement_name.includes("Streak")?"#F59E0B":"#8B5CF6"}}>
                  {ach.achievement_name.includes("Streak")?"🔥":"⚡"}
                </div>
                <div style={{flex:1}}>
                  <span style={{display:"block",fontSize:14,fontWeight:600,color:"#1F2937"}}>{ach.achievement_name}</span>
                  <span style={{display:"block",fontSize:12,color:"#6B7280",margin:"2px 0"}}>{ach.description}</span>
                  <span style={{fontSize:11,color:"#9CA3AF"}}>{new Date(ach.earned_at).toLocaleDateString('en-IN',{day:'numeric',month:'short'})}</span>
                </div>
                <div style={{textAlign:"center"}}>
                  <span style={{display:"block",fontSize:18,fontWeight:700,color:"#F59E0B"}}>+{ach.points}</span>
                  <span style={{fontSize:11,color:"#9CA3AF"}}>pts</span>
                </div>
              </div>
            ))}
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginTop:16,padding:16,background:"linear-gradient(135deg,#FEF3C7 0%,#FDE68A 100%)",borderRadius:12,fontWeight:600}}>
              <span>Total Points Earned</span>
              <span style={{fontSize:20,color:"#D97706"}}>{dashboard.recent_achievements.reduce((sum,a) => sum+a.points,0)} ⭐</span>
            </div>
          </div>
        )}
      </div>

      <div style={{position:"fixed",bottom:0,left:"50%",transform:"translateX(-50%)",width:"100%",maxWidth:480,display:"flex",gap:12,padding:"16px 20px",background:"white",boxShadow:"0 -4px 20px rgba(0,0,0,0.08)",borderRadius:"24px 24px 0 0"}}>
        <button style={{flex:1,padding:16,background:"linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)",color:"white",border:"none",borderRadius:14,fontSize:15,fontWeight:600,cursor:"pointer"}}>📞 Talk to Teacher</button>
        <button style={{flex:1,padding:16,background:"#F3F4F6",color:"#4B5563",border:"none",borderRadius:14,fontSize:15,fontWeight:600,cursor:"pointer"}}>📊 Full Report</button>
      </div>

      <style>{`@keyframes celebration{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}`}</style>
    </div>
  );
}
