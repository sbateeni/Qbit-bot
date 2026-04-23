import React, { useEffect, useRef } from 'react';
import { useLanguage } from '../components/LanguageContext';

const TerminalConsole = ({ logs }) => {
  const scrollRef = useRef(null);
  const { t } = useLanguage();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const levelLabel = (level) => {
    switch(level) {
      case 'INFO': return t('level_info');
      case 'WARNING': return t('level_warn');
      case 'ERROR': return t('level_error');
      default: return level;
    }
  };

  return (
    <div className="bg-slate-950 backdrop-blur-3xl rounded-[40px] border border-white/5 shadow-3xl overflow-hidden ring-1 ring-white/10 flex flex-col h-[480px]">
      <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/40">
        <h2 className="text-base font-black text-slate-400 flex items-center gap-3 uppercase tracking-[0.2em]">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_10px_#10b981]"></span>
          {t('bot_engine_output')}
        </h2>
        <span className="text-base text-slate-600 font-mono tracking-tighter">{t('live_stream_active')}</span>
      </div>
      
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-base space-y-1 custom-scrollbar bg-black/20"
      >
        {(!logs || logs.length === 0) ? (
          <p className="text-slate-700 italic">{t('initializing_stream')}</p>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="flex gap-4 border-b border-white/[0.02] pb-1 hover:bg-white/[0.01]">
              <span className="text-slate-600 shrink-0">[{log.time}]</span>
              <span className={`font-black shrink-0 w-14 ${log.level === 'INFO' ? 'text-indigo-400' : (log.level === 'WARNING' ? 'text-amber-400' : 'text-rose-400')}`}>
                {levelLabel(log.level)}
              </span>
              <span className="text-slate-300 break-all">{log.msg}</span>
            </div>
          ))
        )}
      </div>
      <div className="p-3 bg-black/60 border-t border-white/5 text-center">
         <span className="text-base text-slate-500 uppercase font-bold tracking-[0.3em]">{t('institutional_exec_monitor')}</span>
      </div>
    </div>
  );
};

export default TerminalConsole;
