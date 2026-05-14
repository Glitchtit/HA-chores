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

  return (
    <div className={`rounded-xl p-4 border ${
      done
        ? 'bg-emerald-900/30 border-emerald-700/50'
        : 'bg-gradient-to-br from-blue-900/40 to-orange-900/30 border-orange-500/30'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-widest text-orange-300/80">
            {done ? '🎉 Challenge complete' : '🏆 Weekly challenge'}
          </div>
          <h3 className="text-base font-semibold text-gray-100 mt-0.5 truncate">
            {challenge.name}
          </h3>
          {challenge.description && (
            <p className="text-xs text-gray-400 mt-0.5">{challenge.description}</p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className="text-sm font-semibold text-gray-100">
            {challenge.progress}/{challenge.goal_value}
          </div>
          <div className="text-[10px] text-gray-400">{daysLeft(challenge.period_end)}</div>
        </div>
      </div>
      <div className="mt-2 bg-gray-700 h-2 rounded-full overflow-hidden">
        <div
          className={`${done ? 'bg-emerald-500' : 'bg-gradient-to-r from-blue-500 to-orange-400'} h-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {done && (
        <div className="mt-2 text-xs text-emerald-200">
          Every household member gets {challenge.reward_multiplier}× XP for {challenge.reward_hours}h
        </div>
      )}
    </div>
  );
}
