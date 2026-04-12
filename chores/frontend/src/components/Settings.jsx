import { useState, useCallback, useEffect, useRef } from 'react';
import * as api from '../api';

const HOURS = Array.from({ length: 24 }, (_, i) => ({
  value: i,
  label: `${String(i).padStart(2, '0')}:00`,
}));

const WEEKDAYS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
];

const NOTIF_DEFAULTS = {
  notif_assigned: { enabled: true },
  notif_overdue:  { enabled: true },
  notif_badge:    { enabled: true },
  notif_levelup:  { enabled: true },
  notif_reminder: { enabled: true, when: 'day_of', hour: 8 },
  notif_streak:   { enabled: true, hour: 18 },
  notif_weekly:   { enabled: true, weekday: 0, hour: 9 },
};

function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
        checked ? 'bg-amber-500' : 'bg-gray-600'
      }`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
        checked ? 'translate-x-6' : 'translate-x-1'
      }`} />
    </button>
  );
}

function NotifRow({ icon, label, description, cfgKey, cfg, onChange }) {
  const enabled = cfg?.enabled ?? true;
  return (
    <div className="py-3 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg shrink-0">{icon}</span>
          <div className="min-w-0">
            <div className="text-sm font-medium">{label}</div>
            {description && <div className="text-xs text-gray-500">{description}</div>}
          </div>
        </div>
        <Toggle checked={enabled} onChange={v => onChange({ ...cfg, enabled: v })} />
      </div>
    </div>
  );
}

export default function Settings({ persons, activePerson, setActivePerson, addToast }) {
  const [syncing, setSyncing] = useState(false);
  const [testingNotify, setTestingNotify] = useState(false);
  const [notifCfg, setNotifCfg] = useState(NOTIF_DEFAULTS);
  const saveTimers = useRef({});

  // Load notification config for the active person whenever they change
  useEffect(() => {
    if (!activePerson) { setNotifCfg(NOTIF_DEFAULTS); return; }
    api.getConfig().then(rows => {
      const loaded = { ...NOTIF_DEFAULTS };
      for (const row of rows) {
        // Keys are stored as "{cfgKey}:{person_entity_id}"
        const suffix = `:${activePerson}`;
        if (row.key.endsWith(suffix)) {
          const baseKey = row.key.slice(0, -suffix.length);
          if (baseKey in NOTIF_DEFAULTS) {
            try { loaded[baseKey] = { ...NOTIF_DEFAULTS[baseKey], ...JSON.parse(row.value) }; }
            catch { /* use default */ }
          }
        }
      }
      setNotifCfg(loaded);
    }).catch(() => {});
  }, [activePerson]);

  // Debounced auto-save — key is scoped to the active person
  const updateNotifCfg = useCallback((key, value) => {
    if (!activePerson) return;
    setNotifCfg(prev => ({ ...prev, [key]: value }));
    const scopedKey = `${key}:${activePerson}`;
    clearTimeout(saveTimers.current[scopedKey]);
    saveTimers.current[scopedKey] = setTimeout(async () => {
      try {
        await api.setConfigValue(scopedKey, JSON.stringify(value));
      } catch {
        addToast('Failed to save notification setting', 'error');
      }
    }, 600);
  }, [activePerson, addToast]);

  const handleSyncPersons = useCallback(async () => {
    setSyncing(true);
    try {
      const synced = await api.syncPersons();
      addToast(`Synced ${synced.length} persons from Home Assistant`, 'success');
    } catch {
      addToast('Failed to sync persons', 'error');
    }
    setSyncing(false);
  }, [addToast]);

  const handleTestNotification = useCallback(async () => {
    if (!activePerson) return;
    setTestingNotify(true);
    try {
      await api.testNotification(activePerson);
      addToast('📲 Test notification sent!', 'success');
    } catch {
      addToast('No mobile device found for this person', 'error');
    }
    setTestingNotify(false);
  }, [activePerson, addToast]);

  const sel = 'bg-gray-700 rounded px-2 py-1.5 text-sm border border-gray-600 focus:outline-none focus:border-amber-500';

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h2 className="text-lg font-semibold">⚙️ Settings</h2>

      {/* Active person selection */}
      <div className="bg-gray-800 rounded-xl p-5 space-y-3">
        <h3 className="font-medium">👤 Active Person</h3>
        <p className="text-sm text-gray-400">
          Select who is currently using the app. This determines whose chores are shown on the Dashboard and My Chores tabs.
        </p>
        <div className="space-y-2">
          {persons.map(p => (
            <button
              key={p.entity_id}
              onClick={() => setActivePerson(p.entity_id)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${
                activePerson === p.entity_id
                  ? 'bg-amber-600/20 border border-amber-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center overflow-hidden">
                {p.avatar_url ? (
                  <img src={p.avatar_url} className="w-full h-full object-cover" alt="" />
                ) : (
                  <span className="text-lg">👤</span>
                )}
              </div>
              <div className="text-left">
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-gray-400">
                  Lv {p.level} · {p.xp_total} XP · 🔥 {p.current_streak}d streak
                </div>
              </div>
              {activePerson === p.entity_id && (
                <span className="ml-auto text-amber-400">✓</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Notification Settings */}
      <div className="bg-gray-800 rounded-xl p-5">
        <h3 className="font-medium mb-1">🔔 Notifications</h3>
        <p className="text-xs text-gray-500 mb-3">
          {activePerson
            ? <>Settings for <span className="text-amber-400">{persons.find(p => p.entity_id === activePerson)?.name ?? activePerson}</span>. Changes save automatically.</>
            : 'Select a person above to configure their notification preferences.'}
        </p>

        {!activePerson ? (
          <p className="text-sm text-gray-500 italic">No person selected.</p>
        ) : (<>

        {/* Immediate notifications */}
        <div className="divide-y divide-gray-700">
          <NotifRow icon="🧹" label="Chore Assigned" description="When a chore is assigned to you"
            cfgKey="notif_assigned" cfg={notifCfg.notif_assigned}
            onChange={v => updateNotifCfg('notif_assigned', v)} />
          <NotifRow icon="⏰" label="Chore Overdue" description="When a chore passes its due date"
            cfgKey="notif_overdue" cfg={notifCfg.notif_overdue}
            onChange={v => updateNotifCfg('notif_overdue', v)} />
          <NotifRow icon="🏆" label="Achievement Unlocked" description="When you earn a new badge"
            cfgKey="notif_badge" cfg={notifCfg.notif_badge}
            onChange={v => updateNotifCfg('notif_badge', v)} />
          <NotifRow icon="📈" label="Level Up" description="When you reach a new level"
            cfgKey="notif_levelup" cfg={notifCfg.notif_levelup}
            onChange={v => updateNotifCfg('notif_levelup', v)} />
        </div>

        {/* Divider */}
        <div className="mt-3 mb-1 text-xs text-gray-500 uppercase tracking-wider">Reminders</div>
        <div className="divide-y divide-gray-700">

          {/* Chore Reminder */}
          <div className="py-3 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-lg shrink-0">🔔</span>
                <span className="text-sm font-medium">Chore Reminder</span>
              </div>
              <Toggle
                checked={notifCfg.notif_reminder.enabled}
                onChange={v => updateNotifCfg('notif_reminder', { ...notifCfg.notif_reminder, enabled: v })}
              />
            </div>
            {notifCfg.notif_reminder.enabled && (
              <div className="flex items-center gap-2 pl-8 flex-wrap">
                <select
                  value={notifCfg.notif_reminder.when}
                  onChange={e => updateNotifCfg('notif_reminder', { ...notifCfg.notif_reminder, when: e.target.value })}
                  className={sel}
                >
                  <option value="day_of">Day of</option>
                  <option value="day_before">Day before</option>
                </select>
                <span className="text-xs text-gray-500">at</span>
                <select
                  value={notifCfg.notif_reminder.hour}
                  onChange={e => updateNotifCfg('notif_reminder', { ...notifCfg.notif_reminder, hour: Number(e.target.value) })}
                  className={sel}
                >
                  {HOURS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
                </select>
              </div>
            )}
          </div>

          {/* Streak Warning */}
          <div className="py-3 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-lg shrink-0">🔥</span>
                <span className="text-sm font-medium">Streak Warning</span>
              </div>
              <Toggle
                checked={notifCfg.notif_streak.enabled}
                onChange={v => updateNotifCfg('notif_streak', { ...notifCfg.notif_streak, enabled: v })}
              />
            </div>
            {notifCfg.notif_streak.enabled && (
              <div className="flex items-center gap-2 pl-8 flex-wrap">
                <span className="text-xs text-gray-500">Send at</span>
                <select
                  value={notifCfg.notif_streak.hour}
                  onChange={e => updateNotifCfg('notif_streak', { ...notifCfg.notif_streak, hour: Number(e.target.value) })}
                  className={sel}
                >
                  {HOURS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
                </select>
              </div>
            )}
          </div>

          {/* Weekly Summary */}
          <div className="py-3 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-lg shrink-0">📊</span>
                <span className="text-sm font-medium">Weekly Summary</span>
              </div>
              <Toggle
                checked={notifCfg.notif_weekly.enabled}
                onChange={v => updateNotifCfg('notif_weekly', { ...notifCfg.notif_weekly, enabled: v })}
              />
            </div>
            {notifCfg.notif_weekly.enabled && (
              <div className="flex items-center gap-2 pl-8 flex-wrap">
                <span className="text-xs text-gray-500">Every</span>
                <select
                  value={notifCfg.notif_weekly.weekday}
                  onChange={e => updateNotifCfg('notif_weekly', { ...notifCfg.notif_weekly, weekday: Number(e.target.value) })}
                  className={sel}
                >
                  {WEEKDAYS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
                <span className="text-xs text-gray-500">at</span>
                <select
                  value={notifCfg.notif_weekly.hour}
                  onChange={e => updateNotifCfg('notif_weekly', { ...notifCfg.notif_weekly, hour: Number(e.target.value) })}
                  className={sel}
                >
                  {HOURS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
                </select>
              </div>
            )}
          </div>
        </div>
        </>)}
      </div>

      {/* HA Sync */}
      <div className="bg-gray-800 rounded-xl p-5 space-y-3">
        <h3 className="font-medium">🏠 Home Assistant Integration</h3>
        <p className="text-sm text-gray-400">
          Sync household members from Home Assistant Person entities.
        </p>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={handleSyncPersons}
            disabled={syncing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium"
          >
            {syncing ? 'Syncing...' : '🔄 Sync Persons from HA'}
          </button>
          <button
            onClick={handleTestNotification}
            disabled={testingNotify || !activePerson}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded-lg text-sm font-medium"
          >
            {testingNotify ? 'Sending...' : '🔔 Test Notification'}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Test notification sends to the active person's linked devices.
        </p>
      </div>

      {/* About */}
      <div className="bg-gray-800 rounded-xl p-5">
        <h3 className="font-medium mb-2">ℹ️ About</h3>
        <p className="text-sm text-gray-400">
          Chores is a gamified household chore management app for Home Assistant.
          Earn XP, level up, unlock badges, and compete on the leaderboard!
        </p>
        <div className="mt-3 text-xs text-gray-600">
          Made with ❤️ for Home Assistant
        </div>
      </div>
    </div>
  );
}

