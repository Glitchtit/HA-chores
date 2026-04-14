import { useState, useEffect } from 'react';
import * as api from '../api';

const MONTH_NAMES = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function periodLabel(period) {
  try {
    const [year, month] = period.split('-');
    return `${MONTH_NAMES[parseInt(month)]} ${year}`;
  } catch {
    return period;
  }
}

export default function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getLeaderboard()
      .then(setLeaderboard)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!leaderboard?.entries?.length) {
    return (
      <div className="text-center py-12 text-gray-500">
        <div className="text-4xl mb-2">🏆</div>
        <p>No one on the leaderboard yet</p>
      </div>
    );
  }

  const medal = (rank) => rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : null;
  const podiumHeight = (rank) => rank === 1 ? 'h-28' : rank === 2 ? 'h-20' : 'h-14';
  const label = leaderboard.period ? periodLabel(leaderboard.period) : '';

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div>
        <h2 className="text-lg font-semibold">🏆 Leaderboard</h2>
        {label && <p className="text-sm text-gray-400">{label}</p>}
      </div>

      {/* Podium (top 3) */}
      {leaderboard.entries.length >= 1 && (
        <div className="flex justify-center items-end gap-4 py-4">
          {[1, 0, 2].map(idx => {
            const entry = leaderboard.entries[idx];
            if (!entry) return <div key={idx} className="w-24" />;
            return (
              <div key={entry.entity_id} className="flex flex-col items-center">
                <div className="text-3xl mb-1">{medal(entry.rank) || ''}</div>
                <div className="text-xl mb-1">
                  {entry.avatar_url ? (
                    <img src={entry.avatar_url} className="w-12 h-12 rounded-full" alt="" />
                  ) : '👤'}
                </div>
                <div className="text-sm font-medium text-center truncate max-w-[80px]">
                  {entry.name}
                </div>
                <div className="text-xs text-amber-400 font-bold">Lv {entry.level}</div>
                <div className={`${podiumHeight(entry.rank)} w-20 bg-gradient-to-t from-amber-700 to-amber-500 rounded-t-lg mt-2 flex items-end justify-center pb-2`}>
                  <span className="text-xs font-bold">{entry.xp_month} XP</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Full rankings */}
      <div className="space-y-2">
        {leaderboard.entries.map(entry => (
          <div key={entry.entity_id}
            className="bg-gray-800 rounded-lg p-4 flex items-center gap-4">
            <div className="text-lg font-bold text-gray-500 w-8 text-center">
              {medal(entry.rank) || `#${entry.rank}`}
            </div>
            <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center overflow-hidden">
              {entry.avatar_url ? (
                <img src={entry.avatar_url} className="w-full h-full object-cover" alt="" />
              ) : (
                <span className="text-lg">👤</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{entry.name}</div>
              <div className="flex gap-3 text-xs text-gray-400 mt-0.5">
                <span>Lv {entry.level}</span>
                <span>🔥 {entry.current_streak}d</span>
                <span>🎖️ {entry.badges_count}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-amber-400 font-bold">{entry.xp_month}</div>
              <div className="text-xs text-gray-500">XP this month</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

