import React from 'react';
import { useLanguage } from '../components/LanguageContext';

const MarketWatch = ({ prices, prevPrices }) => {
  const { t } = useLanguage();

  return (
    <div className="border-l border-white/5 pl-8">
      <h2 className="text-base font-bold uppercase tracking-widest text-emerald-400 mb-5 flex items-center gap-2">
        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping"></div> {t('live_market_watch')}
      </h2>
      <div className="space-y-1.5 pr-2 overflow-visible">
        {Object.entries(prices).map(([symbol, price]) => {
          const prev = prevPrices[symbol];
          const isUp = prev ? price.bid > prev.bid : null;
          const colorClass = isUp === true ? 'text-emerald-400' : (isUp === false ? 'text-rose-400' : 'text-white');
          
          return (
            <div key={symbol} className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-all group">
              <span className="text-base font-black text-slate-400 group-hover:text-white transition-colors uppercase">{symbol}</span>
              <div className="flex flex-col items-end">
                <span className={`text-base font-mono font-black transition-colors duration-300 ${colorClass}`}>
                  {price.bid.toFixed(symbol.includes('JPY') || symbol.includes('XAU') ? 3 : 5)}
                </span>
                <span className="text-base font-bold text-slate-600 uppercase">{t('ask')} {price.ask.toFixed(symbol.includes('JPY') || symbol.includes('XAU') ? 3 : 5)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MarketWatch;
