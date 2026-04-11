import { useState, useCallback } from 'react';
import * as api from '../api';

export default function Settings({ persons, activePerson, setActivePerson, addToast }) {
  const [syncing, setSyncing] = useState(false);

  const handleSyncPersons = useCallback(async () => {
    setSyncing(true);
    try {
      const synced = await api.syncPersons();
      addToast(`Synced ${synced.length} persons from Home Assistant`, 'success');
    } catch {
      addToast('Failed to sync persons', 'error');
    }
    setSyncing(false);
  }, [addToast]);

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h2 className="text-lg font-semibold">⚙️ Settings</h2>

      {/* Active person selection */}
      <div className="bg-gray-800 rounded-xl p-5 space-y-3">
        <h3 className="font-medium">👤 Active Person</h3>
        <p className="text-sm text-gray-400">
          Select who is currently using the app. This determines whose chores are shown on the Dashboard and My Chores tabs.
        </p>
        <div className="space-y-2">
          {persons.map(p => (
            <button
              key={p.entity_id}
              onClick={() => setActivePerson(p.entity_id)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${
                activePerson === p.entity_id
                  ? 'bg-amber-600/20 border border-amber-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center overflow-hidden">
                {p.avatar_url ? (
                  <img src={p.avatar_url} className="w-full h-full object-cover" alt="" />
                ) : (
                  <span className="text-lg">👤</span>
                )}
              </div>
              <div className="text-left">
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-gray-400">
                  Lv {p.level} · {p.xp_total} XP · 🔥 {p.current_streak}d streak
                </div>
              </div>
              {activePerson === p.entity_id && (
                <span className="ml-auto text-amber-400">✓</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* HA Sync */}
      <div className="bg-gray-800 rounded-xl p-5 space-y-3">
        <h3 className="font-medium">🏠 Home Assistant Integration</h3>
        <p className="text-sm text-gray-400">
          Sync household members from Home Assistant Person entities.
        </p>
        <button
          onClick={handleSyncPersons}
          disabled={syncing}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium"
        >
          {syncing ? 'Syncing...' : '🔄 Sync Persons from HA'}
        </button>
      </div>

      {/* About */}
      <div className="bg-gray-800 rounded-xl p-5">
        <h3 className="font-medium mb-2">ℹ️ About</h3>
        <p className="text-sm text-gray-400">
          Chores is a gamified household chore management app for Home Assistant.
          Earn XP, level up, unlock badges, and compete on the leaderboard!
        </p>
        <div className="mt-3 text-xs text-gray-600">
          Made with ❤️ for Home Assistant
        </div>
      </div>
    </div>
  );
}
