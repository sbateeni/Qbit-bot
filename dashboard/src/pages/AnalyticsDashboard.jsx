import React, { useEffect, useState } from 'react';
import { useLanguage } from '../components/LanguageContext';

const API_URL =
  import.meta.env.VITE_API_URL ||
  "/api";

const AnalyticsDashboard = () => {
  const { lang, t } = useLanguage();
  const [period, setPeriod] = useState("all");
  const [data, setData] = useState({ 
    total_profit: 0, win_rate: 0, total_trades: 0, profit_factor: 0, strategies: {} 
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/analytics?period=${period}`)
      .then(r => r.ok ? r.json() : null)
      .then(res => {
        if (res) setData(res);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [period]);

  const StrategyCard = ({ name, stats, color }) => (
    <div className={`bg-white/[0.02] border border-${color}-500/20 rounded-2xl p-6 flex flex-col gap-4 relative overflow-hidden group`}>
      <div className={`absolute top-0 right-0 w-32 h-32 bg-${color}-500/10 blur-[50px] -mr-10 -mt-10 transition-all duration-700 group-hover:bg-${color}-500/20`}></div>
      <h3 className="text-xl font-black text-white tracking-widest uppercase relative z-10 flex items-center justify-between">
        {name}
        <span className={`text-xs px-2 py-1 rounded bg-${color}-500/10 text-${color}-400`}>
          {stats.trades} Trades
        </span>
      </h3>
      <div className="grid grid-cols-2 gap-4 relative z-10">
        <div className="flex flex-col">
          <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Profit/Loss</span>
          <span className={`text-2xl font-black ${stats.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {stats.profit >= 0 ? '+' : ''}{stats.profit}$
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Win Rate</span>
          <span className="text-2xl font-black text-white">{stats.win_rate}%</span>
        </div>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 relative overflow-hidden">
        <div className={`bg-${color}-500 h-1.5 rounded-full`} style={{ width: `${stats.win_rate}%` }}></div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-8 pb-32 animate-in fade-in slide-in-from-bottom-4 duration-1000 ease-out">
      
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-black text-white tracking-tighter uppercase">{t('analytics_title') || 'Performance Analytics'}</h1>
          <p className="text-slate-500 text-base max-w-xl">
            {t('analytics_desc') || 'Institutional grade performance metrics. Track win rates, profit factors, and total realized capital across all autonomous engines.'}
          </p>
        </div>
        
        {/* Period Selector */}
        <div className="flex bg-slate-900 border border-white/5 rounded-xl p-1">
          {['day', 'week', 'month', 'all'].map(p => (
            <button 
              key={p} 
              onClick={() => setPeriod(p)}
              className={`px-6 py-2 rounded-lg text-sm font-bold uppercase tracking-wider transition-all ${period === p ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-400 hover:text-white'}`}
            >
              {t(p) || p}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-32">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      ) : (
        <>
          {/* Main KPI Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-slate-900/50 border border-white/5 rounded-2xl p-6 flex flex-col justify-center">
              <span className="text-slate-500 text-sm font-bold uppercase tracking-wider mb-2">Total Net Profit</span>
              <span className={`text-4xl font-black tracking-tighter ${data.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {data.total_profit >= 0 ? '+' : ''}{data.total_profit.toFixed(2)}$
              </span>
            </div>
            
            <div className="bg-slate-900/50 border border-white/5 rounded-2xl p-6 flex flex-col justify-center">
              <span className="text-slate-500 text-sm font-bold uppercase tracking-wider mb-2">Global Win Rate</span>
              <span className="text-4xl font-black text-white tracking-tighter">{data.win_rate}%</span>
            </div>
            
            <div className="bg-slate-900/50 border border-white/5 rounded-2xl p-6 flex flex-col justify-center relative overflow-hidden">
              <span className="text-slate-500 text-sm font-bold uppercase tracking-wider mb-2">Profit Factor</span>
              <span className="text-4xl font-black text-amber-400 tracking-tighter">{data.profit_factor}</span>
              <div className="absolute right-[-10px] bottom-[-20px] text-8xl opacity-5">⚖️</div>
            </div>

            <div className="bg-slate-900/50 border border-white/5 rounded-2xl p-6 flex flex-col justify-center relative overflow-hidden">
              <span className="text-slate-500 text-sm font-bold uppercase tracking-wider mb-2">Executions</span>
              <span className="text-4xl font-black text-indigo-400 tracking-tighter">{data.total_trades}</span>
              <div className="absolute right-[-10px] bottom-[-20px] text-8xl opacity-5">⚡</div>
            </div>
          </div>

          {/* Engine Breakdown */}
          <h2 className="text-2xl font-black text-white tracking-tight uppercase mt-8">{t('engine_breakdown') || 'Engine Breakdown'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
             {data.strategies['Scalper'] && <StrategyCard name="Smart Scalper" stats={data.strategies['Scalper']} color="indigo" />}
             {data.strategies['Swing'] && <StrategyCard name="Macro Swing" stats={data.strategies['Swing']} color="amber" />}
             {data.strategies['Sniper'] && <StrategyCard name="TV Sniper" stats={data.strategies['Sniper']} color="rose" />}
             {data.strategies['Manual'] && <StrategyCard name="Manual / Interventions" stats={data.strategies['Manual']} color="slate" />}
          </div>
          
          {data.total_trades === 0 && (
             <div className="text-center py-20 border border-white/5 border-dashed rounded-3xl">
                <span className="text-slate-500 font-bold uppercase tracking-widest">No trades recorded in this period.</span>
             </div>
          )}
        </>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
