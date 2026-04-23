import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import Header from './components/Header';
import MainDashboard from './pages/MainDashboard';
import ScalperDashboard from './pages/ScalperDashboard';
import SwingDashboard from './pages/SwingDashboard';
import SniperDashboard from './pages/SniperDashboard';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import SystemAudit from './pages/SystemAudit';
import { useLanguage } from './components/LanguageContext';
import { API_URL } from './utils/apiBase';

const authEnabled = false;

function App() {
  const [account, setAccount] = useState({ balance: 0, equity: 0, currency: 'USD' });
  const [positions, setPositions] = useState([]);
  const [insight, setInsight] = useState({ message: "Loading...", ai_count: 0, last_update: "—", params: {} });
  const [isTrading, setIsTrading] = useState(true);
  const [filterActive, setFilterActive] = useState(true);
  const [history, setHistory] = useState({ total_profit: 0, trades: [] });
  const [market, setMarket] = useState({ status: "Checking...", color: "text-slate-500" });
  const [news, setNews] = useState([]);
  const [terminalLogs, setTerminalLogs] = useState([]);
  const [prices, setPrices] = useState({});
  const [prevPrices, setPrevPrices] = useState({});
  const [aiFeed, setAiFeed] = useState([]);
  const [evolution, setEvolution] = useState([]);
  const [intel, setIntel] = useState({ technical_summary: "Neutral", sentiment_score: 50, ai_note: "Consulting Gemini..." });
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("standard");
  const [period, setPeriod] = useState("day");
  const { lang, t } = useLanguage();

  // 🕒 Smart Session Countdown Logic State (Synchronized with Backend)
  const [countdown, setCountdown] = useState({ label: t('checking'), time: "—", isOpen: false });

  useEffect(() => {
    // MT5 session first: if broker has no fresh quotes / terminal off, show stopped (rose) in header
    if (!market || market.mt5_market_open === false) {
      setCountdown({
        label: t("mt5_market_stopped"),
        time: market.status || t("mt5_no_quotes"),
        isOpen: false,
        modeType: "MT5_CLOSED",
      });
      return;
    }
    if (!isTrading) {
      setCountdown({
        label: t("observation_mode"),
        time: t("system_paused_note"),
        isOpen: false,
        modeType: "👁️ OBSERVATION",
      });
      return;
    }
    if (market && market.status && String(market.status).includes("Live")) {
      const label = market.trading_mode === "⚔️ TRADING" ? t("trading_mode") : t("observation_mode");
      setCountdown({
        label,
        time: market.session || "Live",
        isOpen: market.trading_mode === "⚔️ TRADING",
        modeType: market.trading_mode,
      });
    } else if (market && market.next_open) {
      setCountdown({ label: t("opens_in"), time: market.next_open, isOpen: false, modeType: "CLOSED" });
    } else {
      setCountdown({ label: t("standby_label"), time: t("closed"), isOpen: false, modeType: "CLOSED" });
    }
  }, [market, isTrading, t]);

  const fetchData = async () => {
    try {
      const endpoints = ["account", "market-intelligence", "news", `history?period=${period}`, "trading/filter-status", "market-status", "logs", "market/prices", "trading/status", "positions", "ai-insights", "strategy/evolution", "mode", "insight"];
      const results = await Promise.all(endpoints.map(e => fetch(`${API_URL}/${e}`).then(r => r.ok ? r.json() : null)));

      if (results[0]) setAccount(results[0]);
      if (results[1]) setIntel(Array.isArray(results[1]) ? (results[1][0] || {}) : results[1]);
      if (results[2]) setNews(Array.isArray(results[2]) ? results[2] : (results[2].news || []));
      if (results[3]) setHistory(results[3]);
      if (results[4]) setFilterActive(results[7]?.active || results[4].active); // Safety for array index
      if (results[5]) setMarket(results[5]);
      if (results[6]) setTerminalLogs(results[6]);
      if (results[7]) { setPrevPrices(prices); setPrices(results[7]); }
      if (results[8]) setIsTrading(results[8].enabled);
      if (results[9]) setPositions(results[9]);
      if (results[10]) setAiFeed(results[10]);
      if (results[11]) setEvolution(results[11]);
      if (results[12]) setMode(results[12].mode);
      if (results[13]) setInsight(results[13]);
    } catch (error) {
      console.error("Backend offline", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [period]);

  const apiCall = async (url, method = "POST", body = null) => {
    try {
      const res = await fetch(`${API_URL}/${url}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : null
      });
      return res.ok;
    } catch (err) { return false; }
  };

  const toggleFilter = () => apiCall("trading/filter/toggle").then(ok => ok && setFilterActive(!filterActive));
  const toggleTrading = () => apiCall(`trading/${isTrading ? 'pause' : 'start'}`).then(ok => ok && setIsTrading(!isTrading));
  const toggleMode = () => apiCall(`mode/${mode === "standard" ? "aggressive" : "standard"}`).then(ok => ok && setMode(mode === "standard" ? "aggressive" : "standard"));
  const closePosition = (ticket) => apiCall(`positions/close/${ticket}`).then(ok => ok && fetchData());
  const handlePanic = () => confirm("⚠️ CLOSE ALL TRADES?") && apiCall("panic").then(ok => ok && fetchData());

  const copyHistory = () => {
    const text = "Time | Symbol | Profit (USD)\n" + (history.trades || []).map(t => `${t.time} | ${t.symbol} | ${t.profit >= 0 ? '+' : ''}${t.profit.toFixed(2)}`).join('\n');
    navigator.clipboard.writeText(text);
    alert("Copied!");
  };


  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#020617] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
        <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(79,70,229,0.15),transparent_50%)] pointer-events-none"></div>

        <Header
          isTrading={isTrading} toggleTrading={toggleTrading}
          filterActive={filterActive} toggleFilter={toggleFilter}
          mode={mode} toggleMode={toggleMode}
          countdown={countdown} market={market} handlePanic={handlePanic}
        />

        <div className="px-6 lg:px-12 py-4 border-b border-white/5 bg-slate-900/40 backdrop-blur-xl sticky top-0 z-40">
          <div className="max-w-[1800px] mx-auto flex items-center justify-between">
            <div className="flex bg-slate-950/50 p-1.5 rounded-2xl border border-white/5 overflow-x-auto no-scrollbar gap-2">
              <NavLink
                to="/main"
                className={({ isActive }) => `whitespace-nowrap px-8 py-3 rounded-[16px] font-black tracking-widest uppercase text-base transition-all ${isActive ? 'bg-slate-700 text-white shadow-[0_0_20px_rgba(51,65,85,0.4)]' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}
              >
                {t('dashboard')}
              </NavLink>
              <NavLink
                to="/scalper"
                className={({ isActive }) => `whitespace-nowrap px-8 py-3 rounded-[16px] font-black tracking-widest uppercase text-base transition-all ${isActive ? 'bg-indigo-500 text-white shadow-[0_0_20px_rgba(99,102,241,0.4)]' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}
              >
                {t('scalper')}
              </NavLink>
              <NavLink
                to="/swing"
                className={({ isActive }) => `whitespace-nowrap px-8 py-3 rounded-[16px] font-black tracking-widest uppercase text-base transition-al ${isActive ? 'bg-amber-500 text-slate-900 shadow-[0_0_20px_rgba(245,158,11,0.4)]' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}
              >
                {t('swing')}
              </NavLink>
              <NavLink
                to="/sniper"
                className={({ isActive }) => `whitespace-nowrap px-8 py-3 rounded-[16px] font-black tracking-widest uppercase text-base transition-al ${isActive ? 'bg-red-600 text-white shadow-[0_0_20px_rgba(220,38,38,0.4)]' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}
              >
                {t('sniper')}
              </NavLink>
              <NavLink
                to="/analytics"
                className={({ isActive }) => `whitespace-nowrap px-8 py-3 rounded-[16px] font-black tracking-widest uppercase text-base transition-all ${isActive ? 'bg-emerald-600 text-white shadow-[0_0_20px_rgba(5,150,105,0.4)]' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}
              >
                {t('analytics') || '📈 الأداء'}
              </NavLink>
              <NavLink
                to="/audit"
                className={({ isActive }) => `whitespace-nowrap px-8 py-3 rounded-[16px] font-black tracking-widest uppercase text-base transition-all ${isActive ? 'bg-slate-700 text-white shadow-[0_0_20px_rgba(255,255,255,0.1)]' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}
              >
                {t('audit') || '🕵️ التدقيق'}
              </NavLink>
            </div>
          </div>
        </div>

        <div className="p-6 md:p-10 max-w-[1800px] mx-auto w-full">
          <Routes>
            <Route path="/" element={<Navigate to="/main" replace />} />

            <Route path="/main" element={
              <MainDashboard
                account={account} positions={positions} closePosition={closePosition}
                terminalLogs={terminalLogs} history={history} period={period}
                setPeriod={setPeriod} copyHistory={copyHistory} market={market}
                prices={prices} prevPrices={prevPrices} aiFeed={aiFeed}
              />
            } />

            <Route path="/scalper" element={
              <ScalperDashboard
                insight={insight} aiFeed={aiFeed} prices={prices} prevPrices={prevPrices}
                news={news} evolution={evolution}
              />
            } />

            <Route path="/swing" element={
              <SwingDashboard
                intel={intel} positions={positions} closePosition={closePosition}
                account={account} history={history} market={market} loading={loading}
              />
            } />

            <Route path="/sniper" element={<SniperDashboard />} />
            <Route path="/analytics" element={<AnalyticsDashboard />} />
            <Route path="/audit" element={<SystemAudit />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
