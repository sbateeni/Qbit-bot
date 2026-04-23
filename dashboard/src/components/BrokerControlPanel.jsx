import React, { useEffect, useState } from 'react';
import { API_URL } from '../utils/apiBase';

const BROWSER_DB_NAME = "qbitBrowserStore";
const BROWSER_DB_VERSION = 1;
const BROWSER_STORE = "brokerCredentials";

const openBrowserDb = () =>
  new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      resolve(null);
      return;
    }
    const request = window.indexedDB.open(BROWSER_DB_NAME, BROWSER_DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(BROWSER_STORE)) {
        db.createObjectStore(BROWSER_STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

const readBrowserCreds = async (id) => {
  const db = await openBrowserDb();
  if (!db) return null;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(BROWSER_STORE, "readonly");
    const store = tx.objectStore(BROWSER_STORE);
    const req = store.get(id);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
};

const writeBrowserCreds = async (id, payload) => {
  const db = await openBrowserDb();
  if (!db) return;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(BROWSER_STORE, "readwrite");
    const store = tx.objectStore(BROWSER_STORE);
    const req = store.put({ id, ...payload, updatedAt: Date.now() });
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
};

const BrokerControlPanel = ({ session, activeAccount }) => {
  const [provider, setProvider] = useState("fxcm");
  const [environment, setEnvironment] = useState("demo");
  const [brokerAccountId, setBrokerAccountId] = useState("");
  const [brokerApiToken, setBrokerApiToken] = useState("");
  const [status, setStatus] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isPinging, setIsPinging] = useState(false);
  const [pingResult, setPingResult] = useState(null);
  const [credsLoaded, setCredsLoaded] = useState(false);
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
  const browserCredKey = `broker:${accountId || "default"}`;
  const quickAccessUrl = "https://www.fxcm.com/markets/platforms/trading-station/";
  const withTimeout = async (url, options = {}, timeoutMs = 12000) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  };

  const saveBroker = async () => {
    if (!accountId) return setStatus("اختر حساب المشترك أولاً");
    if (!brokerAccountId || !brokerApiToken) return setStatus("أدخل Account ID و API Token الخاصين بـ FXCM");
    setIsSaving(true);
    try {
      const res = await withTimeout(`${API_URL}/v2/broker/connection`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          account_id: accountId,
          provider,
          broker_account_id: brokerAccountId,
          api_key: brokerApiToken,
          environment,
        }),
      });
      setStatus(res.ok ? "تم ربط حساب الوسيط بنجاح" : "فشل ربط حساب الوسيط");
    } catch (err) {
      setStatus("تعذر الاتصال بالـAPI أثناء الحفظ");
    } finally {
      setIsSaving(false);
    }
  };

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

  const pingBroker = async () => {
    if (!accountId) return setStatus("اختر حساب المشترك أولاً");
    setIsPinging(true);
    setPingResult(null);
    try {
      const res = await withTimeout(`${API_URL}/v2/broker/ping/${encodeURIComponent(accountId)}`, {
        headers: authHeaders(),
      });
      const payload = await res.json().catch(() => ({}));
      setPingResult(payload);
      setStatus(payload?.ok ? "اتصال الوسيط يعمل" : "اتصال الوسيط غير مكتمل");
    } catch (err) {
      setStatus("انتهت مهلة فحص الاتصال أو تعذر الوصول للـAPI");
      setPingResult({ ok: false, error: "timeout_or_network_error" });
    } finally {
      setIsPinging(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    setCredsLoaded(false);
    readBrowserCreds(browserCredKey)
      .then((saved) => {
        if (cancelled || !saved) return;
        setBrokerAccountId(saved.brokerAccountId || "");
        setBrokerApiToken(saved.brokerApiToken || "");
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setCredsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [browserCredKey]);

  useEffect(() => {
    if (!credsLoaded) return;
    writeBrowserCreds(browserCredKey, { brokerAccountId, brokerApiToken }).catch(() => {});
  }, [browserCredKey, brokerAccountId, brokerApiToken, credsLoaded]);

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-3xl p-6 space-y-5">
      <h3 className="text-white text-lg font-black">لوحة إعداد المشترك</h3>
      <p className="text-slate-400 text-sm">أدخل بيانات FXCM (ForexConnect) ثم اضبط المخاطر وشغّل الاستراتيجية.</p>

      <div className="bg-slate-950/70 border border-white/10 rounded-2xl p-4 space-y-3">
        <p className="text-indigo-300 text-xs font-bold uppercase tracking-widest">1) ربط حساب الوسيط</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value="FXCM" readOnly />
          <select className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={environment} onChange={e => setEnvironment(e.target.value)}>
            <option value="demo">Demo</option>
            <option value="live">Live</option>
          </select>
          <input
            className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white"
            value={brokerAccountId}
            onChange={e => setBrokerAccountId(e.target.value)}
            placeholder="FXCM Account ID (مثل 12345678)"
            tabIndex={1}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
            name="fxcm-account-id-manual"
          />
          <input
            type="password"
            className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white"
            value={brokerApiToken}
            onChange={e => setBrokerApiToken(e.target.value)}
            placeholder="FXCM API Token"
            tabIndex={2}
            autoComplete="new-password"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
            name="fxcm-api-token-manual"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="px-2 py-1 rounded-lg bg-amber-500/10 border border-amber-400/30 text-amber-300 font-bold">
            نستخدم FXCM REST API: أدخل Account ID + API Token
          </span>
          <a
            href="https://www.fxcm.com/markets/platforms/trading-station/"
            target="_blank"
            rel="noreferrer"
            className="px-2 py-1 rounded-lg bg-slate-800 border border-white/15 text-slate-200 font-bold"
          >
            كيفية الحصول على API
          </a>
        </div>
        <a
          href={quickAccessUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center px-3 py-2 rounded-xl border border-indigo-400/30 bg-indigo-500/10 text-indigo-300 text-xs font-bold"
        >
          رابط وصول سريع إلى منصة FXCM ({environment})
        </a>
        <div className="flex flex-wrap gap-2">
          <button disabled={isSaving} className="px-4 py-2 bg-indigo-600 rounded-xl font-bold disabled:opacity-50" onClick={saveBroker}>
            {isSaving ? "جارٍ الحفظ..." : "حفظ ربط الوسيط"}
          </button>
          <button disabled={isPinging} className="px-4 py-2 bg-slate-700 rounded-xl font-bold disabled:opacity-50" onClick={pingBroker}>
            {isPinging ? "جارٍ الفحص..." : "فحص الاتصال"}
          </button>
        </div>
      </div>

      <div className="bg-slate-950/70 border border-white/10 rounded-2xl p-4 space-y-3">
        <p className="text-emerald-300 text-xs font-bold uppercase tracking-widest">2) إعدادات المخاطر</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.max_daily_loss} onChange={e => setRisk({ ...risk, max_daily_loss: e.target.value })} placeholder="الخسارة اليومية القصوى" />
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.max_open_trades} onChange={e => setRisk({ ...risk, max_open_trades: e.target.value })} placeholder="أقصى عدد صفقات مفتوحة" />
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.max_position_size} onChange={e => setRisk({ ...risk, max_position_size: e.target.value })} placeholder="أقصى حجم صفقة" />
          <input className="bg-slate-950 border border-white/10 rounded-xl p-3 text-white" value={risk.allowed_instruments} onChange={e => setRisk({ ...risk, allowed_instruments: e.target.value })} placeholder="الأزواج المسموحة (CSV)" />
        </div>
        <button className="px-4 py-2 bg-emerald-600 rounded-xl font-bold" onClick={saveRisk}>حفظ المخاطر</button>
      </div>

      <div className="bg-slate-950/70 border border-white/10 rounded-2xl p-4 space-y-3">
        <p className="text-amber-300 text-xs font-bold uppercase tracking-widest">3) تشغيل الاستراتيجية</p>
        <div className="flex flex-wrap gap-2">
          <input className="bg-slate-950 border border-white/10 rounded-xl p-2 text-white" value={strategy} onChange={e => setStrategy(e.target.value)} placeholder="اسم الاستراتيجية" />
          <button className="px-4 py-2 bg-amber-600 rounded-xl font-bold" onClick={startStrategy}>تشغيل</button>
        </div>
      </div>

      {status && <p className="text-sm text-slate-300">{status}</p>}
      {pingResult && (
        <pre className="text-xs bg-black/30 border border-white/10 rounded-xl p-3 text-slate-300 overflow-x-auto">
          {JSON.stringify(pingResult, null, 2)}
        </pre>
      )}
    </div>
  );
};

export default BrokerControlPanel;
