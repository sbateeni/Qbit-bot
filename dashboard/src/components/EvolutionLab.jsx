import React from 'react';
import { useLanguage } from '../components/LanguageContext';

const EvolutionLab = ({ news, evolution }) => {
  const { t } = useLanguage();

  return (
    <div className="bg-white/[0.02] backdrop-blur-3xl rounded-[40px] border border-white/5 shadow-3xl overflow-hidden ring-1 ring-white/10 p-10">
      <div className="flex items-center justify-between mb-10">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            {t('strategy_evolution_lab')}
            <span className="text-base bg-indigo-500/20 text-indigo-400 px-3 py-1 rounded-full border border-indigo-500/10 font-black tracking-widest uppercase">
              {t('system_log')}
            </span>
          </h2>
          <p className="text-slate-500 text-base mt-1">{t('evolution_desc')}</p>
        </div>
      </div>

      <div className="space-y-6 max-h-[500px] overflow-y-auto pr-4 custom-scrollbar">
        {/* AI Fundamental Context */}
        <div className="mb-8 bg-indigo-500/5 border border-indigo-500/10 rounded-[32px] p-6">
          <h3 className="text-base font-black text-indigo-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
            <span className="w-2 h-2 bg-indigo-500 rounded-full"></span> {t('fundamental_ai_context')}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(news || []).slice(0, 4).map((item, i) => (
              <div key={i} className="flex gap-3 items-start bg-slate-900/50 p-4 rounded-2xl border border-white/5">
                <div className="text-xl">📰</div>
                <div>
                  <p className="text-base text-slate-200 font-bold leading-tight mb-1">{item.title}</p>
                  <span className="text-base text-slate-500 uppercase font-black">{item.published}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="text-base text-slate-500 mt-4 italic">{t('ai_lab_monitors')}</p>
        </div>

        {!evolution || evolution.length === 0 ? (
          <div className="py-20 text-center border-2 border-dashed border-white/5 rounded-[32px]">
            <p className="text-slate-600 font-bold italic">{t('no_evolution_steps')}</p>
          </div>
        ) : (
          evolution.map((evo, i) => (
            <div key={i} className="relative pl-8 pb-10 border-l border-white/5 last:pb-0">
              <div className="absolute left-[-5px] top-0 w-[9px] h-[9px] bg-indigo-500 rounded-full shadow-[0_0_10px_#6366f1]"></div>

              <div className="bg-white/[0.02] border border-white/5 rounded-3xl p-6 hover:border-indigo-500/30 transition-all group">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                  <div className="space-y-1">
                    <span className="text-base font-black text-indigo-400 uppercase tracking-widest">{evo.timestamp}</span>
                    <h4 className="text-lg font-bold text-white leading-tight">{t('ai_adjustment')} "{evo.ai_analysis}"</h4>
                  </div>
                  <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 rounded-2xl">
                    <span className="text-base font-black text-emerald-400 uppercase">{t('trade_failed')}</span>
                    <span className="text-base font-bold text-white">{evo.trade_failed?.symbol || t('unknown')} (#{evo.trade_failed?.ticket || '???'})</span>
                    <span className="text-base font-black text-rose-500 ml-2">${evo.trade_failed?.profit?.toFixed(2)}</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Market Footprint */}
                  <div className="md:col-span-2 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl p-4 flex flex-wrap items-center gap-6">
                    <span className="text-base font-black text-indigo-400 uppercase tracking-widest border-r border-indigo-500/20 pr-6">{t('market_footprint')}</span>
                    <div className="flex items-center gap-4">
                      <span className="text-base text-slate-500 uppercase font-bold">{t('h1_trend')}</span>
                      <span className={`text-base font-black ${evo.market_snapshot?.h1_trend === 'UP' ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {evo.market_snapshot?.h1_trend === 'UP' ? t('up') : t('down')}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-base text-slate-500 uppercase font-bold">{t('rsi')}</span>
                      <span className="text-base font-mono text-white">{evo.market_snapshot?.rsi || 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-base text-slate-500 uppercase font-bold">{t('ema_slope')}</span>
                      <span className="text-base font-mono text-white">{evo.market_snapshot?.slope || 'N/A'}</span>
                    </div>
                  </div>

                  {/* Before */}
                  <div className="bg-slate-950/50 rounded-2xl p-5 border border-white/5">
                    <p className="text-base font-black text-slate-500 uppercase tracking-widest mb-4">{t('initial_params')}</p>
                    <div className="flex flex-wrap gap-3">
                      {evo.config_change?.before && Object.entries(evo.config_change.before)
                        .filter(([k]) => ['rsi_oversold', 'rsi_overbought', 'sl_points'].includes(k))
                        .map(([k, v]) => (
                          <div key={k} className="bg-white/5 px-3 py-1.5 rounded-xl border border-white/5">
                            <span className="text-base text-slate-500 uppercase block font-bold">{k.replace(/_/g, ' ')}</span>
                            <span className="text-slate-300 font-mono text-base">{v}</span>
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* After */}
                  <div className="bg-indigo-500/5 rounded-2xl p-5 border border-indigo-500/10 relative overflow-hidden group-hover:bg-indigo-500/10 transition-all">
                    <div className="absolute right-[-10px] top-[-10px] text-4xl opacity-5">🚀</div>
                    <p className="text-base font-black text-indigo-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse"></span>
                      {t('optimized_params')}
                    </p>
                    <div className="flex flex-wrap gap-3">
                      {evo.config_change?.after && Object.entries(evo.config_change.after)
                        .filter(([k]) => ['rsi_oversold', 'rsi_overbought', 'sl_points'].includes(k))
                        .map(([k, v]) => (
                          <div key={k} className="bg-indigo-500/20 px-3 py-1.5 rounded-xl border border-indigo-500/30">
                            <span className="text-base text-indigo-300 uppercase block font-bold">{k.replace(/_/g, ' ')}</span>
                            <span className="text-white font-black text-base">{v}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EvolutionLab;
