import React from 'react';

import { useLanguage } from '../components/LanguageContext';

const IntelligencePanel = ({ insight, aiFeed, prices, prevPrices }) => {
  const { t, lang } = useLanguage();

  const PARAM_LABELS = {
    'rsi_oversold':          t('param_rsi_oversold'),
    'rsi_overbought':        t('param_rsi_overbought'),
    'sl_points':             t('param_sl_points'),
    'tp_points':             t('param_tp_points'),
    'virtual_balance':       t('param_virtual_balance'),
    'target_profit_usd':     t('param_target_profit_usd'),
    'safety_stop_usd':       t('param_safety_stop_usd'),
  };

  const translateMessage = (msg) => {
    if (!msg) return msg;
    if (msg.includes('self-calibrated')) {
      const match = msg.match(/\d+/);
      const count = match ? match[0] : '0';
      return lang === 'ar' ? `قام الذكاء الاصطناعي بمعايرته ذاتياً ${count} مرة.` : `AI autonomously self-calibrated ${count} times.`;
    }
    if (msg === 'Loading...') return lang === 'ar' ? 'جاري التحميل...' : 'Loading...';
    return msg;
  };

  const translateUpdate = (upd) => {
    if (!upd || upd === '—') return upd;
    if (upd === 'Never') return lang === 'ar' ? 'لم يحدث بعد' : 'Never';
    return upd;
  };

  return (
    <div className="lg:col-span-3 bg-gradient-to-br from-indigo-500/10 via-slate-900/40 to-purple-500/5 backdrop-blur-2xl p-8 rounded-[32px] border border-white/10 shadow-2xl relative overflow-hidden group">
      <div className="absolute right-0 top-0 w-full h-full bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent"></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10 h-full">
        
        {/* Col 1: Core Intelligence */}
        <div>
          <h2 className="text-base font-bold uppercase tracking-widest text-indigo-400 mb-5 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-indigo-500 rounded-full"></span> {t('core_intelligence')}
          </h2>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex flex-col items-center justify-center shrink-0">
                <span className="text-xl font-black text-indigo-300">{insight.ai_count}</span>
                <span className="text-base text-indigo-500 uppercase font-bold">{t('adjustment')}</span>
              </div>
              <div>
                <p className="text-white font-bold text-base leading-snug">{translateMessage(insight.message)}</p>
                <p className="text-slate-500 text-base mt-1">{t('update_label')} <span className="text-slate-400">{translateUpdate(insight.last_update)}</span></p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(insight.params || {}).map(([k, v]) => (
                <div key={k} className="bg-white/5 rounded-xl px-3 py-2 border border-white/5">
                  <p className="text-base text-slate-500 uppercase tracking-widest font-bold">{PARAM_LABELS[k] || k.replace(/_/g,' ')}</p>
                  <p className="text-white font-black text-lg">{v}</p>
                </div>
              ))}
            </div>
            <span className="text-base font-black bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full border border-indigo-500/20 uppercase tracking-tighter inline-block mt-2">{t('ai_calibration_live')}</span>
          </div>
        </div>

        {/* Col 2: Recent AI Thinking */}
        <div className="md:col-span-2 border-l border-white/5 pl-8 text-left">
          <h2 className="text-base font-bold uppercase tracking-widest text-indigo-400 mb-6 flex items-center gap-3">
            {t('ai_thinking_log')}
          </h2>
          <div className="space-y-3 max-h-[260px] overflow-y-auto pr-2 custom-scrollbar">
            {aiFeed.length === 0 ? (
              <p className="text-slate-500 text-base italic">{t('waiting_first_analysis')}</p>
            ) : (
              aiFeed.map((item, i) => {
                const isCli = item.reason?.includes("Gemini CLI:");
                const displayReason = item.reason?.replace("Gemini CLI: ", "");
                
                return (
                  <div key={i} className={`p-4 rounded-2xl border transition-all text-left ${
                    isCli 
                    ? 'bg-indigo-500/10 border-indigo-500/30 border-2 shadow-[0_0_15px_rgba(99,102,241,0.2)]' 
                    : 'bg-white/5 border-white/5 hover:border-indigo-500/30'
                  }`}>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-indigo-400">{item.time}</span>
                        {isCli && (
                          <span className="text-[10px] bg-indigo-500 text-white px-2 py-0.5 rounded-full font-black uppercase tracking-tighter">
                            CLI ANALYST
                          </span>
                        )}
                      </div>
                      <span className="text-base text-emerald-500 font-bold">{isCli ? t('recommendation') || 'ADVICE' : t('applied')}</span>
                    </div>
                    <p className={`text-base leading-relaxed ${isCli ? 'text-white' : 'text-slate-300'}`}>
                      {displayReason}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default IntelligencePanel;
