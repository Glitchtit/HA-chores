import { useCallback, useEffect, useState } from 'react';
import * as api from '../api';

function ObjectiveRow({ objective }) {
  const pct = objective.target_count > 0
    ? Math.min(100, (objective.progress / objective.target_count) * 100)
    : 0;
  const done = objective.progress >= objective.target_count;
  return (
    <div className="bg-gray-800/60 rounded-lg p-2 border border-gray-700/60">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-base">{objective.chore_icon || '🧹'}</span>
        <span className="flex-1 truncate text-gray-100">{objective.chore_name}</span>
        <span className={`text-xs ${done ? 'text-emerald-300' : 'text-gray-400'}`}>
          {objective.progress}/{objective.target_count}
        </span>
      </div>
      <div className="mt-1 bg-gray-700 h-1.5 rounded-full overflow-hidden">
        <div
          className={`${done ? 'bg-emerald-500' : 'bg-rose-500'} h-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function BossPanel() {
  const [boss, setBoss] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api.getActiveBoss()
      .then((d) => { setBoss(d); setError(null); })
      .catch(() => setError('Failed to load boss'));
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onCompleted = () => load();
    window.addEventListener('chore-completed', onCompleted);
    return () => window.removeEventListener('chore-completed', onCompleted);
  }, [load]);

  if (error || !boss) return null;

  const totalProgress = (boss.objectives || []).reduce((s, o) => s + (o.progress || 0), 0);
  const totalTarget = (boss.objectives || []).reduce((s, o) => s + (o.target_count || 0), 0);
  const overallPct = totalTarget > 0 ? Math.min(100, (totalProgress / totalTarget) * 100) : 0;
  const defeated = boss.status === 'defeated';

  return (
    <div className={`rounded-xl p-4 border ${
      defeated
        ? 'bg-emerald-900/30 border-emerald-700/50'
        : 'bg-gradient-to-br from-rose-900/40 to-amber-900/30 border-rose-500/40'
    }`}>
      <div className="flex items-center gap-3">
        <div className="text-4xl">{boss.icon || '👹'}</div>
        <div className="flex-1 min-w-0">
          <div className="text-xs uppercase tracking-widest text-rose-300/80">
            {defeated ? '🎉 Boss defeated' : 'Seasonal Boss'}
          </div>
          <h3 className="text-base font-semibold text-gray-100 truncate">
            {boss.name}
          </h3>
          {boss.description && (
            <p className="text-xs text-gray-400 mt-0.5 truncate">{boss.description}</p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className="text-sm font-semibold text-gray-100">
            {totalProgress}/{totalTarget}
          </div>
          <div className="text-[10px] text-gray-400">
            until {boss.end_date}
          </div>
        </div>
      </div>
      <div className="mt-2 bg-gray-700 h-2 rounded-full overflow-hidden">
        <div
          className={`${defeated ? 'bg-emerald-500' : 'bg-gradient-to-r from-rose-500 to-amber-400'} h-full transition-all duration-500`}
          style={{ width: `${overallPct}%` }}
        />
      </div>
      {(boss.objectives || []).length > 0 && (
        <div className="mt-3 space-y-1.5">
          {boss.objectives.map((o) => (
            <ObjectiveRow key={o.id} objective={o} />
          ))}
        </div>
      )}
    </div>
  );
}
