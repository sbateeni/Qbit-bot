import React from 'react';
import { useLanguage } from './LanguageContext';

const Header = ({ isTrading, toggleTrading, filterActive, toggleFilter, mode, toggleMode, countdown, market, handlePanic }) => {
  const { lang, toggleLang, t } = useLanguage();
  return (
    <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-6 pb-8 border-b border-white/5">
      <div className="flex flex-wrap items-center gap-6">
        <div className="w-16 h-16 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 rounded-3xl flex items-center justify-center shadow-2xl shadow-indigo-500/30 ring-2 ring-white/10 group">
          <span className="text-3xl font-black text-white group-hover:scale-110 transition-transform duration-500">Q</span>
        </div>
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tighter text-white inline-flex items-center gap-4">
            Qbit-Bot <span className="text-base font-black text-indigo-400 bg-indigo-500/10 px-4 py-1.5 rounded-2xl border border-indigo-500/20 shadow-lg shadow-indigo-500/5">SOVEREIGN v4.5</span>
          </h1>
          <p className="text-slate-500 mt-1 font-bold uppercase tracking-[0.2em]">{t('powered_by')}</p>
        </div>
        
        <button 
            onClick={toggleTrading}
            className={`ml-6 p-1.5 rounded-full border transition-all duration-500 flex items-center gap-3 pr-6 ${isTrading ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'}`}
          >
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isTrading ? 'bg-emerald-500 text-white' : 'bg-amber-500 text-white'}`}>
              {isTrading ? '⏸' : '▶'}
            </div>
            <span className="text-base font-black uppercase tracking-widest">{isTrading ? t('bot_active') : t('bot_paused')}</span>
          </button>
 
        <button 
            onClick={toggleFilter}
            className={`ml-3 p-1.5 rounded-full border transition-all duration-500 flex items-center gap-3 pr-6 ${filterActive ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}
          >
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${filterActive ? 'bg-indigo-500 text-white' : 'bg-rose-500 text-white'}`}>
              🛡️
            </div>
            <span className="text-base font-black uppercase tracking-widest">{filterActive ? t('shield_active') : t('shield_inactive')}</span>
          </button>
 
        <div className="flex bg-slate-900/50 p-1.5 rounded-2xl border border-white/5 ml-4 backdrop-blur-xl">
           <button 
            onClick={() => mode !== "standard" && toggleMode()}
            className={`px-5 py-2.5 rounded-xl text-base font-bold transition-all duration-300 ${mode === 'standard' ? 'bg-indigo-600 text-white shadow-xl shadow-indigo-600/30 ring-1 ring-indigo-400/50' : 'text-slate-500 hover:text-slate-300'}`}
           >
             {t('standard')}
           </button>
           <button 
            onClick={() => mode !== "aggressive" && toggleMode()}
            className={`px-5 py-2.5 rounded-xl text-base font-bold transition-all duration-300 ${mode === 'aggressive' ? 'bg-orange-600 text-white shadow-xl shadow-orange-600/30 ring-1 ring-orange-400/50' : 'text-slate-500 hover:text-slate-300'}`}
           >
             {t('aggressive')}
           </button>
        </div>

        <button 
            onClick={toggleLang}
            className="flex items-center justify-center ml-2 p-2 px-6 rounded-2xl bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-all font-black text-xs uppercase shadow-xl"
            title="Toggle Language"
        >
            {lang === 'ar' ? '🇬🇧 English' : '🇸🇦 عربي'}
        </button>
      </div>
 
      <div className="flex flex-wrap items-center gap-4 lg:gap-6">
        <div className={`flex items-center gap-4 px-6 py-2.5 rounded-2xl border backdrop-blur-xl shadow-inner transition-all duration-700 ${
          countdown.modeType === '⚔️ TRADING' ? 'bg-emerald-500/5 border-emerald-500/20 shadow-emerald-500/5' : 
          countdown.modeType === '👁️ OBSERVATION' ? 'bg-amber-500/5 border-amber-500/20 shadow-amber-500/5' :
          'bg-rose-500/5 border-rose-500/20 shadow-rose-500/5'
        }`}>
           <div className="flex flex-col items-start min-w-[100px]">
              <span className={`text-base font-black uppercase tracking-[0.2em] mb-0.5 ${
                countdown.modeType === '⚔️ TRADING' ? 'text-emerald-500/60' : 
                countdown.modeType === '👁️ OBSERVATION' ? 'text-amber-500/60' :
                'text-rose-500/60'
              }`}>
                {countdown.label}
              </span>
              <span className={`text-xl font-mono font-black tracking-wider ${
                countdown.modeType === '⚔️ TRADING' ? 'text-emerald-400 drop-shadow-[0_0_10px_rgba(52,211,153,0.3)]' : 
                countdown.modeType === '👁️ OBSERVATION' ? 'text-amber-400 drop-shadow-[0_0_10px_rgba(245,158,11,0.3)]' :
                'text-rose-400 drop-shadow-[0_0_10px_rgba(244,63,94,0.3)]'
              }`}>
                {countdown.time}
              </span>
           </div>
           <div className={`w-1 h-8 rounded-full ${
             countdown.modeType === '⚔️ TRADING' ? 'bg-emerald-500/20' : 
             countdown.modeType === '👁️ OBSERVATION' ? 'bg-amber-500/20' :
             'bg-rose-500/20'
           }`}></div>
           <div className="flex items-center gap-2">
              <div className="relative flex h-2 w-2">
                {countdown.modeType === '⚔️ TRADING' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                {countdown.modeType === '👁️ OBSERVATION' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${
                  countdown.modeType === '⚔️ TRADING' ? 'bg-emerald-500' : 
                  countdown.modeType === '👁️ OBSERVATION' ? 'bg-amber-500' :
                  'bg-rose-500'
                }`}></span>
              </div>
              <span className={`text-base font-black uppercase tracking-widest ${
                countdown.modeType === '⚔️ TRADING' ? 'text-emerald-400' : 
                countdown.modeType === '👁️ OBSERVATION' ? 'text-amber-400' :
                'text-rose-400'
              }`}>
                {countdown.modeType === '⚔️ TRADING' ? t('live') : 
                 countdown.modeType === '👁️ OBSERVATION' ? t('standby') : 
                 countdown.modeType === 'MT5_CLOSED' ? t('mt5_market_stopped') : t('closed')}
              </span>
           </div>
        </div>
 
        <div className="hidden md:flex flex-col items-end mr-4">
          <div className="flex items-center gap-2">
            <div className="relative flex h-3 w-3">
              {market.mt5_market_open === true && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${
                market.mt5_market_open === true ? 'bg-emerald-500' : 
                market.mt5_market_open === false ? 'bg-rose-500' : 'bg-slate-500'
              }`}></span>
            </div>
            <span className={`text-base font-black uppercase tracking-[0.2em] ${market.color || 'text-slate-400'}`}>
                {market.mt5_market_open === true && market.status?.includes("Live")
                  ? market.status.replace("Live — ", `${t('live')} — `)
                  : market.mt5_market_open === false
                  ? (market.status || t('mt5_market_stopped'))
                  : market.status?.includes("Closed")
                  ? market.status.replace("Closed — ", `${t('closed')} — `)
                  : (market.status || t('checking'))}
            </span>
          </div>
        </div>
        <button 
          onClick={handlePanic}
          className="group bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white font-bold py-3.5 px-10 rounded-2xl shadow-lg border border-red-500/30 transition-all duration-500 overflow-hidden relative"
        >
          <span className="relative z-10 flex items-center gap-2">{t('panic_close')}</span>
          <div className="absolute inset-x-0 bottom-0 h-0 group-hover:h-full bg-red-600 transition-all duration-300 -z-0"></div>
        </button>
      </div>
    </header>
  );
};

export default Header;
