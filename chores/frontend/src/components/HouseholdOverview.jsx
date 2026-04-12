import { useState, useEffect, useCallback } from 'react';
import * as api from '../api';
import PersonPickerModal from './PersonPickerModal';

export default function HouseholdOverview({ persons, addToast, onSelectPerson }) {
  const [leaderboard, setLeaderboard] = useState([]);
  const [todayChores, setTodayChores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pickerModal, setPickerModal] = useState(null); // { instanceId, action: 'claim'|'complete' }

  const load = useCallback(async () => {
    try {
      const [lb, chores] = await Promise.all([
        api.getLeaderboard(),
        api.getTodayInstances(),
      ]);
      setLeaderboard(lb.entries || []);
      setTodayChores(chores);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handlePickerSelect = async (personId) => {
    if (!pickerModal) return;
    const { instanceId, action } = pickerModal;
    setPickerModal(null);
    try {
      if (action === 'claim') {
        await api.claimInstance(instanceId, personId);
        addToast('🙋 Chore claimed!', 'success');
      } else {
        await api.completeInstance(instanceId, personId);
        addToast('✅ Chore done! +XP', 'success');
      }
      load();
    } catch {
      addToast('Action failed', 'error');
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  // Count pending chores per person for badge
  const pendingByPerson = {};
  todayChores.forEach(ci => {
    if (ci.assigned_to && ci.status !== 'completed' && ci.status !== 'skipped') {
      pendingByPerson[ci.assigned_to] = (pendingByPerson[ci.assigned_to] || 0) + 1;
    }
  });

  const done = todayChores.filter(c => c.status === 'completed').length;
  const total = todayChores.length;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Summary strip */}
      {total > 0 && (
        <div className="bg-gray-800 rounded-xl px-5 py-3 flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Today's progress</span>
              <span>{done}/{total} done</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-green-400 rounded-full transition-all"
                style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Person cards */}
      <div>
        <h2 className="text-lg font-semibold mb-3">👨‍👩‍👧 Household</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {leaderboard.map((p) => (
            <button
              key={p.entity_id}
              onClick={() => onSelectPerson(p.entity_id)}
              className="bg-gray-800 hover:bg-gray-750 rounded-xl p-4 text-left transition-all border border-gray-700 hover:border-amber-500/50 active:scale-95 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <span className="w-10 h-10 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-xl">
                  {p.name.charAt(0).toUpperCase()}
                </span>
                {pendingByPerson[p.entity_id] > 0 && (
                  <span className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold shrink-0">
                    {pendingByPerson[p.entity_id]}
                  </span>
                )}
              </div>
              <div>
                <div className="font-semibold truncate">{p.name}</div>
                <div className="flex items-center gap-1.5 text-xs text-gray-400 mt-0.5 flex-wrap">
                  <span className="text-amber-400 font-semibold">Lv {p.level}</span>
                  <span>·</span>
                  <span>🔥 {p.current_streak}</span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{p.xp_total} XP · #{p.rank}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Today's chores — all */}
      <div>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          📅 Today's Chores
          <span className="text-sm font-normal text-gray-500">({total})</span>
        </h3>
        {total === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">🎉</div>
            <p>All done for today!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {todayChores.map(ci => {
              const assignedPerson = persons.find(p => p.entity_id === ci.assigned_to);
              const isCompleted = ci.status === 'completed';
              const isUnclaimedClaimMode = ci.chore_assignment_mode === 'claim' && !ci.assigned_to && !isCompleted;

              return (
                <div
                  key={ci.id}
                  className={`bg-gray-800 rounded-lg p-4 flex flex-wrap items-center gap-3 ${
                    ci.status === 'overdue' ? 'border border-red-500/40' : ''
                  } ${isCompleted ? 'opacity-50' : ''}`}
                >
                  <span className="text-2xl">{ci.chore_icon || '🧹'}</span>
                  <div className="flex-1 min-w-0">
                    <div className={`font-medium truncate ${isCompleted ? 'line-through text-gray-500' : ''}`}>
                      {ci.chore_name}
                    </div>
                    <div className="text-xs text-gray-400 flex items-center gap-1.5 flex-wrap mt-0.5">
                      {ci.status === 'overdue' && <span className="text-red-400">Overdue ·</span>}
                      <span className="capitalize">{ci.chore_difficulty}</span>
                      <span>·</span>
                      {isCompleted ? (
                        <span className="text-emerald-400">
                          Done{ci.completed_by ? ` by ${persons.find(p => p.entity_id === ci.completed_by)?.name || ci.completed_by}` : ''}
                        </span>
                      ) : assignedPerson ? (
                        <span className="text-blue-300">{assignedPerson.name}</span>
                      ) : (
                        <span className="bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">Unclaimed</span>
                      )}
                    </div>
                  </div>
                  {!isCompleted && (
                    <div className="flex gap-2 shrink-0">
                      {isUnclaimedClaimMode && (
                        <button
                          onClick={() => setPickerModal({ instanceId: ci.id, action: 'claim' })}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
                        >
                          Claim 🙋
                        </button>
                      )}
                      <button
                        onClick={() => setPickerModal({ instanceId: ci.id, action: 'complete' })}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
                      >
                        Done ✓
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {pickerModal && (
        <PersonPickerModal
          title={pickerModal.action === 'claim' ? 'Who is claiming this?' : 'Who completed this?'}
          persons={persons}
          onSelect={handlePickerSelect}
          onCancel={() => setPickerModal(null)}
        />
      )}
    </div>
  );
}
