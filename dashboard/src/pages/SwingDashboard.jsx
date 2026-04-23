import React, { useState, useEffect } from 'react';
import ExposureTable from '../components/ExposureTable';
import { useLanguage } from '../components/LanguageContext';
import { API_URL } from '../utils/apiBase';

const SwingDashboard = ({ intel, positions, closePosition, account, history, market, loading }) => {
  const swingPositions = positions.filter(p => p.magic === 777777);
  
  // Swing Config State (local, persisted to backend)
  const [swingTP, setSwingTP] = useState(1500);
  const [swingSL, setSwingSL] = useState(500);
  const [swingConfidence, setSwingConfidence] = useState(80);
  const [maxTrades, setMaxTrades] = useState(1);
  const [swingTargetProfitUSD, setSwingTargetProfitUSD] = useState(2.0);
  const [saveStatus, setSaveStatus] = useState("apply_changes");
  const [globalBalance, setGlobalBalance] = useState(100.0);
  const [capitalSaveStatus, setCapitalSaveStatus] = useState("apply_capital");
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const { t } = useLanguage();

  // Load saved config from API on mount
  useEffect(() => {
    fetch(`${API_URL}/swing-config`)
      .then(r => r.ok ? r.json() : null)
      .then(cfg => {
        if (cfg) {
          setSwingTP(cfg.tp_points || 1500);
          setSwingSL(cfg.sl_points || 500);
          setSwingConfidence(cfg.min_confidence || 80);
          setMaxTrades(cfg.max_trades || 1);
          setSwingTargetProfitUSD(cfg.target_profit_usd || 2.0);
        }
        setTimeout(() => setIsInitialLoad(false), 500); // Prevent auto-save on mount
      })
      .catch(() => {});

    // Load global config
    fetch(`${API_URL}/global-config`)
      .then(r => r.ok ? r.json() : null)
      .then(data => data && setGlobalBalance(data.virtual_balance))
      .catch(() => {});
  }, []);


  // Calculate swing simulation equity
  const swingProfit = swingPositions.reduce((sum, p) => sum + (p.profit || 0), 0);

  // 🔄 Institutional Auto-Save System
  useEffect(() => {
     if (isInitialLoad) return;
     const timer = setTimeout(() => {
        saveSwingConfig(true);
     }, 1000);
     return () => clearTimeout(timer);
  }, [swingTP, swingSL, swingConfidence, maxTrades, swingTargetProfitUSD]);

  const saveSwingConfig = async (isAuto = false) => {
    if (!isAuto) setSaveStatus("Saving...");
    try {
      await fetch(`${API_URL}/swing-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          tp_points: swingTP, 
          sl_points: swingSL, 
          min_confidence: swingConfidence,
          max_trades: maxTrades,
          target_profit_usd: swingTargetProfitUSD
        })
      });
      setSaveStatus(isAuto ? "✅ Auto-Saved" : "applied");
    } catch {
      setSaveStatus("error");
    } finally {
      setTimeout(() => setSaveStatus("apply_changes"), 2000);
    }
  };

  const saveGlobalCapital = async () => {
    setCapitalSaveStatus("Saving...");
    try {
      await fetch(`${API_URL}/global-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ virtual_balance: globalBalance })
      });
      setCapitalSaveStatus("applied");
    } catch {
      setCapitalSaveStatus("error");
    } finally {
      setTimeout(() => setCapitalSaveStatus("apply_capital"), 2000);
    }
  };

  // Smart Intel Selection: Match the active Swing position if exists, otherwise fallback to top intel
  const activeSymbol = swingPositions.length > 0 ? swingPositions[0].symbol : null;
  const activeIntel = Array.isArray(intel) 
    ? (activeSymbol ? (intel.find(i => i.pair === activeSymbol) || intel[0]) : intel[0])
    : intel;

  return (
    <div className="space-y-8 animate-in fade-in zoom-in duration-500">
      
      {/* ═══ Global Capital (Demo) ═══ */}
      <div className="bg-slate-900/60 backdrop-blur-3xl p-6 rounded-[32px] border border-white/10 shadow-xl flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-4">
           <div className="w-12 h-12 bg-amber-500/10 rounded-2xl flex items-center justify-center text-2xl border border-amber-500/20">
              💰
           </div>
           <div>
              <p className="text-base text-amber-500 font-black uppercase tracking-widest">{t('global_capital_demo')}</p>
              <div className="flex items-center gap-2">
                 <span className="text-white font-black text-2xl">$</span>
                 <input 
                    type="number" value={globalBalance} 
                    onChange={e => setGlobalBalance(parseFloat(e.target.value))}
                    className="bg-transparent text-2xl font-black text-white outline-none w-24"
                 />
              </div>
           </div>
        </div>
        <button 
          onClick={saveGlobalCapital}
          className="px-10 py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-2xl font-black text-base tracking-widest uppercase transition-all shadow-lg shadow-amber-500/20 active:scale-95"
        >
          {capitalSaveStatus === "apply_capital" ? t('apply_capital') :
           capitalSaveStatus === "Saving..." ? t('saving') :
           capitalSaveStatus === "applied" ? t('applied') : t('error')}
        </button>
      </div>

      {/* ═══ Swing Macro Engine (Settings) ═══ */}
      <div className="bg-slate-900/40 backdrop-blur-3xl rounded-[40px] border border-white/5 p-8 shadow-2xl">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 mb-8">
          <div>
            <h2 className="text-xl font-black uppercase text-amber-500 flex items-center gap-3">
              {t('swing_macro_engine')}
              <span className="text-base bg-amber-500/10 text-amber-500 px-3 py-1 rounded-full border border-amber-500/10 font-black tracking-widest uppercase">
                 {t('engine_v1_2')}
              </span>
            </h2>
            <p className="text-slate-500 text-base mt-1">{t('swing_desc')}</p>
          </div>
          <button 
            onClick={saveSwingConfig}
            className="px-8 py-3 bg-amber-600 hover:bg-amber-500 text-slate-900 rounded-2xl font-black text-base tracking-widest uppercase transition-all shadow-lg shadow-amber-500/20 active:scale-95"
          >
            {saveStatus === "apply_changes" ? t('apply_changes') : 
             saveStatus === "Saving..." ? t('saving') : 
             saveStatus === "applied" ? t('applied') : t('error')}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
            <span className="text-base text-amber-500 font-black tracking-widest uppercase">{t('target_points')}</span>
            <input 
              type="number" value={swingTP} onChange={e => setSwingTP(parseInt(e.target.value))}
              className="bg-transparent text-white text-lg font-black outline-none"
            />
          </div>
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1 border-emerald-500/20">
            <span className="text-base text-emerald-500 font-black tracking-widest uppercase">{t('basket_target')}</span>
            <input 
              type="number" step="0.5" value={swingTargetProfitUSD} 
              onChange={e => setSwingTargetProfitUSD(parseFloat(e.target.value))}
              className="bg-transparent text-white text-lg font-black outline-none"
            />
          </div>
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
            <span className="text-base text-rose-500 font-black tracking-widest uppercase">{t('stop_points')}</span>
            <input 
              type="number" value={swingSL} onChange={e => setSwingSL(parseInt(e.target.value))}
              className="bg-transparent text-white text-lg font-black outline-none"
            />
          </div>
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
            <span className="text-base text-indigo-400 font-black tracking-widest uppercase">{t('min_confidence')}</span>
            <input 
              type="number" value={swingConfidence} onChange={e => setSwingConfidence(parseInt(e.target.value))}
              className="bg-transparent text-white text-lg font-black outline-none"
            />
          </div>
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
            <span className="text-base text-slate-500 font-black tracking-widest uppercase">{t('max_concurrent')}</span>
            <input 
              type="number" value={maxTrades} onChange={e => setMaxTrades(parseInt(e.target.value))}
              className="bg-transparent text-white text-lg font-black outline-none"
            />
          </div>
        </div>
      </div>

      {/* ═══ ROW 2: Pulse + Holdings ═══ */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-8 items-start">

        {/* Macro Pulse */}
        <div className="xl:col-span-2 bg-gradient-to-br from-amber-600/10 to-transparent p-8 rounded-[40px] border border-amber-500/20 shadow-2xl relative overflow-hidden group">
          <div className="absolute right-0 top-0 p-12 opacity-5 text-9xl select-none">🏛️</div>
          <h2 className="text-xl font-black uppercase tracking-[0.2em] text-amber-500 mb-8 flex items-center gap-4">
            <span className="w-3 h-3 bg-amber-500 rounded-full animate-pulse"></span>
            {t('macro_pulse')}
          </h2>
          <div className="space-y-8 relative z-10">
            <div className="space-y-6">
              <p className="text-slate-500 text-base font-black uppercase tracking-widest">{t('institutional_sentiment_matrix') || 'Institutional Sentiment Matrix'} {activeIntel?.pair ? `- ${activeIntel.pair}` : ''}</p>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-separate border-spacing-y-2">
                  <thead>
                    <tr className="text-slate-600 text-xs font-black uppercase tracking-widest">
                      <th className="px-4 py-2">{t('timeframe')}</th>
                      <th className="px-4 py-2">{t('summary')}</th>
                      <th className="px-4 py-2">{t('ma')}</th>
                      <th className="px-4 py-2">{t('oscillators')}</th>
                      <th className="px-4 py-2">{t('patterns') || 'Patterns'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {['5M', '15M', '1H', 'D'].map(tf => {
                      const data = activeIntel?.matrix?.[tf] || { summary: 'NEUTRAL', ma: 'NEUTRAL', osc: 'NEUTRAL', counts: {buy:0, sell:0, neutral:0}, indicators: {rsi:50, adx:20, atr:0}, patterns: [] };
                      const getCol = (val) => val.includes('Buy') ? 'text-emerald-400' : val.includes('Sell') ? 'text-rose-400' : 'text-slate-500';
                      
                      return (
                        <tr key={tf} className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden group hover:bg-white/[0.05] transition-all">
                          <td className="px-4 py-3">
                            <span className="font-black text-amber-500 block">{tf === 'D' ? t('daily') : tf}</span>
                            <span className="text-[10px] text-slate-600 font-bold uppercase">ATR: {data.indicators.atr}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`font-bold uppercase text-base block ${getCol(data.summary)}`}>{data.summary}</span>
                            <div className="flex gap-1 text-[10px] font-black uppercase mt-0.5">
                               <span className="text-emerald-500/60">B:{data.counts.buy}</span>
                               <span className="text-rose-500/60">S:{data.counts.sell}</span>
                               <span className="text-slate-500/60">N:{data.counts.neutral}</span>
                            </div>
                          </td>
                          <td className={`px-4 py-3 font-medium uppercase text-base ${getCol(data.ma)}`}>{data.ma}</td>
                          <td className="px-4 py-3">
                             <span className={`font-medium uppercase text-base block ${getCol(data.osc)}`}>{data.osc}</span>
                             <span className="text-[10px] text-indigo-400/60 font-black">RSI: {data.indicators.rsi} | ADX: {data.indicators.adx}</span>
                          </td>
                          <td className="px-4 py-3">
                             <div className="flex flex-wrap gap-1 max-w-[150px]">
                               {data.patterns && data.patterns.length > 0 ? data.patterns.map((p, i) => (
                                 <span key={i} className={`text-[9px] font-black px-1.5 py-0.5 rounded border uppercase tracking-tighter ${p.includes('Bullish') ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
                                   {p}
                                 </span>
                               )) : <span className="text-[10px] text-slate-700 font-black uppercase tracking-tighter">—</span>}
                             </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Confidence Bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-slate-500 text-base font-black uppercase tracking-widest">{t('confidence_level')}</p>
                <span className="text-amber-500 font-black text-base">{activeIntel?.sentiment_score || 50}%</span>
              </div>
              <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ${(activeIntel?.sentiment_score || 50) >= 80 ? 'bg-emerald-500' : (activeIntel?.sentiment_score || 50) >= 50 ? 'bg-amber-500' : 'bg-rose-500'}`}
                  style={{ width: `${activeIntel?.sentiment_score || 50}%` }}
                ></div>
              </div>
              <p className="text-base text-slate-600 mt-1">
                {t('activation_threshold')}: {swingConfidence}% — {t('bot_active_conf')} {swingConfidence}%
              </p>
            </div>

            <div className="pt-6 border-t border-white/5">
              <p className="text-amber-500/80 text-base font-medium leading-relaxed italic">
                "{activeIntel?.ai_note || t('consulting_market')}"
              </p>
            </div>

            {/* Entry Status */}
            <div className={`flex items-center gap-3 p-4 rounded-2xl border ${(activeIntel?.sentiment_score || 0) >= swingConfidence ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-slate-900/50 border-white/5'}`}>
              <div className={`w-3 h-3 rounded-full ${(activeIntel?.sentiment_score || 0) >= swingConfidence ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`}></div>
              <p className={`text-base font-black uppercase tracking-widest ${(activeIntel?.sentiment_score || 0) >= swingConfidence ? 'text-emerald-400' : 'text-slate-500'}`}>
                {(activeIntel?.sentiment_score || 0) >= swingConfidence ? t('swing_ready') : t('swing_standby')}
              </p>
            </div>
            
            {/* 🎯 Real-time Pivot Point Radar */}
            <div className="pt-6 border-t border-white/5 space-y-4">
              <p className="text-slate-500 text-base font-black uppercase tracking-widest">{t('pivot_points_radar') || 'Pivot Points Radar'} {activeIntel?.pair ? `(${activeIntel.pair})` : ''}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 {/* Classic Pivots */}
                 <div className="bg-white/[0.02] p-6 rounded-3xl border border-white/5 space-y-4">
                    <h4 className="text-amber-500 font-black text-base uppercase tracking-widest border-b border-white/5 pb-2">Classic Levels</h4>
                    <div className="grid grid-cols-3 gap-4 text-center">
                       <div className="flex flex-col"><span className="text-[10px] text-slate-600 font-bold">S2</span><span className="text-rose-400 font-mono font-bold">{activeIntel?.pivots?.classic?.s2 || '—'}</span></div>
                       <div className="flex flex-col"><span className="text-[10px] text-slate-600 font-bold">S1</span><span className="text-rose-400 font-mono font-bold">{activeIntel?.pivots?.classic?.s1 || '—'}</span></div>
                       <div className="flex flex-col bg-white/5 p-2 rounded-xl"><span className="text-[10px] text-amber-500 font-bold">PIVOT</span><span className="text-white font-mono font-bold">{activeIntel?.pivots?.classic?.pivot || '—'}</span></div>
                       <div className="flex flex-col"><span className="text-[10px] text-slate-600 font-bold">R1</span><span className="text-emerald-400 font-mono font-bold">{activeIntel?.pivots?.classic?.r1 || '—'}</span></div>
                       <div className="flex flex-col"><span className="text-[10px] text-slate-600 font-bold">R2</span><span className="text-emerald-400 font-mono font-bold">{activeIntel?.pivots?.classic?.r2 || '—'}</span></div>
                    </div>
                 </div>

                 {/* Fibonacci Pivots */}
                 <div className="bg-white/[0.02] p-6 rounded-3xl border border-white/5 space-y-4">
                    <h4 className="text-indigo-400 font-black text-base uppercase tracking-widest border-b border-white/5 pb-2">Fibonacci Levels</h4>
                    <div className="grid grid-cols-3 gap-4 text-center">
                       <div className="flex flex-col"><span className="text-[10px] text-slate-600 font-bold">S1</span><span className="text-rose-400 font-mono font-bold">{activeIntel?.pivots?.fibonacci?.s1 || '—'}</span></div>
                       <div className="flex flex-col bg-white/5 p-2 rounded-xl"><span className="text-[10px] text-indigo-400 font-bold">PIVOT</span><span className="text-white font-mono font-bold">{activeIntel?.pivots?.fibonacci?.pivot || '—'}</span></div>
                       <div className="flex flex-col"><span className="text-[10px] text-slate-600 font-bold">R1</span><span className="text-emerald-400 font-mono font-bold">{activeIntel?.pivots?.fibonacci?.r1 || '—'}</span></div>
                    </div>
                 </div>
              </div>
            </div>
          </div>
        </div>

        {/* Swing Holdings */}
        <div className="xl:col-span-3 bg-slate-900/40 backdrop-blur-3xl rounded-[40px] border border-white/5 p-8 relative overflow-hidden flex flex-col">
          <div className="absolute left-0 top-0 w-1 h-full bg-amber-500 rounded-sm"></div>
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-3">
            {t('long_term_portfolio')}
            <span className="text-base bg-amber-500/20 text-amber-400 px-3 py-1 rounded-full border border-amber-500/10 font-black tracking-widest uppercase">
              {swingPositions.length} {t('active_holds')}
            </span>
          </h2>
          <p className="text-slate-400 text-base mb-6">
            {t('swing_isolated_desc')}
          </p>

          <div className="flex-1">
            <ExposureTable positions={swingPositions} closePosition={closePosition} />
          </div>

          {swingPositions.length === 0 && (
            <div className="mt-4 py-14 border-2 border-dashed border-white/5 rounded-3xl text-center">
              <div className="text-6xl mb-4 opacity-50">🔭</div>
              <p className="text-slate-500 font-bold text-base">{t('scanning_pulse')}</p>
              <p className="text-slate-600 text-base mt-2">{t('bot_active_conf')} {swingConfidence}%</p>
            </div>
          )}

          {/* Swing P&L Summary */}
          {swingPositions.length > 0 && (
            <div className={`mt-6 p-4 rounded-2xl border flex items-center justify-between ${swingProfit >= 0 ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'}`}>
              <span className="text-base font-black uppercase text-slate-500 tracking-widest">{t('unrealized_pnl')}</span>
              <span className={`text-xl font-black ${swingProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {swingProfit >= 0 ? '+' : ''}{swingProfit.toFixed(2)} USD
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ═══ ROW 3: Strategy Info (How Swing Works) ═══ */}
      <div className="bg-white/[0.02] border border-white/5 rounded-[32px] p-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex flex-col items-center text-center gap-3 p-6 bg-white/[0.02] rounded-2xl border border-white/5">
          <div className="text-4xl">📍</div>
          <p className="text-base font-black uppercase text-amber-500 tracking-widest">{t('entry_logic')}</p>
          <p className="text-slate-400 text-base leading-relaxed">{t('entry_logic_desc1')} <strong className="text-white">"{t('strong_buy')}/{t('strong_sell')}"</strong> {t('entry_logic_desc2')} {swingConfidence}%.</p>
        </div>
        <div className="flex flex-col items-center text-center gap-3 p-6 bg-white/[0.02] rounded-2xl border border-white/5">
          <div className="text-4xl">🛡️</div>
          <p className="text-base font-black uppercase text-indigo-400 tracking-widest">{t('risk_control')}</p>
          <p className="text-slate-400 text-base leading-relaxed">{t('risk_desc1')} <strong className="text-white">Magic #777777</strong> {t('risk_desc2')} <strong className="text-white">${globalBalance}</strong>. {t('risk_desc3')} <strong className="text-white">{swingSL}</strong> {t('risk_desc4')}</p>
        </div>
        <div className="flex flex-col items-center text-center gap-3 p-6 bg-white/[0.02] rounded-2xl border border-white/5">
          <div className="text-4xl">🎯</div>
          <p className="text-base font-black uppercase text-emerald-400 tracking-widest">{t('profit_target')}</p>
          <p className="text-slate-400 text-base leading-relaxed">{t('profit_desc1')} <strong className="text-white">{swingTP}</strong> {t('profit_desc2')} <strong className="text-white">{t('profit_desc3')} ${swingTargetProfitUSD}</strong>{t('profit_desc4')}</p>
        </div>
      </div>
    </div>
  );
};

export default SwingDashboard;
