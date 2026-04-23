import React, { useState, useEffect } from 'react';
import ExposureTable from '../components/ExposureTable';
import TerminalConsole from '../components/TerminalConsole';
import HistoryPanel from '../components/HistoryPanel';
import MarketWatch from '../components/MarketWatch';
import { useLanguage } from '../components/LanguageContext';
import BrokerControlPanel from '../components/BrokerControlPanel';
import { API_URL } from '../utils/apiBase';

const MainDashboard = ({ 
  account, positions, closePosition, terminalLogs, history, period, setPeriod, copyHistory, market,
  prices, prevPrices, aiFeed, activeAccount, session
}) => {
  const [globalBalance, setGlobalBalance] = useState(100.0);
  const [saveStatus, setSaveStatus] = useState("apply_capital");
  const [regimes, setRegimes] = useState({});
  const [auditNotes, setAuditNotes] = useState(null);
  const [journal, setJournal] = useState([]);
  const { t } = useLanguage();

  useEffect(() => {
    fetch(`${API_URL}/global-config`)
      .then(r => r.ok ? r.json() : null)
      .then(data => data && setGlobalBalance(data.virtual_balance))
      .catch(() => {});
    
    const fetchData = () => {
        const accId = activeAccount?.id || "default";
        
        fetch(`${API_URL}/regimes?account_id=${accId}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => data && setRegimes(data))
            .catch(() => {});
        
        fetch(`${API_URL}/audit/notes?account_id=${accId}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => data && setAuditNotes(data))
            .catch(() => {});

        fetch(`${API_URL}/trading/journal?account_id=${accId}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => data && setJournal(data))
            .catch(() => {});
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const saveGlobalConfig = async () => {
    setSaveStatus("Saving...");
    try {
      await fetch(`${API_URL}/global-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ virtual_balance: globalBalance })
      });
      setSaveStatus("✅ Applied!");
    } catch {
      setSaveStatus("error");
    } finally {
      setTimeout(() => setSaveStatus("apply_capital"), 2000);
    }
  };

  const drawdownPct = account?.balance > 0 ? ((account.balance - account.equity) / account.balance * 100) : 0;

  return (
    <div className="space-y-8 animate-in fade-in zoom-in duration-500">
      
      {/* ═══ AI Sovereign Strategic Banner ═══ */}
      {auditNotes && (
        <div className="bg-indigo-600/20 backdrop-blur-3xl p-6 rounded-[32px] border border-indigo-500/30 flex items-center gap-6 animate-pulse-slow">
           <div className={`p-4 rounded-2xl font-black text-2xl ${auditNotes.overall_health_score < 40 ? 'bg-red-500 text-white' : 'bg-emerald-500 text-white'}`}>
              {auditNotes.overall_health_score}%
           </div>
           <div className="flex-1">
              <h3 className="text-indigo-400 font-black uppercase tracking-widest text-sm mb-1">🧠 {t('sovereign_strategic_insight')}</h3>
              <p className="text-white font-bold">{auditNotes.strategic_note}</p>
           </div>
           {auditNotes.suggested_tweaks?.length > 0 && (
             <div className="hidden md:block bg-white/5 px-4 py-2 rounded-xl border border-white/10 text-xs font-bold text-slate-400">
                {t('active_tweaks')}: {auditNotes.suggested_tweaks.length}
             </div>
           )}
        </div>
      )}

      {/* ═══ Sovereign Control & Global Liquidity Hub ═══ */}
      <div className="bg-slate-900/80 backdrop-blur-3xl p-10 rounded-[48px] border border-white/10 shadow-3xl relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 blur-[100px] -z-10 group-hover:bg-indigo-500/20 transition-all duration-1000"></div>
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-10">
          <div className="space-y-3">
            <h2 className="text-3xl font-black text-white flex items-center gap-4">
              {t('global_control')}
              <span className="text-base bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-4 py-1.5 rounded-2xl font-black tracking-[0.2em] uppercase shadow-lg shadow-indigo-500/10">
                {t('v3_5_institutional')}
              </span>
            </h2>
            <p className="text-slate-400 text-lg font-bold uppercase tracking-widest">{t('global_control_desc')}</p>
          </div>

          <div className="bg-white/5 p-8 rounded-[32px] border border-white/10 flex flex-col md:flex-row items-center gap-8 shadow-inner ring-1 ring-white/5">
            <div className="flex flex-col">
              <span className="text-sm text-slate-500 font-black uppercase tracking-[0.3em] mb-2">{t('demo_capital')}</span>
              <div className="flex items-center gap-2">
                 <span className="text-2xl font-black text-indigo-400">$</span>
                 <input 
                    type="number" value={globalBalance} 
                    onChange={e => setGlobalBalance(parseFloat(e.target.value))}
                    className="bg-transparent text-3xl font-black text-white outline-none w-36 placeholder:text-slate-700"
                 />
              </div>
            </div>
            <button 
              onClick={saveGlobalConfig}
              className="px-10 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-[24px] font-black text-base tracking-[0.2em] uppercase transition-all active:scale-95 shadow-2xl shadow-indigo-500/40 border border-indigo-400/30"
            >
              {saveStatus === "apply_capital" ? t('apply_capital') : 
               saveStatus === "Saving..." ? t('saving') : 
               saveStatus === "✅ Applied!" ? t('applied') : t('error')}
            </button>
          </div>
        </div>
      </div>

      {/* ═══ Account Detail Summary ═══ */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-900/40 backdrop-blur-3xl p-8 rounded-[32px] border border-white/5 shadow-2xl">
          <p className="text-slate-500 text-base font-black uppercase tracking-[0.2em] mb-2">{t('account_balance')}</p>
          <p className="text-3xl font-black text-white">
            {(account?.balance || 0).toLocaleString()} <span className="text-base text-slate-500 font-bold ml-1">{account?.currency}</span>
          </p>
        </div>
        <div className="bg-slate-900/40 backdrop-blur-3xl p-8 rounded-[32px] border border-white/5 shadow-2xl">
          <p className="text-slate-500 text-base font-black uppercase tracking-[0.2em] mb-2">{t('equity')}</p>
          <p className={`text-3xl font-black ${(account?.equity || 0) >= (account?.balance || 0) ? 'text-emerald-400' : 'text-rose-400'}`}>
            {(account?.equity || 0).toLocaleString()}
          </p>
        </div>
        <div className="bg-slate-900/40 backdrop-blur-3xl p-8 rounded-[32px] border border-white/5 shadow-2xl">
          <p className="text-slate-500 text-base font-black uppercase tracking-[0.2em] mb-1">{t('account_info')}</p>
          <p className="text-base font-black text-white truncate">{account?.name === 'Demo Account' ? t('demo_account') : account?.name || t('loading')}</p>
          <p className="text-base text-slate-600 font-bold uppercase tracking-widest">{account?.server}</p>
        </div>
        <div className="bg-slate-900/40 backdrop-blur-3xl p-8 rounded-[32px] border border-white/5 shadow-2xl flex flex-col justify-center">
          <p className="text-slate-500 text-base font-black uppercase tracking-[0.2em] mb-2">{t('market_engine_status')}</p>
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full animate-pulse ${
              market?.mt5_market_open === true ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 
              market?.mt5_market_open === false ? 'bg-rose-500 shadow-[0_0_10px_#f43f5e]' : 'bg-slate-500'
            }`}></div>
            <p className={`text-base font-black uppercase tracking-widest ${market?.color || 'text-slate-500'}`}>
                {market?.mt5_market_open === true && market?.status?.includes("Live")
                  ? market.status.replace("Live — ", `${t('live')} — `)
                  : market?.mt5_market_open === false
                  ? (market?.status || t('mt5_market_stopped'))
                  : market?.status?.includes("Closed")
                  ? market.status.replace("Closed — ", `${t('closed')} — `)
                  : market?.status || t('checking')}
            </p>
          </div>
        </div>
      </div>
      {/* 🛡️ Sovereign Health Monitor (Phase 4.5) */}
      <div className="bg-slate-900/60 backdrop-blur-3xl p-10 rounded-[48px] border border-white/5 shadow-2xl relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-transparent -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
        <div className="flex flex-col md:flex-row justify-between items-center gap-10">
            <div className="flex-1 space-y-4 w-full">
                <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                        <h2 className="text-sm font-black uppercase tracking-[0.3em] text-slate-500">{t('liquidity_health')}</h2>
                        <span className="text-2xl font-black text-white">{t('equity_shield')}</span>
                    </div>
                    <span className="text-base font-mono font-black text-slate-500 tracking-widest">{t('max_limit_5')}</span>
                </div>
                <div className="h-4 w-full bg-white/5 rounded-full overflow-hidden border border-white/5 p-1 ring-1 ring-white/5">
                    <div 
                        className={`h-full rounded-full transition-all duration-1000 ${drawdownPct > 4 ? 'bg-gradient-to-r from-rose-600 to-rose-400 shadow-[0_0_20px_rgba(244,63,94,0.4)]' : 'bg-gradient-to-r from-emerald-600 to-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)]'}`}
                        style={{ width: `${Math.max(2, Math.min(100, drawdownPct * 20))}%` }}
                    ></div>
                </div>
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${drawdownPct > 4 ? 'bg-rose-500 animate-ping' : 'bg-emerald-500'}`}></div>
                        <span className="text-xs font-black text-slate-500 uppercase tracking-widest">{drawdownPct > 4 ? 'CRITICAL RISK' : 'STABLE LIQUIDITY'}</span>
                    </div>
                    <p className="text-lg text-slate-400 font-bold uppercase tracking-widest">
                        {t('current_drawdown')} <span className={`font-black text-2xl ml-2 ${drawdownPct > 1 ? 'text-rose-400' : 'text-white'}`}>{drawdownPct.toFixed(2)}%</span>
                    </p>
                </div>
            </div>
            
            {drawdownPct > 5 ? (
                <button 
                  onClick={() => fetch(`${API_URL}/unlock-system`, { method: 'POST' }).then(() => window.location.reload())}
                  className="px-12 py-5 bg-rose-600 hover:bg-rose-500 text-white rounded-[32px] font-black text-lg tracking-[0.2em] uppercase shadow-2xl shadow-rose-500/30 animate-pulse border border-rose-400/30 transition-all hover:scale-105"
                >
                  {t('reset_shield')}
                </button>
            ) : market?.mt5_market_open === false ? (
                <div className="px-10 py-5 bg-rose-500/10 border border-rose-500/25 text-rose-300 rounded-[32px] font-black text-sm tracking-[0.15em] uppercase flex items-center gap-3 shadow-xl backdrop-blur-3xl text-center leading-relaxed">
                    <span className="w-2.5 h-2.5 bg-rose-500 rounded-full animate-pulse shrink-0"></span>
                    {t('mt5_no_quotes')}
                </div>
            ) : (
                <div className="px-10 py-5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-[32px] font-black text-base tracking-[0.2em] uppercase flex items-center gap-3 shadow-xl backdrop-blur-3xl">
                    <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse"></span>
                    {t('system_protected')}
                </div>
            )}
        </div>
      </div>

      {/* 📜 Sovereign Decision Journal (Phase 4.5) */}
      <div className="bg-slate-900/60 backdrop-blur-3xl p-10 rounded-[48px] border border-white/5 shadow-2xl">
        <div className="flex justify-between items-center mb-8">
            <h2 className="text-sm font-black uppercase tracking-[0.3em] text-slate-500 flex items-center gap-4">
              <span className="w-1.5 h-6 bg-indigo-500 rounded-full"></span>
              {t('audit_journal')}
            </h2>
            <div className="px-4 py-1.5 bg-white/5 rounded-xl border border-white/10 flex items-center gap-3">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t('live_audit')}</span>
            </div>
        </div>
        <div className="space-y-4 max-h-[400px] overflow-y-auto pr-6 custom-scrollbar">
            {(terminalLogs || []).filter(l => {
                const msg = typeof l === 'string' ? l : (l?.msg || "");
                return msg.includes("[JOURNAL]");
            }).slice(-15).reverse().map((log, idx) => {
                const msg = typeof log === 'string' ? log : (log?.msg || "");
                const parts = msg.split("]");
                const content = parts.length > 1 ? parts.slice(1).join("]") : msg;
                const isEntry = content.includes("ENTRY") || content.includes("OPEN");
                const isBlock = content.includes("BLOCK") || content.includes("SKIP") || content.includes("Closed");
                const isAlert = content.includes("PAUSE") || content.includes("Emergency");
                
                return (
                    <div key={idx} className="bg-white/[0.01] border border-white/5 p-5 rounded-3xl flex items-center justify-between group hover:bg-white/[0.03] hover:border-white/10 transition-all">
                        <div className="flex items-center gap-5">
                            <div className={`w-3 h-3 rounded-full shadow-lg ${isEntry ? 'bg-emerald-400 shadow-emerald-500/40' : isAlert ? 'bg-rose-500 shadow-rose-500/40 animate-pulse' : isBlock ? 'bg-amber-400 shadow-amber-500/40' : 'bg-slate-600'}`}></div>
                            <span className={`text-base font-mono font-bold tracking-tight ${isAlert ? 'text-rose-400' : isEntry ? 'text-emerald-300' : 'text-slate-300'}`}>{content.trim()}</span>
                        </div>
                        <span className="text-[10px] font-black text-slate-700 uppercase tracking-widest">{typeof log === 'object' ? log.time : ''}</span>
                    </div>
                );
            })}
            {(!terminalLogs || terminalLogs.filter(l => {
                const msg = typeof l === 'string' ? l : (l?.msg || "");
                return msg.includes("[JOURNAL]");
            }).length === 0) && (
                <div className="text-center py-16 opacity-20 flex flex-col items-center gap-4">
                    <span className="text-4xl text-slate-600">⚖️</span>
                    <span className="text-lg font-bold tracking-widest italic">{t('awaiting_logic')}</span>
                </div>
            )}
        </div>
      </div>

      {/* 🤖 Gemini CLI Insights — New Intervention Radar */}
      {aiFeed && aiFeed.some(item => item.reason?.includes("Gemini CLI:")) && (
        <div className="bg-gradient-to-r from-indigo-500/20 to-purple-500/20 backdrop-blur-3xl p-8 rounded-[40px] border border-indigo-500/30 shadow-2xl relative overflow-hidden group animate-pulse-slow">
          <div className="flex flex-col md:flex-row items-center gap-6">
            <div className="w-16 h-16 bg-indigo-500 rounded-3xl flex items-center justify-center shadow-lg shadow-indigo-500/40 shrink-0">
              <span className="text-2xl font-black text-white">AI</span>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-lg font-black uppercase tracking-widest text-white">{t('gemini_cli_analyst') || 'Gemini CLI Analyst'}</h2>
                <span className="bg-white/10 px-3 py-0.5 rounded-full text-xs font-black text-indigo-300 uppercase tracking-widest border border-white/5">NEW ADVICE</span>
              </div>
              <p className="text-slate-200 text-base font-medium leading-relaxed">
                {aiFeed.find(item => item.reason?.includes("Gemini CLI:"))?.reason.replace("Gemini CLI: ", "")}
              </p>
            </div>
            <div className="text-right">
              <span className="text-base font-mono text-indigo-400 font-bold">
                {aiFeed.find(item => item.reason?.includes("Gemini CLI:"))?.time}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 📡 Institutional Matrix Radar — v4.5 Sovereign */}
      <div className="bg-slate-900/40 backdrop-blur-3xl p-10 rounded-[48px] border border-white/10 shadow-3xl relative overflow-hidden">
        <div className="flex justify-between items-center mb-10">
            <h2 className="text-2xl font-black uppercase text-white flex items-center gap-4">
              {t('market_regime_radar')}
              <span className="text-base bg-white/5 px-4 py-1 rounded-xl border border-white/10 font-black tracking-widest text-slate-500 uppercase">{t('institutional_dist')}</span>
            </h2>
            <div className="flex items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/5">
                <span className="text-xs font-black text-slate-500 uppercase tracking-widest">{t('global_pulse')}</span>
                <div className="flex gap-1">
                    {[1,2,3,4,5].map(i => <div key={i} className="w-1.5 h-4 bg-emerald-500/40 rounded-full animate-pulse" style={{animationDelay: `${i*150}ms`}}></div>)}
                </div>
            </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Object.entries(regimes || {}).map(([sym, data]) => {
                const isTrending = data.regime?.includes("TRENDING");
                const isRanging = data.regime === "RANGING";
                const bias = data.bias || "NEUTRAL";
                
                // Conflict Detection: Bullish bias in Down trend or vice-versa
                const hasConflict = (bias === "BULLISH" && data.regime?.includes("DOWN")) || (bias === "BEARISH" && data.regime?.includes("UP"));
                
                const biasAr = bias === "BULLISH" ? t('bullish') : (bias === "BEARISH" ? t('bearish') : t('neutral'));
                const biasColor = bias === "BULLISH" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : (bias === "BEARISH" ? "text-rose-400 bg-rose-500/10 border-rose-500/20" : "text-slate-500 bg-white/5 border-white/5");
                const summaryColor = (data.summary || "").includes('Buy') ? 'text-emerald-500' : (data.summary || "").includes('Sell') ? 'text-rose-500' : 'text-slate-500';

                return (
                    <div key={sym} className={`bg-white/[0.02] border p-6 rounded-[32px] flex flex-col gap-4 group hover:bg-white/[0.04] transition-all relative overflow-hidden ${hasConflict ? 'border-amber-500/30' : 'border-white/5 hover:border-white/20'}`}>
                        {hasConflict && <div className="absolute top-0 right-0 left-0 h-1 bg-amber-500/50 animate-pulse"></div>}
                        
                        <div className="flex justify-between items-start">
                            <div className="flex flex-col">
                                <span className="text-2xl font-black text-white tracking-widest uppercase group-hover:text-indigo-400 transition-colors">{sym}</span>
                                <span className={`text-[12px] font-black uppercase tracking-widest mt-1 ${isTrending ? 'text-amber-400' : (isRanging ? 'text-indigo-400' : 'text-slate-500')}`}>
                                    {data.regime?.includes("TRENDING_UP") ? t('uptrend') : data.regime?.includes("TRENDING_DOWN") ? t('downtrend') : data.regime === 'RANGING' ? t('ranging') : t('undefined')}
                                </span>
                            </div>
                            <span className={`text-[11px] px-3 py-1.5 rounded-xl font-black tracking-widest border shadow-lg ${biasColor}`}>
                                {biasAr}
                            </span>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 border-y border-white/5 py-4">
                            <div className="flex flex-col">
                                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-1">{t('confluence') || 'Matrix'}</span>
                                <div className="flex items-center gap-2">
                                    <span className={`text-base font-black uppercase ${data.confluence?.score >= 70 ? (data.confluence.confluence === 'BUY' ? 'text-emerald-500' : 'text-rose-500') : 'text-slate-500'}`}>
                                        {data.confluence?.confluence || 'NEUTRAL'}
                                    </span>
                                    <span className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded border border-white/10 text-slate-400">{data.confluence?.score || 0}%</span>
                                </div>
                            </div>
                            <div className="flex flex-col items-end text-right">
                                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-1">PIVOT</span>
                                <span className="text-base font-black text-white font-mono">{data.pivot}</span>
                            </div>
                        </div>

                        <div className="flex justify-between items-center bg-black/40 p-3 rounded-2xl border border-white/5">
                            <div className="flex flex-col">
                                <span className="text-[10px] text-slate-600 font-black tracking-[0.2em] uppercase">ADX</span>
                                <span className="text-sm text-white font-mono font-black">{data.adx || 0}</span>
                            </div>
                            {hasConflict && (
                                <div className="group/hint relative">
                                    <span className="text-amber-500 animate-pulse">⚠️</span>
                                    <div className="absolute bottom-full right-0 mb-2 w-32 hidden group-hover/hint:block bg-amber-600 text-white text-[10px] font-black p-2 rounded-xl shadow-2xl z-50">
                                        {t('conflict_warning')}
                                    </div>
                                </div>
                            )}
                            <div className="flex flex-col items-end">
                                <span className="text-[10px] text-slate-600 font-black tracking-[0.2em] uppercase">ATR</span>
                                <span className="text-sm text-white font-mono font-black">{data.atr || 0}</span>
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
      </div>

      {/* 📊 High-Performance Grid Layout */}
      <BrokerControlPanel session={session} activeAccount={activeAccount} />
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
        
        {/* Left Pillar: Execution & Audit (8 Cols) */}
        <div className="xl:col-span-8 space-y-8">
          <ExposureTable positions={positions} closePosition={closePosition} />
          <TerminalConsole logs={terminalLogs} />
          <HistoryPanel 
            history={history} 
            period={period} 
            setPeriod={setPeriod} 
            copyHistory={copyHistory} 
            copyStatus="📋 Copy" 
          />
        </div>

        {/* Right Pillar: Execution & Management (4 Cols) */}
        <div className="xl:col-span-4 space-y-8">
            {/* 📋 Live Execution Logic Trace */}
            <div className="bg-slate-900/40 backdrop-blur-3xl p-8 rounded-[48px] border border-white/5 shadow-2xl space-y-6">
                <div className="flex justify-between items-center">
                    <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
                        <span className="w-2 h-8 bg-emerald-500 rounded-full"></span>
                        {t('live_logic_trace')}
                    </h3>
                    <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full uppercase tracking-widest animate-pulse">
                        {t('real_time')}
                    </span>
                </div>
                
                <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    {journal.length === 0 && <div className="py-10 text-center text-slate-600 font-bold uppercase tracking-widest">{t('waiting_logic')}</div>}
                    {journal.map((log, i) => (
                        <div key={i} className="bg-white/5 p-4 rounded-2xl border border-white/5 flex items-start gap-4 hover:bg-white/10 transition-all border-l-4" 
                             style={{ borderLeftColor: log.decision === 'ENTRY' ? '#10b981' : log.decision === 'EXIT' ? '#f59e0b' : '#334155' }}>
                            <div className="flex flex-col items-center min-w-[50px]">
                                <span className="text-[10px] text-slate-500 font-black">{log.timestamp.split(' ')[1]}</span>
                                <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded mt-1 ${
                                    log.decision === 'ENTRY' ? 'bg-emerald-500/20 text-emerald-400' : 
                                    (log.decision === 'SKIP' || log.decision === 'BLOCK') ? 'bg-slate-700/50 text-slate-400' : 'bg-amber-500/20 text-amber-400'
                                }`}>{log.decision}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-white font-bold text-sm truncate">
                                    <span className="text-indigo-400 mr-1">[{log.strategy}]</span> {log.symbol}
                                </p>
                                <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{log.reason}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* 📡 Confluence Heatmap */}
            <div className="bg-slate-900/40 backdrop-blur-3xl p-8 rounded-[48px] border border-white/5 shadow-2xl space-y-6">
                <h3 className="text-xl font-black text-white uppercase tracking-widest">{t('confluence_heatmap')}</h3>
                <div className="space-y-3">
                    {Object.entries(regimes).map(([sym, data]) => (
                        <div key={sym} className="bg-white/5 p-3 rounded-2xl border border-white/5 flex justify-between items-center group hover:bg-indigo-500/10 transition-all">
                            <span className="text-white font-black text-sm">{sym}</span>
                            <div className="flex items-center gap-3">
                                <div className="h-1.5 w-16 bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 transition-all" style={{ width: `${data.confluence?.score || 0}%` }}></div>
                                </div>
                                <span className="font-black text-xs text-emerald-400">{data.confluence?.score || 0}%</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Institutional Protocol */}
            <div className="bg-slate-900/60 backdrop-blur-3xl p-8 rounded-[48px] border border-white/5 shadow-2xl flex flex-col justify-center gap-6">
                <h3 className="text-base font-black uppercase tracking-widest text-slate-500">{t('institutional_protocol')}</h3>
                <div className="space-y-4">
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-400 font-bold">{t('execution_guard')}</span>
                        <span className="text-emerald-400 font-black">● {t('active')}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-400 font-bold">{t('equity_shield')}</span>
                        <span className="text-emerald-400 font-black">{t('limit_5')}</span>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default MainDashboard;
