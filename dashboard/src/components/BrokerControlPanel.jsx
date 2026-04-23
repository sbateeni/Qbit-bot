import React, { useState } from 'react';
import { API_URL } from '../utils/apiBase';

const BrokerControlPanel = ({ session, activeAccount }) => {
  const [status, setStatus] = useState("");
  const [strategy, setStrategy] = useState("smart_scalper");
  const [risk, setRisk] = useState({
    max_daily_loss: 100,
    max_open_trades: 3,
    max_position_size: 1000,
    allowed_instruments: "EUR_USD,GBP_USD,USD_JPY",
  });

  const authHeaders = () => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${session?.access_token || ""}`,
  });

  const accountId = activeAccount?.id;

  const saveRisk = async () => {
    if (!accountId) return setStatus("اختر حساب المشترك أولاً");
    const res = await fetch(`${API_URL}/v2/risk/limits`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        account_id: accountId,
        max_daily_loss: Number(risk.max_daily_loss),
        max_open_trades: Number(risk.max_open_trades),
        max_position_size: Number(risk.max_position_size),
        allowed_instruments: risk.allowed_instruments.split(",").map(x => x.trim()).filter(Boolean),
      }),
    });
    setStatus(res.ok ? "تم حفظ حدود المخاطر" : "فشل حفظ حدود المخاطر");
  };

  const startStrategy = async () => {
    if (!accountId) return setStatus("اختر حساب المشترك أولاً");
    const res = await fetch(`${API_URL}/v2/strategy/start?account_id=${encodeURIComponent(accountId)}&strategy=${encodeURIComponent(strategy)}`, {
      method: "POST",
      headers: authHeaders(),
    });
    setStatus(res.ok ? "تم تشغيل الاستراتيجية" : "فشل تشغيل الاستراتيجية");
  };

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-3xl p-6 space-y-5">
      <h3 className="text-white text-lg font-black">لوحة إعداد المشترك</h3>
      <p className="text-slate-400 text-sm">يتم جلب بيانات الوسيط تلقائيًا من MT5 المحلي، بدون أي إدخال يدوي.</p>

      <div className="bg-slate-950/70 border border-white/10 rounded-2xl p-4 space-y-3">
        <p className="text-emerald-300 text-xs font-bold uppercase tracking-widest">1) إعدادات المخاطر</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.max_daily_loss} onChange={e => setRisk({ ...risk, max_daily_loss: e.target.value })} placeholder="الخسارة اليومية القصوى" />
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.max_open_trades} onChange={e => setRisk({ ...risk, max_open_trades: e.target.value })} placeholder="أقصى عدد صفقات مفتوحة" />
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.max_position_size} onChange={e => setRisk({ ...risk, max_position_size: e.target.value })} placeholder="أقصى حجم صفقة" />
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.allowed_instruments} onChange={e => setRisk({ ...risk, allowed_instruments: e.target.value })} placeholder="الأزواج المسموحة (CSV)" />
        </div>
        <button className="px-4 py-2 bg-emerald-600 rounded-xl font-bold" onClick={saveRisk}>حفظ المخاطر</button>
      </div>

      <div className="bg-slate-950/70 border border-white/10 rounded-2xl p-4 space-y-3">
        <p className="text-amber-300 text-xs font-bold uppercase tracking-widest">2) تشغيل الاستراتيجية</p>
        <div className="flex flex-wrap gap-2">
          <input className="bg-slate-950 border border-white/10 rounded-xl p-2 text-white" value={strategy} onChange={e => setStrategy(e.target.value)} placeholder="اسم الاستراتيجية" />
          <button className="px-4 py-2 bg-amber-600 rounded-xl font-bold" onClick={startStrategy}>تشغيل</button>
        </div>
      </div>

      {status && <p className="text-sm text-slate-300">{status}</p>}
    </div>
  );
};

export default BrokerControlPanel;
