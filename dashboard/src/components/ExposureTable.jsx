import React from 'react';
import { useLanguage } from '../components/LanguageContext';

const ExposureTable = ({ positions, closePosition }) => {
  const { t } = useLanguage();

  return (
    <div className="bg-white/[0.02] backdrop-blur-3xl rounded-[40px] border border-white/5 shadow-3xl overflow-hidden ring-1 ring-white/10">
      <div className="p-8 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
        <h2 className="text-xl font-bold text-white flex items-center gap-3">
          {t('current_market_exposure')}
          <span className="bg-indigo-500/20 text-indigo-400 py-1 px-4 rounded-full text-base font-black tracking-widest uppercase border border-indigo-500/10">
            {positions.length} {t('active_holds')}
          </span>
        </h2>
      </div>
      
      <div className="overflow-x-auto min-h-[350px]">
        <table className="w-full text-left">
          <thead>
            <tr className="text-slate-500 text-base uppercase tracking-widest border-b border-white/5 bg-white/[0.01]">
              <th className="px-6 py-4 font-black">{t('ticket')}</th>
              <th className="px-6 py-4 font-black">{t('instrument')}</th>
              <th className="px-6 py-4 font-black text-center">{t('strategy')}</th>
              <th className="px-6 py-4 font-black text-center">{t('timeframe')}</th>
              <th className="px-6 py-4 font-black">{t('execution')}</th>
              <th className="px-6 py-4 font-black">{t('volume')}</th>
              <th className="px-6 py-4 font-black text-right">{t('floating_pl')}</th>
              <th className="px-6 py-4 font-black text-right">{t('action')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {positions.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-6 py-20 text-center">
                  <div className="flex flex-col items-center gap-4 opacity-30">
                    <div className="w-16 h-16 rounded-full border-2 border-dashed border-slate-500 flex items-center justify-center text-3xl">🕳️</div>
                    <p className="text-slate-400 font-bold uppercase tracking-widest text-base">{t('no_holds_void')}</p>
                  </div>
                </td>
              </tr>
            ) : (
              positions.map((pos) => (
                <tr key={pos.ticket} className="hover:bg-white/[0.03] transition-colors group">
                  <td className="px-6 py-6 font-mono text-base text-slate-500">
                     #{pos.ticket}
                  </td>
                  <td className="px-6 py-6">
                    <div className="flex items-center gap-3">
                      <div className="w-1.5 h-6 bg-indigo-500 rounded-full group-hover:h-8 transition-all"></div>
                      <span className="text-white font-black text-xl tracking-tighter">{pos.symbol}</span>
                    </div>
                  </td>
                  <td className="px-6 py-6 text-center">
                     <span className={`text-base font-black px-2 py-1 rounded-lg border uppercase tracking-widest ${
                        pos.magic === 777777 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 
                        pos.magic === 999999 ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' :
                        'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                     }`}>
                      {pos.magic === 777777 ? t('swing_hold') : 
                       pos.magic === 999999 ? t('sniper_hold') || 'Sniper' : 
                       t('scalp_hold')}
                     </span>
                  </td>
                  <td className="px-6 py-6 text-center">
                     <span className="text-base font-black px-2 py-0.5 rounded-lg bg-slate-800 text-slate-400 border border-white/5">
                      {pos.timeframe || (pos.magic === 777777 ? "H1" : "M5")}
                     </span>
                  </td>
                  <td className="px-6 py-6">
                     <span className={`text-base font-black px-2 py-1 rounded-lg border uppercase tracking-widest ${pos.type === 0 || pos.type === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'}`}>
                      {pos.type === 0 || pos.type === 'BUY' ? t('buy') : t('sell')}
                     </span>
                  </td>
                  <td className="px-6 py-6">
                    <span className="text-slate-300 font-mono text-lg font-bold">{pos.volume.toFixed(2)}</span>
                  </td>
                  <td className="px-6 py-6 text-right">
                    <span className={`text-2xl font-black ${(pos.profit || 0) >= 0 ? 'text-emerald-400 drop-shadow-[0_0_10px_rgba(52,211,153,0.2)]' : 'text-rose-400'}`}>
                      ${(pos.profit || 0).toFixed(2)}
                    </span>
                  </td>
                  <td className="px-6 py-6 text-right">
                     <button 
                      onClick={() => closePosition(pos.ticket)}
                      className="bg-rose-500/10 hover:bg-rose-500 text-red-500 hover:text-white border border-rose-500/20 px-4 py-2 rounded-xl text-base font-black uppercase tracking-widest transition-all shadow-lg hover:shadow-rose-500/20 active:scale-95"
                     >
                       {t('close')}
                     </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ExposureTable;
