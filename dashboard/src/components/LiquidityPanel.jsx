import React from 'react';
import { useLanguage } from '../components/LanguageContext';

const LiquidityPanel = ({ account, market, vBalance, history, targetProfit, safetyStop, updateVBalance, updateTargetProfit, updateSafetyStop, loading }) => {
  const { t } = useLanguage();

  return (
    <div className="bg-white/[0.03] backdrop-blur-2xl px-8 py-4 rounded-[24px] border border-white/10 shadow-2xl relative overflow-hidden group">
      <div className="absolute -right-8 -top-8 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl group-hover:bg-emerald-500/10 transition-all duration-700"></div>
      
      {loading ? (
        <div className="flex items-center gap-8 animate-pulse">
           <div className="h-8 bg-white/5 rounded-lg w-40"></div>
           <div className="h-8 bg-white/5 rounded-lg w-40"></div>
           <div className="h-8 bg-white/5 rounded-lg w-60"></div>
        </div>
      ) : (
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          
          {/* Section 1: Real Account */}
          <div className="flex items-center gap-8 border-r border-white/5 pr-8">
            <div className="flex flex-col">
              <p className="text-slate-500 text-base font-black uppercase tracking-widest mb-0.5">{t('live_balance')}</p>
              <p className="text-xl font-black text-white">{account.balance.toLocaleString()} <span className="text-base text-slate-600 font-bold">{account.currency}</span></p>
            </div>
            <div className="flex flex-col">
              <p className="text-slate-500 text-base font-black uppercase tracking-widest mb-0.5">{t('floating_equity')}</p>
              <p className={`text-xl font-black ${account.equity >= account.balance ? 'text-emerald-400' : 'text-rose-400'}`}>
                {account.equity.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Section 2: Simulation Logic */}
          <div className="flex-1 flex items-center justify-between gap-8">
              <div className="flex items-center gap-6">
                <div className="flex flex-col">
                   <p className="text-indigo-400 text-base font-black uppercase tracking-[0.2em] mb-0.5">{t('simulation_mode')}</p>
                   <p className={`text-2xl font-black tracking-tighter ${(parseFloat(vBalance || 0) + (history?.total_profit || 0)) >= parseFloat(vBalance || 0) ? 'text-indigo-400 drop-shadow-[0_0_10px_rgba(129,140,248,0.3)]' : 'text-rose-400'}`}>
                    ${(parseFloat(vBalance || 0) + (history?.total_profit || 0)).toFixed(2)}
                  </p>
                </div>
                <div className="h-10 w-px bg-white/5 hidden lg:block"></div>
                <p className="text-base text-slate-500 italic max-w-[150px] leading-tight">{t('sim_desc1')}{targetProfit || 2}{t('sim_desc2')}{safetyStop || 1}{t('sim_desc3')}</p>
             </div>

             <div className="flex items-center gap-4">
                <div className="flex flex-col items-end">
                   <div className="flex items-center gap-2 bg-slate-900/50 border border-indigo-500/20 rounded-xl px-3 py-1.5 hover:border-indigo-500/40 transition-all">
                    <span className="text-base text-slate-500 font-black tracking-widest">{t('start')}</span>
                    <input type="number" value={vBalance} onChange={(e) => updateVBalance(e.target.value)} className="bg-transparent text-white text-base font-black w-14 focus:outline-none"/>
                  </div>
                </div>
                <div className="flex flex-col items-end">
                   <div className="flex items-center gap-2 bg-slate-900/50 border border-emerald-500/20 rounded-xl px-3 py-1.5 hover:border-emerald-500/40 transition-all">
                    <span className="text-base text-emerald-500 font-black tracking-widest">{t('target')}</span>
                    <input type="number" step="0.1" value={targetProfit} onChange={(e) => updateTargetProfit(e.target.value)} className="bg-transparent text-white text-base font-black w-14 focus:outline-none"/>
                  </div>
                </div>
                <div className="flex flex-col items-end">
                   <div className="flex items-center gap-2 bg-slate-900/50 border border-rose-500/20 rounded-xl px-3 py-1.5 hover:border-rose-500/40 transition-all">
                    <span className="text-base text-rose-500 font-black tracking-widest">{t('safety')}</span>
                    <input type="number" step="0.1" value={safetyStop} onChange={(e) => updateSafetyStop(e.target.value)} className="bg-transparent text-white text-base font-black w-14 focus:outline-none"/>
                  </div>
                </div>
             </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default LiquidityPanel;
