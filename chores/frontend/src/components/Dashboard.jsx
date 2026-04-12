import { useState, useEffect, useCallback } from 'react';
import * as api from '../api';

export default function Dashboard({ activePerson, persons, addToast }) {
  const [todayChores, setTodayChores] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [chores, personStats] = await Promise.all([
        api.getTodayInstances(activePerson),
        activePerson ? api.getPersonStats(activePerson) : null,
      ]);
      setTodayChores(chores);
      setStats(personStats);
    } catch { /* ignore */ }
    setLoading(false);
  }, [activePerson]);

  useEffect(() => { load(); }, [load]);

  const handleComplete = async (instanceId) => {
    try {
      await api.completeInstance(instanceId, activePerson);
      addToast('✅ Chore completed! +XP', 'success');
      load();
    } catch (e) {
      addToast('Failed to complete chore', 'error');
    }
  };

  const handleClaim = async (instanceId) => {
    try {
      await api.claimInstance(instanceId, activePerson);
      addToast('🙋 Chore claimed!', 'success');
      load();
    } catch (e) {
      addToast('Failed to claim chore', 'error');
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  const xpForNext = stats ? (50 * stats.level * stats.level) : 0;
  const xpProgress = stats ? ((stats.xp_total - 50 * (stats.level - 1) ** 2) / (xpForNext - 50 * (stats.level - 1) ** 2)) * 100 : 0;

  return (
    <div className="space-y-6 max-w-4xl mx-auto lg:grid lg:grid-cols-2 lg:gap-6 lg:space-y-0 lg:items-start">
      {/* Stats card */}
      {stats && (
        <div className="bg-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{stats.name}</h2>
              <p className="text-gray-400 text-sm">Rank #{stats.rank}</p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-amber-400">Lv {stats.level}</div>
              <div className="text-sm text-gray-400">{stats.xp_total} XP</div>
            </div>
          </div>

          {/* XP Progress bar */}
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Level {stats.level}</span>
              <span>Level {stats.level + 1}</span>
            </div>
            <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 rounded-full animate-xp-fill"
                style={{ width: `${Math.min(Math.max(xpProgress, 0), 100)}%` }}
              />
            </div>
          </div>

          {/* Streak & stats row */}
          <div className="flex justify-around text-center">
            <div className={stats.current_streak >= 3 ? 'animate-streak-glow rounded-lg p-2' : 'p-2'}>
              <div className="text-2xl">🔥</div>
              <div className="text-lg font-bold">{stats.current_streak}</div>
              <div className="text-xs text-gray-500">Streak</div>
            </div>
            <div className="p-2">
              <div className="text-2xl">✅</div>
              <div className="text-lg font-bold">{stats.completions_count}</div>
              <div className="text-xs text-gray-500">Completed</div>
            </div>
            <div className="p-2">
              <div className="text-2xl">🎖️</div>
              <div className="text-lg font-bold">{stats.badges?.length || 0}</div>
              <div className="text-xs text-gray-500">Badges</div>
            </div>
          </div>

          {/* Recent badges */}
          {stats.badges?.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {stats.badges.slice(0, 5).map(b => (
                <span key={b.id} className="text-2xl" title={b.name}>{b.icon}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Today's chores */}
      <div>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          📅 Today's Chores
          <span className="text-sm text-gray-500">({todayChores.length})</span>
        </h3>
        {todayChores.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">🎉</div>
            <p>All done for today!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {todayChores.map(ci => (
              <div
                key={ci.id}
                className={`bg-gray-800 rounded-lg p-4 flex items-center justify-between ${
                  ci.status === 'overdue' ? 'border border-red-500/50' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{ci.chore_icon || '🧹'}</span>
                  <div>
                    <div className="font-medium">{ci.chore_name}</div>
                    <div className="text-xs text-gray-500 flex gap-2 items-center">
                      {ci.status === 'overdue' && <span className="text-red-400">Overdue ·</span>}
                      <span>{ci.chore_difficulty}</span>
                      {ci.chore_assignment_mode === 'claim' && ci.status === 'claimed' && ci.assigned_to !== activePerson && (
                        <span className="text-amber-400">· claimed</span>
                      )}
                    </div>
                  </div>
                </div>
                <div>
                  {ci.status === 'completed' ? null
                    : ci.chore_assignment_mode === 'claim' && ci.status === 'pending' && ci.assigned_to !== activePerson ? (
                      <button
                        onClick={() => handleClaim(ci.id)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
                      >
                        Claim 🙋
                      </button>
                    ) : ci.chore_assignment_mode === 'claim' && ci.status === 'claimed' && ci.assigned_to !== activePerson ? (
                      <span className="px-3 py-2 text-xs text-gray-500 bg-gray-700 rounded-lg">
                        Claimed
                      </span>
                    ) : (
                      <button
                        onClick={() => handleComplete(ci.id)}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
                      >
                        Done ✓
                      </button>
                    )
                  }
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
