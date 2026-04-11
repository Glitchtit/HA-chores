import { useState, useEffect } from 'react';
import * as api from '../api';

export default function Achievements({ activePerson, persons }) {
  const [badges, setBadges] = useState([]);
  const [selectedPerson, setSelectedPerson] = useState(activePerson);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedPerson) { setLoading(false); return; }
    setLoading(true);
    api.getPersonBadges(selectedPerson)
      .then(setBadges)
      .catch(() => setBadges([]))
      .finally(() => setLoading(false));
  }, [selectedPerson]);

  const earned        = badges.filter(b => b.earned);
  const lockedVisible = badges.filter(b => !b.earned && !b.badge.hidden);
  const lockedHidden  = badges.filter(b => !b.earned && b.badge.hidden);

  const earnedHidden  = earned.filter(b => b.badge.hidden);
  const earnedVisible = earned.filter(b => !b.badge.hidden);

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">🎖️ Achievements</h2>
        {persons.length > 1 && (
          <select
            value={selectedPerson || ''}
            onChange={e => setSelectedPerson(e.target.value)}
            className="bg-gray-700 rounded px-3 py-1.5 text-sm"
          >
            {persons.map(p => (
              <option key={p.entity_id} value={p.entity_id}>{p.name}</option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : !selectedPerson ? (
        <div className="text-center py-12 text-gray-500">
          <p>No person selected</p>
        </div>
      ) : (
        <>
          {/* Progress summary */}
          <div className="bg-gray-800 rounded-xl p-4 text-center">
            <div className="text-3xl mb-2">
              {earned.length > 0 ? earnedVisible.map(b => b.badge.icon).join(' ') || '🎖️' : '🔒'}
              {earnedHidden.length > 0 && <span className="ml-1 text-lg">+{earnedHidden.length}✨</span>}
            </div>
            <div className="text-lg font-bold">{earned.length} / {badges.length}</div>
            <div className="text-sm text-gray-400">Achievements Unlocked</div>
            <div className="h-2 bg-gray-700 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
                style={{ width: `${badges.length > 0 ? (earned.length / badges.length) * 100 : 0}%` }}
              />
            </div>
          </div>

          {/* Earned badges */}
          {earned.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-2">✨ Earned</h3>
              <div className="grid grid-cols-2 gap-2">
                {earned.map(b => (
                  <div key={b.badge.id}
                    className={`rounded-lg p-4 text-center animate-badge-pop ${b.badge.hidden ? 'bg-purple-900/40 ring-1 ring-purple-500/40' : 'bg-gray-800'}`}>
                    <div className="text-4xl mb-2">{b.badge.icon}</div>
                    <div className="font-medium text-sm">{b.badge.name}</div>
                    {b.badge.hidden && (
                      <div className="text-xs text-purple-400 font-semibold mt-0.5 uppercase tracking-wide">Hidden</div>
                    )}
                    <div className="text-xs text-gray-500 mt-1">{b.badge.description}</div>
                    {b.earned_at && (
                      <div className="text-xs text-amber-400 mt-1">
                        {new Date(b.earned_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Locked visible badges */}
          {lockedVisible.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-2">🔒 Locked</h3>
              <div className="grid grid-cols-2 gap-2">
                {lockedVisible.map(b => (
                  <div key={b.badge.id}
                    className="bg-gray-800/50 rounded-lg p-4 text-center opacity-60">
                    <div className="text-4xl mb-2 grayscale">🔒</div>
                    <div className="font-medium text-sm">{b.badge.name}</div>
                    <div className="text-xs text-gray-500 mt-1">{b.badge.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Locked hidden badges — mystery boxes */}
          {lockedHidden.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-2">🔮 Hidden Achievements</h3>
              <div className="grid grid-cols-2 gap-2">
                {lockedHidden.map(b => (
                  <div key={b.badge.id}
                    className="bg-gray-800/30 rounded-lg p-4 text-center opacity-50 border border-dashed border-gray-600">
                    <div className="text-4xl mb-2">❓</div>
                    <div className="font-medium text-sm text-gray-400">Hidden Achievement</div>
                    <div className="text-xs text-gray-600 mt-1">???</div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-600 text-center mt-2">
                {lockedHidden.length} hidden achievement{lockedHidden.length !== 1 ? 's' : ''} waiting to be discovered
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
