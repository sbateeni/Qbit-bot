import React, { useState } from 'react';
const authEnabled = false;

const LoginPage = ({ onLogin, authEnabled: authFlag = authEnabled }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!authFlag) {
        onLogin({ id: "local-user", email: "local@qbit" });
        return;
      }
      onLogin({ id: "local-user", email });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-6">
      <div className="w-full max-w-md bg-slate-900/40 backdrop-blur-3xl p-10 rounded-[48px] border border-white/5 shadow-2xl space-y-8">
        <div className="text-center space-y-2">
            <h1 className="text-4xl font-black text-white tracking-widest uppercase">
                Qbit<span className="text-indigo-500">Bot</span>
            </h1>
            <p className="text-slate-400 font-bold uppercase tracking-widest text-xs">Sovereign SaaS Edition v5.0</p>
            {!authFlag && (
              <p className="text-amber-400 text-xs font-bold">Local mode active (Supabase disabled)</p>
            )}
        </div>

        <form onSubmit={handleAuth} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-black text-slate-500 uppercase tracking-widest ml-4">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-950/50 border border-white/5 rounded-2xl px-6 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-all font-bold"
              placeholder="name@institutional.com"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black text-slate-500 uppercase tracking-widest ml-4">Access Secret</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-950/50 border border-white/5 rounded-2xl px-6 py-4 text-white focus:outline-none focus:border-indigo-500/50 transition-all font-bold"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs font-bold text-center">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-500 hover:bg-indigo-600 text-white font-black py-4 rounded-2xl shadow-lg shadow-indigo-500/20 transition-all uppercase tracking-widest disabled:opacity-50"
          >
            {loading ? 'Processing...' : (isRegistering ? 'Create Master Account' : 'Authenticate')}
          </button>
        </form>

        <div className="text-center">
          <button
            onClick={() => setIsRegistering(!isRegistering)}
            className="text-slate-500 hover:text-white text-xs font-black uppercase tracking-widest transition-all"
          >
            {isRegistering ? 'Already have access? Login' : 'Request Sovereign Access'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
