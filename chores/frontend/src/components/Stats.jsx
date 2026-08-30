import { useState, useEffect, useMemo } from 'react';
import * as api from '../api';

const MONTH_NAMES = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// One tint per household member, assigned by position in the persons list.
const PERSON_COLORS = [
  { chip: 'bg-blue-900/40 text-blue-300',       dot: 'bg-blue-400' },
  { chip: 'bg-orange-900/40 text-orange-300',   dot: 'bg-orange-400' },
  { chip: 'bg-emerald-900/40 text-emerald-300', dot: 'bg-emerald-400' },
  { chip: 'bg-purple-900/40 text-purple-300',   dot: 'bg-purple-400' },
  { chip: 'bg-pink-900/40 text-pink-300',       dot: 'bg-pink-400' },
  { chip: 'bg-cyan-900/40 text-cyan-300',       dot: 'bg-cyan-400' },
];

function firstName(name) {
  return (name || '').split(' ')[0];
}

function CalendarDay({ dayNum, dateKey, entries, personIndex, isToday }) {
  const MAX_CARDS = 3;
  const shown = entries.slice(0, MAX_CARDS);
  const extra = entries.length - shown.length;

  return (
    <div className={`bg-gray-800 rounded-lg p-1 min-h-16 flex flex-col gap-0.5
                     ${isToday ? 'ring-1 ring-brand-orange' : ''}`}>
      <div className={`text-[10px] leading-none px-0.5 ${isToday ? 'text-brand-orange font-bold' : 'text-gray-500'}`}>
        {dayNum}
      </div>
      {shown.map((e, i) => {
        const p = personIndex[e.completed_by];
        const color = p ? PERSON_COLORS[p.colorIdx % PERSON_COLORS.length] : null;
        return (
          <div
            key={`${dateKey}-${i}`}
            className={`rounded px-1 py-0.5 text-[10px] leading-tight truncate flex items-center gap-0.5
                        ${color ? color.chip : 'bg-gray-700 text-gray-300'}`}
            title={`${e.chore_icon} ${e.chore_name} — ${p ? p.name : e.completed_by}`}
          >
            <span>{e.chore_icon}</span>
            <span className="truncate hidden sm:inline">{p ? firstName(p.name) : '?'}</span>
          </div>
        );
      })}
      {extra > 0 && (
        <div className="text-[10px] text-gray-500 px-0.5">+{extra}</div>
      )}
    </div>
  );
}

function MonthCalendar({ persons, personIndex }) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1); // 1-based
  const [days, setDays] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getStatsCalendar(year, month)
      .then(data => setDays(data.days || {}))
      .catch(() => setDays({}))
      .finally(() => setLoading(false));
  }, [year, month]);

  const prevMonth = () => {
    if (month === 1) { setYear(y => y - 1); setMonth(12); } else setMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (month === 12) { setYear(y => y + 1); setMonth(1); } else setMonth(m => m + 1);
  };

  const daysInMonth = new Date(year, month, 0).getDate();
  // Monday-first offset: JS getDay() has Sunday = 0
  const leadingBlanks = (new Date(year, month - 1, 1).getDay() + 6) % 7;
  const todayKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

  const cells = [];
  for (let i = 0; i < leadingBlanks; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const monthTotal = Object.values(days).reduce((sum, list) => sum + list.length, 0);

  return (
    <div className="bg-gray-800/50 rounded-xl p-3 space-y-2">
      <div className="flex items-center justify-between">
        <button onClick={prevMonth} className="px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors">◀</button>
        <div className="text-center">
          <div className="font-semibold">{MONTH_NAMES[month]} {year}</div>
          <div className="text-xs text-gray-400">
            {loading ? '…' : `${monthTotal} chore${monthTotal === 1 ? '' : 's'} done`}
          </div>
        </div>
        <button onClick={nextMonth} className="px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors">▶</button>
      </div>

      <div className="grid grid-cols-7 gap-1">
        {WEEKDAYS.map(d => (
          <div key={d} className="text-center text-[10px] text-gray-500 uppercase">{d}</div>
        ))}
        {cells.map((dayNum, idx) => {
          if (dayNum === null) return <div key={`blank-${idx}`} />;
          const dateKey = `${year}-${String(month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
          return (
            <CalendarDay
              key={dateKey}
              dayNum={dayNum}
              dateKey={dateKey}
              entries={days[dateKey] || []}
              personIndex={personIndex}
              isToday={dateKey === todayKey}
            />
          );
        })}
      </div>

      {/* Member colour legend */}
      {persons.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1">
          {persons.map((p, i) => (
            <span key={p.entity_id} className="flex items-center gap-1 text-xs text-gray-400">
              <span className={`w-2 h-2 rounded-full ${PERSON_COLORS[i % PERSON_COLORS.length].dot}`} />
              {firstName(p.name)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ComparisonMatrix({ persons, chores }) {
  const grandTotals = useMemo(() => {
    const totals = {};
    for (const p of persons) totals[p.entity_id] = 0;
    for (const c of chores) {
      for (const [pid, n] of Object.entries(c.counts)) {
        totals[pid] = (totals[pid] || 0) + n;
      }
    }
    return totals;
  }, [persons, chores]);

  if (!chores.length) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-2">📊</div>
        <p>No chores yet — nothing to compare</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-800">
            <th className="sticky left-0 z-10 bg-gray-800 text-left px-3 py-2 font-medium text-gray-400">
              Chore
            </th>
            {persons.map(p => (
              <th key={p.entity_id} className="px-3 py-2 min-w-16">
                <div className="flex flex-col items-center gap-1">
                  <div className="w-9 h-9 rounded-full bg-gray-700 flex items-center justify-center overflow-hidden">
                    {p.avatar_url
                      ? <img src={p.avatar_url} className="w-full h-full object-cover" alt="" />
                      : <span className="text-lg">👤</span>}
                  </div>
                  <span className="text-xs font-medium truncate max-w-16">{firstName(p.name)}</span>
                  <span className="text-[10px] text-amber-400">{grandTotals[p.entity_id] || 0} done</span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {chores.map(c => {
            const max = Math.max(0, ...persons.map(p => c.counts[p.entity_id] || 0));
            return (
              <tr key={c.id} className="border-t border-gray-800 hover:bg-gray-800/50 transition-colors">
                <td className="sticky left-0 z-10 bg-gray-900 px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className="text-lg">{c.icon}</span>
                    <span className={`truncate max-w-40 sm:max-w-none ${c.active ? '' : 'text-gray-500 line-through'}`}>
                      {c.name}
                    </span>
                  </span>
                </td>
                {persons.map(p => {
                  const n = c.counts[p.entity_id] || 0;
                  const leader = n > 0 && n === max;
                  return (
                    <td key={p.entity_id} className="px-3 py-2 text-center">
                      <span className={
                        n === 0 ? 'text-gray-600'
                        : leader ? 'text-amber-400 font-bold'
                        : 'text-gray-200'
                      }>
                        {n}{leader && persons.length > 1 ? ' 👑' : ''}
                      </span>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function Stats({ persons }) {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStatsMatrix()
      .then(setMatrix)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // entity_id → { name, colorIdx } for calendar chips
  const personIndex = useMemo(() => {
    const idx = {};
    persons.forEach((p, i) => { idx[p.entity_id] = { name: p.name, colorIdx: i }; });
    return idx;
  }, [persons]);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div>
        <h2 className="text-lg font-semibold">📊 Stats</h2>
        <p className="text-sm text-gray-400">Who has done what, and when</p>
      </div>

      <MonthCalendar persons={persons} personIndex={personIndex} />

      <ComparisonMatrix persons={persons} chores={matrix?.chores || []} />
    </div>
  );
}
