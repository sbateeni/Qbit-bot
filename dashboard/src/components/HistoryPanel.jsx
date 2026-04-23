import React, { useState } from 'react';
import { useLanguage } from '../components/LanguageContext';

const HistoryPanel = ({ history, period, setPeriod, copyHistory, copyStatus }) => {
  const [strategyFilter, setStrategyFilter] = useState("all");
  const { t } = useLanguage();

  const getStrategyLabel = (type) => {
    switch(type) {
      case "Scalper": return t('scalp_hold');
      case "Swing":   return t('swing_hold');
      case "Sniper":  return "🧨 Sniper"; // Did not add sniper_hold, just use Sniper
      case "Manual":  return t('manual');
      default:        return "❓ " + (type || t('unknown'));
    }
  };

  const filteredTrades = (history.trades || []).filter(t => {
    if (strategyFilter === "all") return true;
    return t.strategy?.toLowerCase() === strategyFilter.toLowerCase();
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* History List */}
      <div className="lg:col-span-2 bg-slate-900/40 backdrop-blur-xl p-8 rounded-[32px] border border-white/5 shadow-2xl relative overflow-hidden">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <h2 className="text-base font-bold uppercase tracking-widest text-slate-400 flex items-center gap-3">
              {t('closed_trades_history')}
            </h2>
            <div className="flex items-center gap-2">
              <select 
                value={period} 
                onChange={(e) => setPeriod(e.target.value)}
                className="bg-slate-900 border border-white/5 text-base text-slate-400 font-bold rounded-lg px-2 py-1 focus:outline-none cursor-pointer hover:border-indigo-500/30 transition-all"
              >
                <option value="day">{t('today')}</option>
                <option value="week">{t('last_week')}</option>
                <option value="month">{t('last_month')}</option>
                <option value="year">{t('last_year')}</option>
                <option value="all">{t('all_time')}</option>
              </select>

              <select 
                value={strategyFilter} 
                onChange={(e) => setStrategyFilter(e.target.value)}
                className="bg-slate-900 border border-indigo-500/20 text-base text-indigo-400 font-bold rounded-lg px-2 py-1 focus:outline-none cursor-pointer hover:border-indigo-500/50 transition-all uppercase"
              >
                <option value="all">{t('all_engines')}</option>
                <option value="scalper">{t('scalp_hold')}</option>
                <option value="swing">{t('swing_hold')}</option>
                <option value="sniper">🧨 Sniper</option>
                <option value="manual">{t('manual')}</option>
              </select>

              <button 
                onClick={copyHistory}
                className="text-base bg-indigo-500/10 hover:bg-indigo-500 text-indigo-400 hover:text-white px-3 py-1 rounded-lg border border-indigo-500/20 transition-all font-bold tracking-tight"
              >
                {copyStatus === "📋 Copy" ? t('copy') : copyStatus}
              </button>
            </div>
         </div>

         <div className="overflow-y-auto max-h-[350px] custom-scrollbar pr-2">
            <table className="w-full text-left">
              <thead>
                <tr className="text-base uppercase tracking-widest text-slate-500 border-b border-white/5">
                  <th className="pb-4 font-black">{t('time')}</th>
                  <th className="pb-4 font-black">{t('pair')}</th>
                  <th className="pb-4 font-black">{t('strategy')}</th>
                  <th className="pb-4 font-black text-right">{t('profit_usd')}</th>
                </tr>
              </thead>
              <tbody className="text-base">
                {(!filteredTrades || filteredTrades.length === 0) ? (
                  <tr><td colSpan="4" className="py-8 text-center text-slate-500 italic">{t('no_trades_match')}</td></tr>
                ) : (
                  filteredTrades.map((t, i) => (
                    <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors group">
                      <td className="py-4 text-slate-400 font-medium">{t.time}</td>
                      <td className="py-4 text-white font-bold tracking-tight">{t.symbol}</td>
                      <td className="py-4">
                        <span className="text-base bg-white/5 px-2 py-0.5 rounded border border-white/5 font-bold uppercase tracking-tighter text-slate-300">
                          {getStrategyLabel(t.strategy)}
                        </span>
                      </td>
                      <td className={`py-4 text-right font-black ${t.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {t.profit >= 0 ? '+' : ''}{t.profit.toFixed(2)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
         </div>
      </div>

      {/* Profit Summary */}
      <div className="bg-gradient-to-br from-slate-900 to-indigo-900/40 backdrop-blur-2xl p-10 rounded-[32px] border border-white/10 shadow-2xl flex flex-col justify-center items-center text-center relative group">
         <div className="absolute top-0 right-0 p-8 opacity-10 text-6xl group-hover:scale-110 transition-transform duration-700">💰</div>
         
         <div className="flex flex-col items-center gap-2 mb-4">
           <h3 className="text-slate-400 text-base font-bold uppercase tracking-[0.2em]">{t('realized_profit')}</h3>
           <select 
              value={period} 
              onChange={(e) => setPeriod(e.target.value)}
              className="bg-indigo-500/10 border border-indigo-500/20 text-base text-indigo-400 font-bold rounded-lg px-3 py-1 focus:outline-none cursor-pointer hover:bg-indigo-500/20 transition-all uppercase tracking-widest"
            >
              <option value="day">{t('today')}</option>
              <option value="week">{t('last_week')}</option>
              <option value="month">{t('last_month')}</option>
              <option value="year">{t('last_year')}</option>
              <option value="all">{t('total')}</option>
            </select>
         </div>

         <div className={`text-6xl font-black tracking-tighter mb-2 ${(history.total_profit || 0) >= 0 ? 'text-emerald-400 drop-shadow-[0_0_15px_rgba(52,211,153,0.3)]' : 'text-rose-400'}`}>
            ${(history.total_profit || 0).toFixed(2)}
         </div>
         <p className="text-slate-500 text-base mt-4 uppercase font-bold tracking-tighter">{t('last_sync')} {new Date().toLocaleTimeString()}</p>
      </div>
    </div>
  );
};

export default HistoryPanel;
