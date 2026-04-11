import { useState, useEffect, useCallback } from 'react';
import * as api from './api';
import Dashboard from './components/Dashboard';
import ChoreList from './components/ChoreList';
import MyChores from './components/MyChores';
import Leaderboard from './components/Leaderboard';
import Achievements from './components/Achievements';
import Settings from './components/Settings';

const TABS = [
  { id: 'dashboard', icon: '🏠', label: 'Dashboard' },
  { id: 'chores',    icon: '📋', label: 'Chores' },
  { id: 'my',        icon: '✅', label: 'My Chores' },
  { id: 'leader',    icon: '🏆', label: 'Leaderboard' },
  { id: 'badges',    icon: '🎖️', label: 'Achievements' },
  { id: 'settings',  icon: '⚙️', label: 'Settings' },
];

function Toasts({ toasts, onDismiss }) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {toasts.map(t => (
        <div
          key={t.id}
          onClick={() => onDismiss(t.id)}
          className={`px-4 py-3 rounded-lg shadow-lg cursor-pointer text-sm animate-slide-up ${
            t.type === 'error'   ? 'bg-red-600' :
            t.type === 'success' ? 'bg-emerald-600' :
            'bg-gray-700'
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState('dashboard');
  const [ready, setReady] = useState(false);
  const [checking, setChecking] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [persons, setPersons] = useState([]);
  const [activePerson, setActivePerson] = useState(null);
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // Health check with retry
  useEffect(() => {
    let cancelled = false;
    let tries = 0;
    const check = async () => {
      while (!cancelled && tries < 60) {
        tries++;
        setAttempt(tries);
        try {
          await api.getHealth();
          if (!cancelled) { setReady(true); setChecking(false); }
          return;
        } catch {
          await new Promise(r => setTimeout(r, Math.min(tries * 1000, 5000)));
        }
      }
      if (!cancelled) setChecking(false);
    };
    check();
    return () => { cancelled = true; };
  }, []);

  // Load persons once ready
  useEffect(() => {
    if (!ready) return;
    api.getPersons().then(p => {
      setPersons(p);
      if (p.length > 0 && !activePerson) setActivePerson(p[0].entity_id);
    }).catch(() => {});
  }, [ready]);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🧹</div>
          <p className="text-gray-400">Connecting to Chores API... (attempt {attempt})</p>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="text-5xl mb-4">❌</div>
          <p className="text-red-400">Could not connect to Chores API</p>
        </div>
      </div>
    );
  }

  const renderTab = () => {
    switch (tab) {
      case 'dashboard':
        return <Dashboard activePerson={activePerson} persons={persons} addToast={addToast} />;
      case 'chores':
        return <ChoreList persons={persons} addToast={addToast} />;
      case 'my':
        return <MyChores activePerson={activePerson} persons={persons} addToast={addToast} />;
      case 'leader':
        return <Leaderboard persons={persons} />;
      case 'badges':
        return <Achievements activePerson={activePerson} persons={persons} />;
      case 'settings':
        return <Settings persons={persons} activePerson={activePerson}
                         setActivePerson={setActivePerson} addToast={addToast} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 flex flex-col">
      <Toasts toasts={toasts} onDismiss={dismissToast} />

      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold flex items-center gap-2">
          🧹 <span>Chores</span>
        </h1>
        {activePerson && (
          <div className="text-sm text-gray-400">
            {persons.find(p => p.entity_id === activePerson)?.name || ''}
          </div>
        )}
      </header>

      {/* Content */}
      <main className="flex-1 overflow-auto p-4">
        {renderTab()}
      </main>

      {/* Tab bar */}
      <nav className="bg-gray-800 border-t border-gray-700 flex justify-around py-2">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors ${
              tab === t.id
                ? 'text-amber-400'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <span className="text-lg">{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
