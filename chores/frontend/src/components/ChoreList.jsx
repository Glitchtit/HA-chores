import { useState, useEffect, useCallback, useRef } from 'react';
import * as api from '../api';
import { useGameEffects } from './effects/GameEffects';

const DIFFICULTY_COLORS = {
  easy: 'bg-emerald-600',
  medium: 'bg-amber-600',
  hard: 'bg-red-600',
};

const DIFFICULTY_XP = { easy: 5, medium: 10, hard: 20 };
const DIFFICULTY_LABELS = { easy: '❤️', medium: '💖', hard: '❤️‍🔥' };

const RECURRENCE_OPTIONS = [
  { value: '', label: 'One-time' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly:mon', label: 'Weekly (Mon)' },
  { value: 'weekly:mon,wed,fri', label: '3x/week (M/W/F)' },
  { value: 'weekly:tue,thu,sat', label: '3x/week (T/T/S)' },
  { value: 'weekly:sat', label: 'Weekly (Sat)' },
  { value: 'weekly:sun', label: 'Weekly (Sun)' },
  { value: 'biweekly:even', label: 'Every even week (Friday)' },
  { value: 'biweekly:odd', label: 'Every odd week (Friday)' },
  { value: 'monthly:1', label: 'Monthly (1st)' },
];

export default function ChoreList({ persons, activePerson, addToast }) {
  const [chores, setChores] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const { triggerEffects } = useGameEffects();
  const doneButtonRefs = useRef({});
  const [form, setForm] = useState({
    name: '', description: '', icon: '🧹', xp_reward: 10,
    difficulty: 'medium', recurrence: '', estimated_minutes: '',
    assignment_mode: 'manual', rotation_order: [],
    followup_chore_id: '',
  });
  const [assignChore, setAssignChore] = useState(null); // chore being assigned
  const [assignForm, setAssignForm] = useState({ person_id: '', due_date: '' });

  const load = useCallback(async () => {
    try {
      setChores(await api.getChores(false));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  const resetForm = () => {
    setForm({
      name: '', description: '', icon: '🧹', xp_reward: 10,
      difficulty: 'medium', recurrence: '', estimated_minutes: '',
      assignment_mode: 'manual', rotation_order: [],
      followup_chore_id: '',
    });
    setEditId(null);
    setShowForm(false);
  };

  const openEdit = (chore) => {
    setForm({
      name: chore.name,
      description: chore.description,
      icon: chore.icon,
      xp_reward: chore.xp_reward,
      difficulty: chore.difficulty,
      recurrence: chore.recurrence || '',
      estimated_minutes: chore.estimated_minutes || '',
      assignment_mode: chore.assignment_mode,
      rotation_order: chore.rotation_order || [],
      followup_chore_id: chore.followup_chore_id ?? '',
    });
    setEditId(chore.id);
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = {
      ...form,
      xp_reward: parseInt(form.xp_reward) || 10,
      estimated_minutes: form.estimated_minutes ? parseInt(form.estimated_minutes) : null,
      recurrence: form.recurrence || null,
      rotation_order: form.rotation_order.length > 0 ? form.rotation_order : null,
      followup_chore_id: form.followup_chore_id ? parseInt(form.followup_chore_id) : null,
    };
    try {
      if (editId) {
        await api.updateChore(editId, data);
        addToast('Chore updated', 'success');
      } else {
        await api.createChore(data);
        addToast('Chore created', 'success');
      }
      resetForm();
      load();
    } catch {
      addToast('Failed to save chore', 'error');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this chore and all its instances?')) return;
    try {
      await api.deleteChore(id);
      addToast('Chore deleted', 'success');
      load();
    } catch {
      addToast('Failed to delete', 'error');
    }
  };

  const handleToggleActive = async (chore) => {
    try {
      await api.updateChore(chore.id, { active: !chore.active });
      load();
    } catch {
      addToast('Failed to update', 'error');
    }
  };

  const handleQuickDone = async (chore) => {
    if (!activePerson) { addToast('No active person selected', 'error'); return; }
    if (!confirm(`Mark "${chore.name}" as done right now?`)) return;
    try {
      const today = new Date().toISOString().slice(0, 10);
      const statsBeforePromise = api.getPersonStats(activePerson).catch(() => null);
      const instance = await api.createInstance({
        chore_id: chore.id,
        due_date: today,
        assigned_to: activePerson,
      });
      const [result, statsBefore] = await Promise.all([
        api.completeInstance(instance.id, activePerson),
        statsBeforePromise,
      ]);
      addToast(`✅ +${result.xp_awarded} XP${result.leveled_up ? ' · LEVEL UP! 🎉' : ''}`, 'success');
      if (result.followup_triggered && result.followup_name) {
        addToast(`🔗 "${result.followup_name}" is now up for grabs!`, 'info');
      }
      const oldXP = statsBefore ? statsBefore.xp_total % 100 : 0;
      const newXP = ((statsBefore ? statsBefore.xp_total : 0) + result.xp_awarded) % 100;
      triggerEffects(result, doneButtonRefs.current[chore.id], null, oldXP, newXP);
    } catch {
      addToast('Failed to record chore', 'error');
    }
  };

  const openAssign = (chore) => {
    setAssignChore(chore);
    setAssignForm({
      person_id: persons[0]?.entity_id || '',
      due_date: new Date().toISOString().slice(0, 10),
    });
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    try {
      await api.createInstance({
        chore_id: assignChore.id,
        due_date: assignForm.due_date,
        assigned_to: assignForm.person_id,
      });
      addToast(`Assigned to ${persons.find(p => p.entity_id === assignForm.person_id)?.name || 'person'}`, 'success');
      setAssignChore(null);
    } catch {
      addToast('Failed to assign chore', 'error');
    }
  };

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">📋 Manage Chores</h2>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 rounded-lg text-sm font-medium"
        >
          + New Chore
        </button>
      </div>

      {/* Form modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
             onClick={() => resetForm()}>
          <div className="bg-gray-800 rounded-xl p-5 w-full max-w-md max-h-[90vh] overflow-auto"
               onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">
              {editId ? 'Edit Chore' : 'New Chore'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="flex gap-3">
                <div className="w-16">
                  <label className="text-xs text-gray-400">Icon</label>
                  <input
                    value={form.icon}
                    onChange={e => setForm(f => ({ ...f, icon: e.target.value }))}
                    className="w-full bg-gray-700 rounded px-2 py-2 text-center text-2xl"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-400">Name *</label>
                  <input
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    required
                    className="w-full bg-gray-700 rounded px-3 py-2"
                    placeholder="Vacuum living room"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-400">Description</label>
                <textarea
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full bg-gray-700 rounded px-3 py-2 h-20"
                  placeholder="Optional details..."
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400">Difficulty</label>
                  <select
                    value={form.difficulty}
                    onChange={e => {
                      const diff = e.target.value;
                      setForm(f => ({
                        ...f,
                        difficulty: diff,
                        // Only auto-set XP when creating; in edit mode the user controls it
                        ...(!editId && { xp_reward: DIFFICULTY_XP[diff] }),
                      }));
                    }}
                    className="w-full bg-gray-700 rounded px-2 py-2"
                  >
                    <option value="easy">❤️ (5 XP)</option>
                    <option value="medium">💖 (10 XP)</option>
                    <option value="hard">❤️‍🔥 (20 XP)</option>
                  </select>
                </div>
                {editId ? (
                  <div>
                    <label className="text-xs text-gray-400">XP Reward</label>
                    <input
                      type="number" min="1" value={form.xp_reward}
                      onChange={e => setForm(f => ({ ...f, xp_reward: e.target.value }))}
                      className="w-full bg-gray-700 rounded px-2 py-2"
                    />
                  </div>
                ) : (
                  <div>
                    <label className="text-xs text-gray-400">Est. min</label>
                    <input
                      type="number" min="1" value={form.estimated_minutes}
                      onChange={e => setForm(f => ({ ...f, estimated_minutes: e.target.value }))}
                      className="w-full bg-gray-700 rounded px-2 py-2"
                      placeholder="15"
                    />
                  </div>
                )}
              </div>

              {editId && (
                <div>
                  <label className="text-xs text-gray-400">Est. min</label>
                  <input
                    type="number" min="1" value={form.estimated_minutes}
                    onChange={e => setForm(f => ({ ...f, estimated_minutes: e.target.value }))}
                    className="w-full bg-gray-700 rounded px-2 py-2"
                    placeholder="15"
                  />
                </div>
              )}

              <div>
                <label className="text-xs text-gray-400">Schedule</label>
                <select
                  value={form.recurrence}
                  onChange={e => setForm(f => ({ ...f, recurrence: e.target.value }))}
                  className="w-full bg-gray-700 rounded px-3 py-2"
                >
                  {RECURRENCE_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-gray-400">Assignment Mode</label>
                <select
                  value={form.assignment_mode}
                  onChange={e => setForm(f => ({ ...f, assignment_mode: e.target.value }))}
                  className="w-full bg-gray-700 rounded px-3 py-2"
                >
                  <option value="manual">Manual</option>
                  <option value="rotation">Rotation</option>
                  <option value="claim">Claim (anyone can grab)</option>
                </select>
              </div>

              {form.assignment_mode === 'rotation' && persons.length > 0 && (
                <div>
                  <label className="text-xs text-gray-400">Rotation Order</label>
                  <div className="space-y-1 mt-1">
                    {persons.map(p => (
                      <label key={p.entity_id} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={form.rotation_order.includes(p.entity_id)}
                          onChange={(e) => {
                            setForm(f => ({
                              ...f,
                              rotation_order: e.target.checked
                                ? [...f.rotation_order, p.entity_id]
                                : f.rotation_order.filter(id => id !== p.entity_id),
                            }));
                          }}
                          className="rounded"
                        />
                        {p.name}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs text-gray-400">Follow-up chore <span className="text-gray-600">(optional)</span></label>
                <select
                  value={form.followup_chore_id}
                  onChange={e => setForm(f => ({ ...f, followup_chore_id: e.target.value }))}
                  className="w-full bg-gray-700 rounded px-3 py-2"
                >
                  <option value="">— None —</option>
                  {chores
                    .filter(c => c.active && c.id !== editId)
                    .map(c => (
                      <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                    ))}
                </select>
                {form.followup_chore_id && (
                  <p className="text-xs text-gray-500 mt-1">
                    When this chore is completed, the follow-up will be automatically assigned as claimable today.
                  </p>
                )}
              </div>

              <div className="flex gap-2 pt-2">
                <button type="submit"
                  className="flex-1 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg font-medium">
                  {editId ? 'Update' : 'Create'}
                </button>
                <button type="button" onClick={resetForm}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign modal */}
      {assignChore && (
        <div className="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
             onClick={() => setAssignChore(null)}>
          <div className="bg-gray-800 rounded-xl p-5 w-full max-w-sm"
               onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-1">Assign Chore</h3>
            <p className="text-sm text-gray-400 mb-4">{assignChore.icon} {assignChore.name}</p>
            <form onSubmit={handleAssign} className="space-y-3">
              <div>
                <label className="text-xs text-gray-400">Assign to</label>
                <select
                  value={assignForm.person_id}
                  onChange={e => setAssignForm(f => ({ ...f, person_id: e.target.value }))}
                  required
                  className="w-full bg-gray-700 rounded px-3 py-2 mt-1"
                >
                  {persons.map(p => (
                    <option key={p.entity_id} value={p.entity_id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400">Due date</label>
                <input
                  type="date"
                  value={assignForm.due_date}
                  onChange={e => setAssignForm(f => ({ ...f, due_date: e.target.value }))}
                  required
                  className="w-full bg-gray-700 rounded px-3 py-2 mt-1"
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button type="submit"
                  className="flex-1 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg font-medium">
                  Assign
                </button>
                <button type="button" onClick={() => setAssignChore(null)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Chore list */}
      {chores.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-2">📋</div>
          <p>No chores yet. Create your first one!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {chores.map(c => (
            <div key={c.id}
              className={`bg-gray-800 rounded-lg p-4 ${!c.active ? 'opacity-50' : ''}`}>
              {/* Chore info */}
              <div className="flex items-center gap-3 min-w-0 mb-3">
                <span className="text-3xl shrink-0">{c.icon}</span>
                <div className="min-w-0">
                  <div className="font-semibold text-base truncate">{c.name}</div>
                  <div className="flex flex-wrap gap-2 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${DIFFICULTY_COLORS[c.difficulty]}`}>
                      {DIFFICULTY_LABELS[c.difficulty] || c.difficulty}
                    </span>
                    <span className="text-xs text-gray-500">{c.xp_reward} XP</span>
                    {c.recurrence && (
                      <span className="text-xs text-blue-400">🔄 {c.recurrence}</span>
                    )}
                    <span className="text-xs text-gray-500">{c.assignment_mode}</span>
                    {c.followup_chore_id && (() => {
                      const fu = chores.find(x => x.id === c.followup_chore_id);
                      return fu ? (
                        <span className="text-xs text-purple-400">🔗 {fu.icon} {fu.name}</span>
                      ) : null;
                    })()}
                  </div>
                </div>
              </div>
              {/* Action buttons row */}
              <div className="flex gap-2">
                {c.active && (
                  <button onClick={() => handleQuickDone(c)}
                    ref={el => { doneButtonRefs.current[c.id] = el; }}
                    className="flex-1 py-2.5 bg-green-700 hover:bg-green-600 rounded-lg text-base font-medium transition-colors"
                    title="Quick done – mark as completed now">
                    ✅ Done
                  </button>
                )}
                {c.active && (
                  <button onClick={() => openAssign(c)}
                    className="flex-1 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-base font-medium transition-colors"
                    title="Assign to person">
                    👤 Assign
                  </button>
                )}
                <button onClick={() => openEdit(c)}
                  className="flex-1 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-base font-medium transition-colors"
                  title="Edit">
                  ✏️ Edit
                </button>
                <button onClick={() => handleToggleActive(c)}
                  className="py-2.5 px-4 bg-gray-700 hover:bg-gray-600 rounded-lg text-base transition-colors"
                  title={c.active ? 'Deactivate' : 'Activate'}>
                  {c.active ? '⏸️' : '▶️'}
                </button>
                <button onClick={() => handleDelete(c.id)}
                  className="py-2.5 px-4 bg-gray-700 hover:bg-red-900 rounded-lg text-base text-red-400 transition-colors"
                  title="Delete">
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
