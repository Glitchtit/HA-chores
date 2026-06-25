import { useCallback, useEffect, useState } from 'react';
import * as api from '../api';

function daysLeft(endIso) {
  if (!endIso) return null;
  const end = new Date(endIso);
  end.setHours(23, 59, 59, 999);
  const ms = end - new Date();
  if (ms <= 0) return 'Ends today';
  const d = Math.ceil(ms / 86400000);
  return d === 1 ? '1 day left' : `${d} days left`;
}

export default function ChallengeBanner() {
  const [challenge, setChallenge] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api.getActiveChallenge()
      .then((d) => { setChallenge(d); setError(null); })
      .catch(() => setError('Failed to load challenge'));
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onCompleted = () => load();
    window.addEventListener('chore-completed', onCompleted);
    return () => window.removeEventListener('chore-completed', onCompleted);
  }, [load]);

  if (error || !challenge) return null;

  const pct = challenge.goal_value > 0
    ? Math.min(100, (challenge.progress / challenge.goal_value) * 100)
    : 0;
  const done = challenge.status === 'completed';
  const excess = done ? Math.max(0, challenge.progress - challenge.goal_value) : 0;

  const tokens = challenge.reward_tokens ?? 30;

  return (
    <div className={`relative overflow-hidden rounded-xl p-4 border ${
      done
        ? 'bg-gradient-to-br from-amber-900/40 to-yellow-800/20 animate-golden-sparkle'
        : 'bg-gradient-to-br from-blue-900/40 to-orange-900/30 border-orange-500/30'
    }`}>
      {/* Shiny light-sweep over the completed banner */}
      {done && (
        <div className="animate-shimmer-slow absolute inset-0 pointer-events-none" aria-hidden="true" />
      )}
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className={`text-xs uppercase tracking-widest ${done ? 'text-amber-300' : 'text-orange-300/80'}`}>
            {done ? '🎉 Completed!' : '🏆 Weekly challenge'}
          </div>
          <h3 className="text-base font-semibold text-gray-100 mt-0.5 truncate">
            {challenge.name}
          </h3>
          {challenge.description && (
            <p className="text-xs text-gray-400 mt-0.5">{challenge.description}</p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className={`text-sm font-semibold ${done ? 'text-amber-200' : 'text-gray-100'}`}>
            {challenge.progress}/{challenge.goal_value}
          </div>
          <div className="text-[10px] text-gray-400">
            {done
              ? (excess > 0 ? `+${excess} over goal 🔥` : 'Done this week')
              : daysLeft(challenge.period_end)}
          </div>
        </div>
      </div>
      <div className="relative mt-2 bg-gray-700 h-2 rounded-full overflow-hidden">
        <div
          className={`${done ? 'bg-gradient-to-r from-amber-400 to-yellow-300' : 'bg-gradient-to-r from-blue-500 to-orange-400'} h-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {done && (
        <div className="relative mt-2 text-xs text-amber-200">
          Everyone earned <span className="font-semibold">{tokens} 🪙</span> + {challenge.reward_multiplier}× XP for {challenge.reward_hours}h
        </div>
      )}
    </div>
  );
}
