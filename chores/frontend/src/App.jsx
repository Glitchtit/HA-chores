import { useState, useEffect, useCallback, useRef } from 'react';
import * as api from './api';
import Dashboard from './components/Dashboard';
import ChoreList from './components/ChoreList';
import MyChores from './components/MyChores';
import Leaderboard from './components/Leaderboard';
import Achievements from './components/Achievements';
import Settings from './components/Settings';
import HouseholdOverview from './components/HouseholdOverview';
import { GameEffectsProvider } from './components/effects/GameEffects';

const PERSONAL_TABS = [
  { id: 'dashboard', icon: '🏠', label: 'Dashboard' },
  { id: 'chores',    icon: '📋', label: 'Chores' },
  { id: 'my',        icon: '✅', label: 'My Chores' },
  { id: 'leader',    icon: '🏆', label: 'Leaderboard' },
  { id: 'badges',    icon: '🎖️', label: 'Achievements' },
  { id: 'settings',  icon: '⚙️', label: 'Settings' },
];

const HOUSEHOLD_TABS = [
  { id: 'overview',  icon: '🏡', label: 'Overview' },
  { id: 'chores',    icon: '📋', label: 'Chores' },
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
  const [autoDetected, setAutoDetected] = useState(false);
  const [isHouseholdMode, setIsHouseholdMode] = useState(false);
  const [toasts, setToasts] = useState([]);
  const pickerRef = useRef(null);

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

  const [showPersonPicker, setShowPersonPicker] = useState(false);

  // Close person picker on outside click
  useEffect(() => {
    if (!showPersonPicker) return;
    const handler = (e) => { if (pickerRef.current && !pickerRef.current.contains(e.target)) setShowPersonPicker(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPersonPicker]);

  // Load persons once ready, then auto-detect active person
  useEffect(() => {
    if (!ready) return;
    api.getPersons().then(async p => {
      setPersons(p);
      if (p.length === 0) return;
      try {
        const me = await api.getMe();
        if (me && p.some(person => person.entity_id === me.entity_id)) {
          setActivePerson(me.entity_id);
          setAutoDetected(true);
          setIsHouseholdMode(false);
        } else {
          // No HA user matched — household/shared device mode
          setIsHouseholdMode(true);
          setActivePerson(null);
          setAutoDetected(false);
          setTab('overview');
        }
      } catch {
        setIsHouseholdMode(true);
        setActivePerson(null);
        setAutoDetected(false);
        setTab('overview');
      }
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
      case 'overview':
        return (
          <HouseholdOverview
            persons={persons}
            addToast={addToast}
            onSelectPerson={(id) => { setActivePerson(id); setAutoDetected(false); setTab('dashboard'); }}
          />
        );
      case 'dashboard':
        return <Dashboard activePerson={activePerson} persons={persons} addToast={addToast} />;
      case 'chores':
        return <ChoreList persons={persons} activePerson={activePerson} addToast={addToast} />;
      case 'my':
        return <MyChores activePerson={activePerson} persons={persons} addToast={addToast} />;
      case 'leader':
        return <Leaderboard persons={persons} />;
      case 'badges':
        return <Achievements activePerson={activePerson} persons={persons} />;
      case 'settings':
        return <Settings persons={persons} activePerson={activePerson}
                         setActivePerson={(id) => { setActivePerson(id); setAutoDetected(false); }}
                         addToast={addToast}
                         onPersonsChange={() => api.getPersons().then(setPersons)} />;
      default:
        return null;
    }
  };

  // Active tab set: show household tabs when no person is selected in household mode
  const TABS = (isHouseholdMode && !activePerson) ? HOUSEHOLD_TABS : PERSONAL_TABS;

  return (
    <GameEffectsProvider>
      <div className="min-h-screen bg-gray-900 text-gray-100 flex flex-col lg:flex-row">
        <Toasts toasts={toasts} onDismiss={dismissToast} />

      {/* Sidebar nav — visible on lg screens as left rail */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 bg-gray-800 border-t border-gray-700 flex justify-around py-2
                      lg:top-0 lg:bottom-0 lg:right-auto lg:w-20 lg:flex-col lg:justify-start lg:pt-16 lg:border-t-0 lg:border-r lg:border-gray-700 lg:gap-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex flex-col items-center gap-0.5 px-2 py-1 transition-all
                        lg:w-full lg:py-3 lg:px-0 lg:rounded-none
                        ${tab === t.id
                          ? 'grayscale-0 opacity-100 text-amber-400'
                          : 'grayscale opacity-50 text-gray-400 hover:opacity-75'
                        }`}
          >
            <span className="text-2xl lg:text-2xl">{t.icon}</span>
            <span className="hidden sm:block text-xs lg:block lg:text-[10px]">{t.label}</span>
          </button>
        ))}
      </nav>

      {/* Right-side content area */}
      <div className="flex-1 flex flex-col lg:ml-20 min-w-0">
        {/* Header */}
        <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between relative">
          <h1 className="text-xl font-bold flex items-center gap-2">
            🧹 <span>Chores</span>
          </h1>

          {/* Household mode — no person active */}
          {isHouseholdMode && !activePerson && (
            <span className="text-sm text-gray-400 bg-gray-700 px-2 py-1 rounded">
              🏡 Household
            </span>
          )}

          {/* Person picker (personal mode or household mode with a person selected) */}
          {activePerson && (
            <div className="relative" ref={pickerRef}>
              <button
                onClick={() => setShowPersonPicker(v => !v)}
                className="flex items-center gap-1.5 hover:bg-gray-700 rounded px-2 py-1 transition-colors"
                title={autoDetected ? "Auto-detected from your HA login" : "Tap to switch profile"}
              >
                <span className="text-sm text-gray-300">
                  {persons.find(p => p.entity_id === activePerson)?.name || ''}
                </span>
                {autoDetected
                  ? <span className="text-xs bg-emerald-800/60 text-emerald-400 px-1.5 py-0.5 rounded">you</span>
                  : <span className="text-xs bg-amber-800/60 text-amber-400 px-1.5 py-0.5 rounded" title="Could not auto-detect your profile — tap to select">▾</span>
                }
              </button>
              {showPersonPicker && (
                <div className="absolute right-0 top-full mt-1 bg-gray-700 border border-gray-600 rounded shadow-lg z-50 min-w-40">
                  <button
                    onClick={() => { setActivePerson(null); setIsHouseholdMode(true); setTab('overview'); setShowPersonPicker(false); }}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-600 transition-colors text-blue-300 border-b border-gray-600"
                  >
                    🏡 Household Overview
                  </button>
                  {persons.map(p => (
                    <button
                      key={p.entity_id}
                      onClick={() => { setActivePerson(p.entity_id); setAutoDetected(false); setShowPersonPicker(false); }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-600 transition-colors ${p.entity_id === activePerson ? 'text-amber-400 font-semibold' : 'text-gray-200'}`}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </header>

        {/* Content */}
        <main
          className="flex-1 overflow-auto p-4 pb-20 lg:pb-6"
          style={{ paddingBottom: 'calc(5rem + env(safe-area-inset-bottom))' }}
        >
          {renderTab()}
        </main>
      </div>
    </div>
    </GameEffectsProvider>
  );
}
