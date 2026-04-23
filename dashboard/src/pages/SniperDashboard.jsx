import React, { useState, useEffect } from 'react';
import { useLanguage } from '../components/LanguageContext';
import { API_URL } from '../utils/apiBase';

const SniperDashboard = () => {
  const { t } = useLanguage();
  
  // Sniper Config State
  const [enabled, setEnabled] = useState(false);
  const [volume, setVolume] = useState(0.05);
  const [useLimitOrders, setUseLimitOrders] = useState(true);
  const [cushion, setCushion] = useState(20);
  const [sl, setSl] = useState(300);
  const [tp, setTp] = useState(900);
  const [minConf, setMinConf] = useState(2);
  const [rsiOversold, setRsiOversold] = useState(35);
  const [rsiOverbought, setRsiOverbought] = useState(65);
  const [executionMode, setExecutionMode] = useState("pivot_bounce"); // New Strategy Mode
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  const [saveStatus, setSaveStatus] = useState("apply_settings");
  const [lastSync, setLastSync] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    fetch(`${API_URL}/sniper-config`)
      .then(r => r.json())
      .then(data => {
        setEnabled(data.enabled || false);
        setVolume(data.volume || 0.05);
        setUseLimitOrders(data.use_limit_orders ?? true);
        setCushion(data.limit_cushion_points || 20);
        setSl(data.stop_loss_points || 300);
        setTp(data.take_profit_points || 900);
        setMinConf(data.minimum_tf_confluence || 2);
        setRsiOversold(data.rsi_oversold || 35);
        setRsiOverbought(data.rsi_overbought || 65);
        setExecutionMode(data.execution_mode || "pivot_bounce");
        setLastSync(new Date().toLocaleTimeString());
        setTimeout(() => setIsInitialLoad(false), 500); // Prevent auto-save on load
      })
      .catch(console.error);
  }, []);

  // 🔄 Institutional Auto-Save System
  useEffect(() => {
     if (isInitialLoad) return;
     const timer = setTimeout(() => {
        saveConfig();
     }, 1000);
     return () => clearTimeout(timer);
  }, [volume, useLimitOrders, cushion, sl, tp, minConf, rsiOversold, rsiOverbought, executionMode]);

  const saveConfig = async (newEnabledState = null) => {
    const isEnabled = newEnabledState !== null ? newEnabledState : enabled;
    setSaveStatus("Saving...");
    try {
      const res = await fetch(`${API_URL}/sniper-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            enabled: isEnabled, 
            volume, 
            use_limit_orders: useLimitOrders,
            limit_cushion_points: cushion,
            stop_loss_points: sl,
            take_profit_points: tp,
            minimum_tf_confluence: minConf,
            rsi_oversold: rsiOversold,
            rsi_overbought: rsiOverbought,
            execution_mode: executionMode,
            active_timeframes: ["15M", "1H", "D"]
        })
      });
      if (!res.ok) throw new Error("API Error");
      
      if (newEnabledState === null) {
          setSaveStatus("✅ Auto-Saved");
      } else {
          setSaveStatus("✅ Saved");
      }
    } catch {
      setSaveStatus("error");
    } finally {
      setTimeout(() => setSaveStatus("apply_settings"), 2000);
    }
  };

  const toggleArmed = () => {
    const target = !enabled;
    setEnabled(target);
    saveConfig(target);
  };

  return (
    <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-700">
      
      {/* 🧨 Sniper Header/Status */}
      <div className="bg-slate-950/80 backdrop-blur-3xl p-10 rounded-[40px] border border-red-500/20 shadow-[0_0_50px_rgba(239,68,68,0.1)] relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-red-500/5 blur-[120px] rounded-full -mr-48 -mt-48"></div>
        
        <div className="relative flex flex-col lg:flex-row justify-between items-start lg:items-center gap-8">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-black text-white tracking-tighter uppercase">{t('tv_sniper_title') || 'TradingView Confluence Sniper'}</h1>
              <span className="text-base bg-red-500 text-white px-3 py-1 rounded-full font-black tracking-widest uppercase">{t('engine_version') || 'Engine v4.5'}</span>
            </div>
            <p className="text-slate-500 text-base font-medium max-w-xl">
              {t('tv_sniper_desc') || 'Advanced institutional engine that hunts for confluence across multiple TradingView timeframes and executes precise limit orders at daily Pivot levels (S1/R1) during extreme RSI exhaustion.'}
            </p>
          </div>

          <div className="flex items-center gap-4">
               <div className="bg-white/5 p-4 rounded-3xl border border-white/5 flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${enabled ? 'bg-red-500 animate-ping' : 'bg-slate-700'}`}></div>
                  <span className="text-base font-black uppercase text-white tracking-widest">{enabled ? t('engine_armed') : t('engine_standby')}</span>
                  <button 
                  onClick={toggleArmed}
                  className={`px-6 py-2 rounded-xl text-base font-black uppercase tracking-widest transition-all ${enabled ? 'bg-slate-800 text-white' : 'bg-red-600 text-white shadow-lg shadow-red-500/20'}`}>
                    {enabled ? t('disarm') : t('arm_sniper')}
                  </button>
               </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        
        {/* ⚙️ Core Logic Panel */}
        <div className="xl:col-span-2 bg-slate-900/40 backdrop-blur-2xl p-8 rounded-[40px] border border-white/5 shadow-2xl">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-base font-black uppercase tracking-widest text-slate-400 flex items-center gap-3">
              Institutional Logic Core
              <span className="text-base bg-white/5 px-2 py-0.5 rounded border border-white/5 font-bold normal-case text-slate-500">Live</span>
            </h2>
            <p className="text-base text-slate-600 font-bold uppercase tracking-widest">{t('last_sync')} {lastSync}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* New Tactical Strategy Selector */}
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1 md:col-span-2 border-indigo-500/20">
                <span className="text-base text-indigo-400 font-black tracking-widest uppercase">Tactical Strategy Mode</span>
                <select 
                    value={executionMode} 
                    onChange={e => setExecutionMode(e.target.value)}
                    className="bg-transparent text-xl font-black text-white outline-none [&>option]:bg-slate-900"
                >
                    <option value="pivot_bounce">Pivot Bounce (Reversion on Support/Resistance)</option>
                    <option value="momentum_breakout">Momentum Breakout (Enter on Pivot Breach)</option>
                    <option value="hybrid">Hybrid Interceptor (Dynamic)</option>
                </select>
                <p className="text-slate-500 italic mt-2 text-sm">Determines how the engine reacts when price reaches Daily Pivot zones.</p>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
                <span className="text-base text-indigo-400 font-black tracking-widest uppercase">{t('min_tf_confluence') || 'Minimum TF Confluence'}</span>
                <input 
                    type="number" value={minConf} onChange={e => setMinConf(parseInt(e.target.value))}
                    className="bg-transparent text-xl font-black text-white outline-none"
                    title={t('min_tf_desc') || 'Number of timeframes (out of 15M, 1H, Daily) that MUST agree on STRONG BUY or STRONG SELL.'}
                />
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
                <span className="text-base text-amber-500 font-black tracking-widest uppercase">{t('limit_vs_market') || 'Limit vs Market Execution'}</span>
                <select 
                    value={useLimitOrders ? "True" : "False"} 
                    onChange={e => setUseLimitOrders(e.target.value === "True")}
                    className="bg-transparent text-xl font-black text-white outline-none [&>option]:bg-slate-900"
                >
                    <option value="True">{t('limit_orders_precision') || 'Limit Orders (Precision)'}</option>
                    <option value="False">{t('market_orders_instant') || 'Market Orders (Instant)'}</option>
                </select>
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1 border-rose-500/20">
                <span className="text-base text-rose-500 font-black tracking-widest uppercase">{t('rsi_oversold') || 'RSI Exhaustion (Oversold)'}</span>
                <input 
                    type="number" value={rsiOversold} onChange={e => setRsiOversold(parseInt(e.target.value))}
                    className="bg-transparent text-xl font-black text-white outline-none"
                />
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1 border-emerald-500/20">
                <span className="text-base text-emerald-500 font-black tracking-widest uppercase">{t('rsi_overbought') || 'RSI Exhaustion (Overbought)'}</span>
                <input 
                    type="number" value={rsiOverbought} onChange={e => setRsiOverbought(parseInt(e.target.value))}
                    className="bg-transparent text-xl font-black text-white outline-none"
                />
            </div>
          </div>
        </div>

        {/* 🛠️ Sniper Configuration */}
        <div className="space-y-8">
          <div className="bg-slate-900/60 backdrop-blur-3xl p-8 rounded-[40px] border border-white/5 shadow-2xl flex flex-col gap-6">
            <h2 className="text-base font-black uppercase tracking-widest text-white mb-2">{t('engagement_criteria') || 'Risk & Targets'}</h2>
            
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
              <span className="text-base text-slate-500 font-black tracking-widest uppercase">{t('precise_lot') || 'Lot Size'}</span>
              <input 
                type="number" step="0.01" value={volume} onChange={e => setVolume(parseFloat(e.target.value))}
                className="bg-transparent text-xl font-black text-red-500 outline-none"
              />
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
              <span className="text-base text-slate-500 font-black tracking-widest uppercase">{t('take_profit_points') || 'Take Profit (Points)'}</span>
              <input 
                type="number" value={tp} onChange={e => setTp(parseInt(e.target.value))}
                className="bg-transparent text-xl font-black text-emerald-500 outline-none"
              />
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
              <span className="text-base text-slate-500 font-black tracking-widest uppercase">{t('stop_loss_points') || 'Stop Loss (Points)'}</span>
              <input 
                type="number" value={sl} onChange={e => setSl(parseInt(e.target.value))}
                className="bg-transparent text-xl font-black text-rose-500 outline-none"
              />
            </div>

            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col gap-1">
              <span className="text-base text-amber-500 font-black tracking-widest uppercase">{t('limit_cushion') || 'Limit Cushion (Spread buffer)'}</span>
              <input 
                type="number" value={cushion} onChange={e => setCushion(parseInt(e.target.value))}
                className="bg-transparent text-xl font-black text-white outline-none"
              />
            </div>

            <button 
              onClick={() => saveConfig()}
              className="w-full py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-black text-base tracking-widest uppercase transition-all shadow-lg shadow-red-500/10 active:scale-95"
            >
              {saveStatus === "apply_settings" ? t('apply_settings') || 'Apply Settings' : 
               saveStatus === "Saving..." ? t('saving') || 'Saving...' : 
               saveStatus === "✅ Saved" ? t('applied') || 'Applied' : t('error') || 'Error'}
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};

export default SniperDashboard;
