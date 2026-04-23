import React, { useState, useEffect } from 'react';
import { useLanguage } from '../components/LanguageContext';
import { API_URL } from '../utils/apiBase';

const SystemAudit = () => {
  const [snapshot, setSnapshot] = useState(null);
  const [auditNotes, setAuditNotes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copyStatus, setCopyStatus] = useState("📋 Copy Full Report");
  const { t } = useLanguage();

  const fetchSnapshot = async () => {
    setLoading(true);
    try {
      const snapRes = await fetch(`${API_URL}/audit/snapshot`);
      const snapData = await snapRes.json();
      setSnapshot(snapData);
      
      const notesRes = await fetch(`${API_URL}/audit/notes`);
      const notesData = await notesRes.json();
      setAuditNotes(notesData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSnapshot();
  }, []);

  const copyToClipboard = () => {
    if (!snapshot) return;
    navigator.clipboard.writeText(JSON.stringify(snapshot, null, 2));
    setCopyStatus("✅ Copied!");
    setTimeout(() => setCopyStatus("📋 Copy Full Report"), 2000);
  };

  const copyAIBriefing = () => {
    if (!snapshot) return;
    
    const h = snapshot.health || {};
    const p = snapshot.performance || {};
    const c = snapshot.configs || {};
    
    const report = `
=== 🏛️ QBIT-BOT SOVEREIGN v4.5 EXECUTIVE BRIEFING ===
Time: ${snapshot.timestamp}
Account: ${h.server} | Balance: $${h.balance?.toLocaleString()} | Equity: $${h.equity?.toLocaleString()}
Drawdown: $${h.drawdown?.toFixed(2)} (${((h.drawdown/h.balance)*100 || 0).toFixed(2)}%)

--- 📈 PERFORMANCE (LAST 30 DAYS) ---
Net Profit: $${p.total_profit}
Win Rate: ${p.win_rate}%
Total Trades: ${p.total_executions}
Breakdown: ${JSON.stringify(p.breakdown)}

--- ⚡ ENGINES & CONFIGS ---
- SCALPER: RSI ${c.scalper?.rsi_oversold}/${c.scalper?.rsi_overbought} | SL: ${c.scalper?.sl_points}
- SWING: Confidence > ${c.swing?.min_confidence}%
- SNIPER: Armed: ${c.sniper?.is_armed}

--- 🧠 AI AUDIT INSIGHTS ---
- Health Score: ${auditNotes?.overall_health_score}/100
- Strategic Note: ${auditNotes?.strategic_note}
- Suggested Tweaks: ${auditNotes?.suggested_tweaks?.join(', ')}

--- 📔 RECENT JOURNAL ---
${snapshot.recent_history?.map(t => `[${t.time}] ${t.symbol}: $${t.profit}`).join('\n')}

--- 📡 ACTIVE EXPOSURE ---
${snapshot.active_positions?.map(p => `${p.symbol} ${p.type} (${p.volume}): $${p.profit}`).join('\n') || 'No active trades.'}
===================================================
    `.trim();

    navigator.clipboard.writeText(report);
    alert(t('briefing_copied') || "✅ AI Briefing Copied! Paste it to Gemini for analysis.");
  };

  return (
    <div className="space-y-8 animate-in fade-in zoom-in duration-500 pb-20">
      
      {/* 🛡️ Header: AI Diagnostic Hub */}
      <div className="bg-slate-900/40 backdrop-blur-3xl p-10 rounded-[48px] border border-white/5 shadow-2xl relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[100px] -z-10 group-hover:bg-emerald-500/10 transition-all duration-1000"></div>
        <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            <div className="space-y-3 text-center md:text-left">
                <h1 className="text-4xl font-black text-white flex items-center gap-4 justify-center md:justify-start">
                    🕵️ {t('ai_audit_center') || 'AI Diagnostic & Audit Hub'}
                    <span className="text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full animate-pulse border border-emerald-500/20">LIVE SCAN</span>
                </h1>
                <p className="text-slate-400 text-lg font-bold tracking-widest uppercase italic">{t('ai_audit_desc') || 'Full System Snapshot for Gemini Autonomous Tuning'}</p>
            </div>
            <div className="flex gap-4">
                <button 
                  onClick={fetchSnapshot}
                  className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white rounded-[24px] font-black tracking-widest uppercase transition-all active:scale-95 border border-white/10"
                >
                  🔄 {t('refresh_scan') || 'Refresh Scan'}
                </button>
                <button 
                  onClick={copyToClipboard}
                  className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white rounded-[24px] font-black tracking-widest uppercase transition-all active:scale-95 border border-white/10"
                >
                  {copyStatus}
                </button>
                <button 
                  onClick={copyAIBriefing}
                  className="px-8 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-[24px] font-black tracking-widest uppercase transition-all active:scale-95 shadow-2xl shadow-emerald-500/20 border border-emerald-400/30"
                >
                  📋 {t('copy_ai_briefing') || 'Copy AI Briefing'}
                </button>
            </div>
        </div>
      </div>

      {/* 🤖 Gemini 2.0 Flash: Sovereign Audit Insights */}
      {auditNotes && (
        <div className="bg-gradient-to-br from-indigo-600/20 via-slate-900/40 to-purple-500/10 backdrop-blur-3xl p-10 rounded-[48px] border border-indigo-500/20 shadow-3xl animate-in slide-in-from-top-10 duration-1000">
            <div className="flex flex-col md:flex-row gap-10">
                <div className="md:w-1/3 space-y-6">
                    <div className="w-20 h-20 bg-indigo-500 rounded-[24px] flex items-center justify-center text-3xl shadow-lg shadow-indigo-500/40">⚡</div>
                    <div>
                        <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Gemini 2.5 Flash</h2>
                        <p className="text-slate-500 font-bold uppercase text-xs tracking-widest mt-1">Sovereign Audit Engine</p>
                    </div>
                    <div className="space-y-2">
                        <div className="flex justify-between items-center text-sm font-black text-slate-400 uppercase tracking-widest">
                            <span>Health Score</span>
                            <span className="text-emerald-400">{auditNotes.overall_health_score}/100</span>
                        </div>
                        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500" style={{width: `${auditNotes.overall_health_score}%`}}></div>
                        </div>
                    </div>
                </div>
                <div className="md:w-2/3 space-y-8">
                    <div className="bg-white/5 p-8 rounded-[32px] border border-white/5 relative">
                        <div className="absolute -top-3 -left-3 px-4 py-1 bg-indigo-500 text-[10px] font-black uppercase tracking-widest rounded-lg">Strategic Note</div>
                        <p className="text-xl text-indigo-100 leading-relaxed font-medium italic">
                            "{auditNotes.strategic_note}"
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                            <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.3em] pl-2">Identified Patterns</h3>
                            <div className="space-y-2">
                                {auditNotes.identified_patterns?.map((p, i) => (
                                    <div key={i} className="flex items-center gap-3 bg-white/5 p-4 rounded-2xl border border-white/5 text-sm text-slate-300">
                                        <span className="text-indigo-400">●</span> {p}
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="space-y-4">
                            <h3 className="text-xs font-black uppercase text-slate-500 tracking-[0.3em] pl-2">Suggested Tweaks</h3>
                            <div className="space-y-2">
                                {auditNotes.suggested_tweaks?.map((t, i) => (
                                    <div key={i} className="flex items-center gap-3 bg-indigo-500/10 p-4 rounded-2xl border border-indigo-500/20 text-sm text-indigo-100">
                                        <span className="text-emerald-400">⚡</span> {t}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      )}

      {!snapshot && loading ? (
          <div className="py-40 text-center space-y-4">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-slate-500 font-black tracking-[0.3em] uppercase">{t('diagnostic_in_progress') || 'Capturing System Memory...'}</p>
          </div>
      ) : (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
              
              {/* Left Side: System Metadata */}
              <div className="xl:col-span-8 space-y-8">
                  {snapshot?.warnings?.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/25 rounded-[28px] p-6 space-y-2">
                      <h3 className="text-amber-400 font-black uppercase text-xs tracking-widest">Config drift / warnings</h3>
                      <ul className="list-disc pl-5 text-amber-100/90 text-sm space-y-1">
                        {snapshot.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {/* JSON Code Wall */}
                  <div className="bg-slate-950/80 backdrop-blur-3xl rounded-[40px] border border-white/5 shadow-3xl relative overflow-hidden font-mono text-sm">
                      <div className="p-6 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                          <span className="text-slate-500 font-black tracking-widest uppercase">system_snapshot.json</span>
                          <span className="text-[10px] text-emerald-500 font-black uppercase tracking-widest">{snapshot?.timestamp}</span>
                      </div>
                      <div className="p-8 max-h-[800px] overflow-auto custom-scrollbar">
                           <pre className="text-indigo-300">
                               {JSON.stringify(snapshot, null, 2)}
                           </pre>
                      </div>
                  </div>
              </div>

              {/* Right Side: Quick Analysis Cards */}
              <div className="xl:col-span-4 space-y-8">
                  
                  {/* Health Card */}
                  <div className="bg-slate-900/60 backdrop-blur-xl p-8 rounded-[40px] border border-white/5 shadow-2xl space-y-6">
                      <h3 className="text-base font-black uppercase tracking-widest text-slate-500 border-b border-white/5 pb-4">Core Health Monitor</h3>
                      <div className="space-y-4">
                          <div className="flex justify-between items-center">
                              <span className="text-slate-400 font-bold">Connectivity</span>
                              <span className={snapshot?.health?.is_connected ? 'text-emerald-400 font-black' : 'text-rose-400 font-black'}>{snapshot?.health?.is_connected ? '● STABLE' : '● OFFLINE'}</span>
                          </div>
                          <div className="flex justify-between items-center">
                              <span className="text-slate-400 font-bold">Equity Level</span>
                              <span className="text-white font-mono font-black">${snapshot?.health?.equity?.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between items-center">
                              <span className="text-slate-400 font-bold">Current Exposure</span>
                              <span className="text-indigo-400 font-black">{snapshot?.active_positions?.length} Positions</span>
                          </div>
                      </div>
                  </div>

                  {/* AI Intervention Logic */}
                  <div className="bg-indigo-600/10 backdrop-blur-xl p-8 rounded-[40px] border border-indigo-500/20 shadow-2xl space-y-4">
                      <div className="w-12 h-12 bg-indigo-500 rounded-2xl flex items-center justify-center text-2xl mb-2">🧠</div>
                      <h3 className="text-lg font-black text-white uppercase tracking-widest">Autonomous Advice</h3>
                      <p className="text-slate-300 text-sm leading-relaxed italic border-l-2 border-indigo-500 pl-4 py-2 bg-indigo-500/5">
                          "{snapshot?.active_positions?.length > 0 ? "Analyzing correlation risks across current exposures. Recommendation: Wait for Waterfall Logic confirmation." : "Healthy system state. Ready for next session scan."}"
                      </p>
                  </div>

                  {/* Log Stream Shortlist */}
                  <div className="bg-slate-900/40 p-8 rounded-[40px] border border-white/5 space-y-4">
                      <h3 className="text-xs font-black uppercase tracking-[0.3em] text-slate-600">Recent Log Tail</h3>
                      <div className="space-y-2 max-h-[200px] overflow-hide text-[11px] font-mono text-slate-500">
                          {snapshot?.terminal_logs?.slice(-5).map((log, i) => (
                              <div key={i} className="truncate border-b border-white/5 pb-1 last:border-0">{log}</div>
                          ))}
                      </div>
                  </div>
              </div>
          </div>
      )}
    </div>
  );
};

export default SystemAudit;
