import { useCallback, useEffect, useState } from 'react';
import * as api from '../api';

function QuestRow({ quest }) {
  const pct = quest.target > 0 ? Math.min(100, (quest.progress / quest.target) * 100) : 0;
  const done = !!quest.completed_at;
  const coins = quest.coin_reward ?? 0;
  return (
    <div className={`rounded-lg p-2 border ${done ? 'bg-emerald-900/20 border-emerald-700/50' : 'bg-gray-800 border-gray-700'}`}>
      <div className="flex items-center gap-2 text-sm text-gray-100">
        <span className="text-base">{quest.icon || '🎯'}</span>
        <span className="flex-1 truncate">{quest.label || quest.quest_type}</span>
        {coins > 0 && (
          <span className={`text-xs font-medium ${done ? 'text-amber-300' : 'text-gray-500'}`}>
            +{coins} 🪙
          </span>
        )}
        <span className={`text-xs ${done ? 'text-emerald-300' : 'text-gray-400'}`}>
          {quest.progress}/{quest.target}
        </span>
      </div>
      <div className="mt-1 bg-gray-700 h-1.5 rounded-full overflow-hidden">
        <div
          className={`${done ? 'bg-emerald-500' : 'bg-orange-500'} h-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function DailyQuests({ personId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    if (!personId) return;
    api.getDailyQuests(personId)
      .then((d) => { setData(d); setError(null); })
      .catch(() => setError('Failed to load daily quests'));
  }, [personId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onCompleted = () => load();
    window.addEventListener('chore-completed', onCompleted);
    return () => window.removeEventListener('chore-completed', onCompleted);
  }, [load]);

  if (!personId) return null;
  if (error) {
    return <div className="text-xs text-rose-400">{error}</div>;
  }
  if (!data) return null;

  const allDone = data.quests.length > 0 && data.quests.every((q) => q.completed_at);
  const bundleXp = data.bundle_xp ?? 0;
  const bundleTokens = data.bundle_tokens ?? 0;

  return (
    <div className="bg-gray-900/60 rounded-xl p-3 border border-gray-800 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs uppercase tracking-widest text-gray-400">
          Daily Quests
        </h3>
        {allDone ? (
          <span className="text-[11px] text-amber-300 font-medium">
            🌟 All done · +{bundleXp} XP +{bundleTokens} 🪙
          </span>
        ) : (
          (bundleXp > 0 || bundleTokens > 0) && (
            <span className="text-[11px] text-gray-500">
              All 3 → +{bundleXp} XP +{bundleTokens} 🪙
            </span>
          )
        )}
      </div>
      <div className="space-y-1.5">
        {data.quests.map((q) => (
          <QuestRow key={q.id} quest={q} />
        ))}
      </div>
    </div>
  );
}
