import { useEffect, useState } from 'react';
import * as api from '../api';

export default function ClassPickerModal({ personId, onDone }) {
  const [catalog, setCatalog] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [chosen, setChosen] = useState(null);

  useEffect(() => {
    api.getClassCatalog()
      .then(setCatalog)
      .catch(() => setError('Failed to load classes'));
  }, []);

  const handlePick = async (classId) => {
    if (!personId) {
      onDone?.();
      return;
    }
    setBusy(true);
    setError(null);
    setChosen(classId);
    try {
      await api.setPersonClass(personId, classId);
      // Hold the choice briefly so the user sees the highlight, then dismiss
      setTimeout(() => onDone?.(), 400);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to set class');
      setBusy(false);
      setChosen(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-orange-500/40 rounded-2xl max-w-2xl w-full p-6 shadow-2xl">
        <div className="text-center space-y-1 mb-5">
          <div className="text-4xl">🌟</div>
          <h2 className="text-xl font-display text-orange-400">Pick a Class</h2>
          <p className="text-sm text-gray-400">
            You reached Level 5. Specialize for a category bonus — you can switch later for free.
          </p>
        </div>

        {error && (
          <div className="bg-rose-900/40 border border-rose-700 text-rose-200 text-sm rounded-lg px-3 py-2 mb-4">
            {error}
          </div>
        )}

        {!catalog ? (
          <div className="text-gray-400 text-sm text-center py-6">Loading classes…</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {catalog.classes.map((c) => {
              const isChosen = chosen === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => handlePick(c.id)}
                  disabled={busy}
                  className={`text-left rounded-xl border p-3 transition-all ${
                    isChosen
                      ? 'border-orange-400 bg-orange-500/20'
                      : 'border-gray-700 bg-gray-800 hover:border-orange-400/60 hover:bg-gray-800/80'
                  } ${busy && !isChosen ? 'opacity-50' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{c.icon}</span>
                    <span className="font-semibold text-gray-100">{c.name}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-400">{c.description}</div>
                </button>
              );
            })}
          </div>
        )}

        <div className="mt-5 text-center">
          <button
            onClick={() => onDone?.()}
            disabled={busy}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Decide later
          </button>
        </div>
      </div>
    </div>
  );
}
