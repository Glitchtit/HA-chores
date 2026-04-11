import { useState, useEffect, useCallback } from 'react';
import * as api from '../api';

export default function MyChores({ activePerson, persons, addToast }) {
  const [instances, setInstances] = useState([]);
  const [filter, setFilter] = useState('active');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const statusFilter = filter === 'active'
        ? 'pending,claimed,overdue'
        : filter === 'completed'
        ? 'completed'
        : 'pending,claimed,overdue,completed,skipped';
      const data = await api.getInstances({
        status: statusFilter,
        person: activePerson,
      });
      // Only show chores actually assigned/claimed/completed by this person
      setInstances(data.filter(ci =>
        ci.assigned_to === activePerson || ci.completed_by === activePerson
      ));
    } catch { /* ignore */ }
    setLoading(false);
  }, [activePerson, filter]);

  useEffect(() => { load(); }, [load]);

  const handleComplete = async (id) => {
    try {
      await api.completeInstance(id, activePerson);
      addToast('✅ Chore completed! +XP', 'success');
      load();
    } catch {
      addToast('Failed to complete', 'error');
    }
  };

  const handleClaim = async (id) => {
    try {
      await api.claimInstance(id, activePerson);
      addToast('🙋 Chore claimed!', 'success');
      load();
    } catch {
      addToast('Failed to claim', 'error');
    }
  };

  const handleSkip = async (id) => {
    try {
      await api.skipInstance(id);
      addToast('Chore skipped', 'info');
      load();
    } catch {
      addToast('Failed to skip', 'error');
    }
  };

  const personName = (entityId) =>
    persons.find(p => p.entity_id === entityId)?.name || entityId || 'Unassigned';

  const statusBadge = (status) => {
    const colors = {
      pending: 'bg-blue-600',
      claimed: 'bg-amber-600',
      completed: 'bg-emerald-600',
      overdue: 'bg-red-600',
      skipped: 'bg-gray-600',
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${colors[status] || 'bg-gray-600'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">✅ My Chores</h2>
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          {['active', 'completed', 'all'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                filter === f ? 'bg-amber-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : instances.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-2">{filter === 'active' ? '🎉' : '📭'}</div>
          <p>{filter === 'active' ? 'No chores pending!' : 'No chores found'}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {instances.map(ci => (
            <div key={ci.id}
              className={`bg-gray-800 rounded-lg p-4 ${
                ci.status === 'overdue' ? 'border border-red-500/50' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-2xl flex-shrink-0">{ci.chore_icon || '🧹'}</span>
                  <div className="min-w-0">
                    <div className="font-medium truncate">{ci.chore_name}</div>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {statusBadge(ci.status)}
                      <span className="text-xs text-gray-500">📅 {ci.due_date}</span>
                      {ci.assigned_to && (
                        <span className="text-xs text-gray-400">
                          👤 {personName(ci.assigned_to)}
                        </span>
                      )}
                      {ci.xp_awarded > 0 && (
                        <span className="text-xs text-amber-400">+{ci.xp_awarded} XP</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                {ci.status !== 'completed' && ci.status !== 'skipped' && (
                  <div className="flex gap-1 flex-shrink-0 ml-2">
                    {(!ci.assigned_to || ci.status === 'pending') && ci.assigned_to !== activePerson && (
                      <button
                        onClick={() => handleClaim(ci.id)}
                        className="px-2 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
                        title="Claim"
                      >
                        🙋
                      </button>
                    )}
                    <button
                      onClick={() => handleComplete(ci.id)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-xs font-medium"
                    >
                      Done ✓
                    </button>
                    <button
                      onClick={() => handleSkip(ci.id)}
                      className="px-2 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs"
                      title="Skip"
                    >
                      ⏭️
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
