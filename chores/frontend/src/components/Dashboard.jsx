import { useState, useEffect, useCallback, useRef } from 'react';
import * as api from '../api';
import { useGameEffects } from './effects/GameEffects';

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function timeUntilExpiry(expiresAt) {
  if (!expiresAt) return null;
  const diff = new Date(expiresAt) - new Date();
  if (diff <= 0) return 'Expired';
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  if (days > 0) return `${days}d left`;
  if (hours > 0) return `${hours}h left`;
  return '<1h left';
}

export default function Dashboard({ activePerson, persons, addToast }) {
  const [todayChores, setTodayChores] = useState([]);
  const [optionalChores, setOptionalChores] = useState([]);
  const [stats, setStats] = useState(null);
  const [activePowerups, setActivePowerups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [completingId, setCompletingId] = useState(null);
  const { triggerEffects } = useGameEffects();
  const xpBarRef = useRef(null);
  const doneButtonRefs = useRef({});

  const load = useCallback(async () => {
    try {
      const [chores, personStats, allChores, powerups] = await Promise.all([
        api.getTodayInstances(activePerson),
        activePerson ? api.getPersonStats(activePerson) : null,
        api.getChores(),
        activePerson ? api.getActivePowerups(activePerson) : Promise.resolve([]),
      ]);
      setTodayChores(chores);
      setStats(personStats);
      setActivePowerups(powerups);
      const scheduledIds = new Set(chores.map(c => c.chore_id));
      setOptionalChores(allChores.filter(c => !c.recurrence && !scheduledIds.has(c.id)));
    } catch { /* ignore */ }
    setLoading(false);
  }, [activePerson]);

  useEffect(() => { load(); }, [load]);

  const handleComplete = async (instanceId) => {
    setCompletingId(instanceId);
    try {
      const result = await api.completeInstance(instanceId, activePerson);
      addToast(`✅ +${result.xp_awarded} XP${result.leveled_up ? ' · LEVEL UP! 🎉' : ''}`, 'success');

      // Compute XP bar progress before reload
      const oldXPIntoLevel = stats ? stats.xp_total % 100 : 0;
      const newXP = (stats ? stats.xp_total : 0) + result.xp_awarded;
      const newXPIntoLevel = result.leveled_up ? newXP % 100 : newXP % 100;

      triggerEffects(
        result,
        doneButtonRefs.current[instanceId],
        xpBarRef.current,
        oldXPIntoLevel,
        newXPIntoLevel,
      );

      load();
    } catch (e) {
      addToast('Failed to complete chore', 'error');
    } finally {
      setCompletingId(null);
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

  const handleAdd = async (chore) => {
    try {
      await api.createInstance({ chore_id: chore.id, due_date: todayISO(), assigned_to: activePerson });
      addToast(`📋 "${chore.name}" added to today!`, 'success');
      load();
    } catch {
      addToast('Failed to add chore', 'error');
    }
  };

  const handleDiscardPowerup = async (powerupId) => {
    try {
      await api.discardPowerup(powerupId);
      setActivePowerups(prev => prev.filter(p => p.id !== powerupId));
    } catch {
      addToast('Failed to discard power-up', 'error');
    }
  };

  // Determine if a power-up applies to a given chore difficulty
  const getApplicablePowerup = (difficulty) => {
    return activePowerups.find(p =>
      p.powerup_type !== 'streak_shield' &&
      (p.applies_to === 'any' || p.applies_to === difficulty)
    ) || null;
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  const xpIntoLevel = stats ? stats.xp_total % 100 : 0;
  const xpProgress = xpIntoLevel;

  return (
    <div className="space-y-6 max-w-lg mx-auto">
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
              <span>{xpIntoLevel}/100 XP · Level {stats.level + 1}</span>
            </div>
            <div ref={xpBarRef} className="h-3 bg-gray-700 rounded-full overflow-hidden">
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
              <div className="text-xs text-gray-500">
                Streak
                {stats.current_streak > 0 && (
                  <span className="text-amber-400 ml-1">(+{Math.min(stats.current_streak * 10, 100)}%)</span>
                )}
              </div>
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

      {/* Active Power-ups panel */}
      {activePowerups.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            ⚡ Power-ups
            <span className="text-sm text-gray-500">({activePowerups.length})</span>
          </h3>
          <div className="space-y-2">
            {activePowerups.map(p => (
              <div key={p.id} className="animate-golden-sparkle rounded-lg p-3 flex items-center gap-3">
                <span className="text-2xl flex-shrink-0">{p.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-white text-sm">{p.name}</div>
                  <div className="text-xs text-gray-400">{p.description}</div>
                  <div className="text-xs text-purple-300 mt-0.5">
                    {p.uses_remaining} use{p.uses_remaining !== 1 ? 's' : ''} remaining
                    {p.expires_at && <span className="ml-2 text-gray-500">· {timeUntilExpiry(p.expires_at)}</span>}
                  </div>
                </div>
                <button
                  onClick={() => handleDiscardPowerup(p.id)}
                  className="text-gray-600 hover:text-red-400 transition-colors text-lg flex-shrink-0"
                  title="Discard"
                >🗑️</button>
              </div>
            ))}
          </div>
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
            {todayChores.map(ci => {
              const activePowerup = getApplicablePowerup(ci.chore_difficulty);
              return (
                <div
                  key={ci.id}
                  className={`rounded-lg p-4 flex items-center justify-between transition-colors ${
                    activePowerup ? 'animate-golden-sparkle' : 'bg-gray-800'
                  } ${ci.status === 'overdue' ? 'border border-red-500/50' : ''} ${
                    completingId === ci.id ? 'animate-complete-flash' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <span className="text-2xl">{ci.chore_icon || '🧹'}</span>
                      {activePowerup && (
                        <span className="absolute -top-1 -right-1 text-xs">⚡</span>
                      )}
                    </div>
                    <div>
                      <div className="font-medium">{ci.chore_name}</div>
                      <div className="text-xs text-gray-500 flex gap-2 items-center">
                        {ci.status === 'overdue' && <span className="text-red-400">Overdue ·</span>}
                        <span>{ci.chore_difficulty}</span>
                        {activePowerup && (
                          <span className="text-yellow-400 font-black text-sm">
                            ✨ ~{Math.round((ci.chore_xp_reward ?? 0) * activePowerup.multiplier)} XP
                          </span>
                        )}
                        {ci.chore_assignment_mode === 'claim' && ci.status === 'claimed' && ci.assigned_to !== activePerson && (
                          <span className="text-amber-400">· claimed</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div>
                    {ci.status === 'completed' ? null
                      : ci.chore_assignment_mode === 'claim' && ['pending', 'overdue'].includes(ci.status) && ci.assigned_to !== activePerson ? (
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
                          ref={el => { doneButtonRefs.current[ci.id] = el; }}
                          onClick={() => handleComplete(ci.id)}
                          disabled={completingId === ci.id}
                          className="px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
                        >
                          {completingId === ci.id ? '⏳' : 'Done ❔'}
                        </button>
                      )
                    }
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* You could — easy/medium one-time chores as clickable tiles */}
      {(() => {
        const easyMedChores = optionalChores.filter(c => c.difficulty !== 'hard');
        const hardChores    = optionalChores.filter(c => c.difficulty === 'hard');
        return (
          <>
            {easyMedChores.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  💡 You could
                  <span className="text-sm font-normal text-gray-500">({easyMedChores.length})</span>
                </h3>
                <div className="grid grid-cols-3 gap-2">
                  {easyMedChores.map(c => {
                    const activePowerup = getApplicablePowerup(c.difficulty);
                    return (
                      <button
                        key={c.id}
                        onClick={() => handleAdd(c)}
                        className={`rounded-lg p-3 flex flex-col items-center gap-1 text-center transition-colors hover:brightness-110 active:scale-95 ${
                          activePowerup ? 'animate-golden-sparkle' : 'bg-gray-800 hover:bg-gray-700'
                        }`}
                      >
                        <div className="relative">
                          <span className="text-2xl">{c.icon || '🧹'}</span>
                          {activePowerup && <span className="absolute -top-1 -right-1 text-xs">⚡</span>}
                        </div>
                        <div className="text-xs font-medium leading-tight line-clamp-2">{c.name}</div>
                        <div className="text-xs">
                          {activePowerup ? (
                            <span className="text-yellow-400 font-bold">✨ {Math.round(c.xp_reward * activePowerup.multiplier)} XP</span>
                          ) : (
                            <span className="text-gray-500">{c.xp_reward} XP</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {hardChores.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  💪 Feeling extra?
                  <span className="text-sm font-normal text-gray-500">({hardChores.length})</span>
                </h3>
                <div className="space-y-2">
                  {hardChores.map(c => {
                    const activePowerup = getApplicablePowerup(c.difficulty);
                    return (
                      <div key={c.id} className={`rounded-lg p-4 flex items-center justify-between ${
                        activePowerup ? 'animate-golden-sparkle' : 'bg-gray-800'
                      }`}>
                        <div className="flex items-center gap-3">
                          <div className="relative">
                            <span className="text-2xl">{c.icon || '🧹'}</span>
                            {activePowerup && <span className="absolute -top-1 -right-1 text-xs">⚡</span>}
                          </div>
                          <div>
                            <div className="font-medium">{c.name}</div>
                            <div className="text-xs text-gray-500 flex gap-1.5 items-center">
                              <span className="capitalize">{c.difficulty}</span>
                              <span>·</span>
                              {activePowerup ? (
                                <span className="text-yellow-400 font-black text-sm">
                                  ✨ ~{Math.round(c.xp_reward * activePowerup.multiplier)} XP
                                </span>
                              ) : (
                                <span>{c.xp_reward} XP</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleAdd(c)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
                        >
                          Add
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        );
      })()}
    </div>
  );
}
