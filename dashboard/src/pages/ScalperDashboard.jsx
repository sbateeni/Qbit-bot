import React, { useState, useEffect } from 'react';
import IntelligencePanel from '../components/IntelligencePanel';
import EvolutionLab from '../components/EvolutionLab';
import { useLanguage } from '../components/LanguageContext';

const API_URL =
  import.meta.env.VITE_API_URL ||
  "/api";

const ScalperDashboard = ({ 
  insight, aiFeed, prices, prevPrices, news, evolution
}) => {
  const [config, setConfig] = useState({
    rsi_oversold: 30,
    rsi_overbought: 70,
    sl_points: 100,
    tp_points: 200,
    target_profit_usd: 2.0,
    safety_stop_usd: 1.0,
    virtual_balance: 10.0
  });
  const [saveStatus, setSaveStatus] = useState("apply_changes");
  const { t } = useLanguage();

  useEffect(() => {
    fetch(`${API_URL}/scalper-config`)
      .then(r => r.ok ? r.json() : null)
      .then(data => data && setConfig(data))
      .catch(() => {});
  }, []);

  const saveConfig = async () => {
    setSaveStatus("Saving...");
    try {
      const res = await fetch(`${API_URL}/scalper-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config)
      });
      if (res.ok) setSaveStatus("applied");
      else setSaveStatus("error");
    } catch {
      setSaveStatus("error");
    } finally {
      setTimeout(() => setSaveStatus("apply_changes"), 2000);
    }
  };

  const updateField = (field, val) => setConfig(prev => ({ ...prev, [field]: val }));

  return (
    <div className="space-y-8 animate-in fade-in zoom-in duration-500">
      
      {/* ═══ Scalper Rules Engine (Settings) ═══ */}
      <div className="bg-slate-900/40 backdrop-blur-3xl rounded-[40px] border border-white/5 p-8 shadow-2xl">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 mb-8">
          <div>
            <h2 className="text-xl font-black uppercase text-indigo-400 flex items-center gap-3">
              {t('scalper_rules_engine')}
              <span className="text-base bg-indigo-500/10 text-indigo-500 px-3 py-1 rounded-full border border-indigo-500/10 font-black tracking-widest uppercase">
                 {t('engine_version')}
              </span>
            </h2>
            <p className="text-slate-500 text-base mt-1">{t('scalper_desc')}</p>
          </div>
          <button 
            onClick={saveConfig}
            className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-black text-base tracking-widest uppercase transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
          >
            {saveStatus === "apply_changes" ? t('apply_changes') : 
             saveStatus === "Saving..." ? t('saving') : 
             saveStatus === "applied" ? t('applied') : t('error')}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {/* Target Settings */}
          <div className="space-y-4 p-6 bg-white/[0.02] rounded-3xl border border-white/5">
            <p className="text-base font-black uppercase tracking-widest text-slate-500">{t('targets_risks')}</p>
            <div className="space-y-4">
              <div className="flex justify-between items-center group">
                <span className="text-base text-slate-400">{t('target_profit')}</span>
                <input 
                  type="number" step="0.5" value={config.target_profit_usd} 
                  onChange={e => updateField('target_profit_usd', parseFloat(e.target.value))}
                  className="bg-slate-950 border border-white/5 rounded-lg px-2 py-1 text-base font-bold text-white w-20 text-right focus:border-indigo-500/50 outline-none"
                />
              </div>
              <div className="flex justify-between items-center group">
                <span className="text-base text-slate-400">{t('safety_stop')}</span>
                <input 
                  type="number" step="0.5" value={config.safety_stop_usd} 
                  onChange={e => updateField('safety_stop_usd', parseFloat(e.target.value))}
                  className="bg-slate-950 border border-white/5 rounded-lg px-2 py-1 text-base font-bold text-white w-20 text-right focus:border-indigo-500/50 outline-none"
                />
              </div>
            </div>
          </div>

          {/* RSI Sensitivity */}
          <div className="space-y-4 p-6 bg-white/[0.02] rounded-3xl border border-white/5">
            <p className="text-base font-black uppercase tracking-widest text-slate-500">{t('rsi_sensitivity')}</p>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-base text-slate-400">{t('oversold')}</span>
                <input 
                  type="number" value={config.rsi_oversold} 
                  onChange={e => updateField('rsi_oversold', parseInt(e.target.value))}
                  className="bg-slate-950 border border-white/5 rounded-lg px-2 py-1 text-base font-bold text-white w-16 text-right focus:border-indigo-500/50 outline-none"
                />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-base text-slate-400">{t('overbought')}</span>
                <input 
                  type="number" value={config.rsi_overbought} 
                  onChange={e => updateField('rsi_overbought', parseInt(e.target.value))}
                  className="bg-slate-950 border border-white/5 rounded-lg px-2 py-1 text-base font-bold text-white w-16 text-right focus:border-indigo-500/50 outline-none"
                />
              </div>
            </div>
          </div>

          {/* Points Adjustment */}
          <div className="space-y-4 p-6 bg-white/[0.02] rounded-3xl border border-white/5">
            <p className="text-base font-black uppercase tracking-widest text-slate-500">{t('points_dist')}</p>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-base text-slate-400">{t('sl_points')}</span>
                <input 
                  type="number" value={config.sl_points} 
                  onChange={e => updateField('sl_points', parseInt(e.target.value))}
                  className="bg-slate-950 border border-white/5 rounded-lg px-2 py-1 text-base font-bold text-white w-16 text-right focus:border-indigo-500/50 outline-none"
                />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-base text-slate-400">{t('tp_points')}</span>
                <input 
                  type="number" value={config.tp_points} 
                  onChange={e => updateField('tp_points', parseInt(e.target.value))}
                  className="bg-slate-950 border border-white/5 rounded-lg px-2 py-1 text-base font-bold text-white w-16 text-right focus:border-indigo-500/50 outline-none"
                />
              </div>
            </div>
          </div>

          {/* Quick Info */}
          <div className="space-y-4 p-6 bg-indigo-500/5 rounded-3xl border border-indigo-500/10">
            <p className="text-base font-black uppercase tracking-widest text-indigo-400">{t('link_info')}</p>
            <p className="text-base text-slate-400 leading-relaxed italic">
              {t('link_info_desc')}
            </p>
          </div>
        </div>
      </div>

      {/* Scalper AI Insight */}
      <IntelligencePanel insight={insight} aiFeed={aiFeed} prices={prices} prevPrices={prevPrices} />

      {/* Scalper Strategy Evolution */}
      <EvolutionLab news={news} evolution={evolution} />
      
    </div>
  );
};

export default ScalperDashboard;
