/**
 * GameEffects — Candy Crush-style visual effects system.
 *
 * Usage:
 *   1. Wrap your app with <GameEffectsProvider>
 *   2. In any component: const { triggerEffects, triggerXPBar } = useGameEffects();
 *   3. After completing a chore call triggerEffects(completeResult, buttonEl, xpBarEl)
 */
import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

const GameEffectsContext = createContext(null);

export function useGameEffects() {
  return useContext(GameEffectsContext);
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function uid() {
  return Math.random().toString(36).slice(2);
}

const CONFETTI_COLORS = [
  '#f59e0b', '#10b981', '#3b82f6', '#ec4899',
  '#8b5cf6', '#f97316', '#14b8a6', '#facc15',
];

function randomBetween(a, b) {
  return a + Math.random() * (b - a);
}

/* ── FloatingXP ──────────────────────────────────────────────────────────── */

function FloatingXP({ xp, x, y, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 1200);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div
      className="animate-float-xp fixed z-[200] font-black text-xl pointer-events-none select-none"
      style={{
        left: x,
        top: y,
        color: '#fbbf24',
        textShadow: '0 0 12px rgba(251,191,36,0.9), 0 2px 4px rgba(0,0,0,0.8)',
        transform: 'translateX(-50%)',
      }}
    >
      +{xp} XP
    </div>
  );
}

/* ── Confetti ─────────────────────────────────────────────────────────────── */

function ConfettiBurst({ x, y, onDone }) {
  const count = 32;
  const particles = useRef(
    Array.from({ length: count }, (_, i) => {
      const angle = (i / count) * 360 + randomBetween(-10, 10);
      const dist = randomBetween(60, 140);
      const rad = (angle * Math.PI) / 180;
      const ex = Math.cos(rad) * dist;
      const ey = Math.sin(rad) * dist - randomBetween(20, 60); // upward bias
      const duration = randomBetween(0.55, 0.95);
      const size = randomBetween(5, 10);
      const color = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
      const isCircle = Math.random() > 0.5;
      return { ex, ey, duration, size, color, isCircle };
    })
  ).current;

  useEffect(() => {
    const t = setTimeout(onDone, 1100);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <>
      {particles.map((p, i) => (
        <div
          key={i}
          className="animate-confetti fixed z-[190] pointer-events-none"
          style={{
            left: x,
            top: y,
            width: p.size,
            height: p.size,
            borderRadius: p.isCircle ? '50%' : '2px',
            backgroundColor: p.color,
            '--confetti-end': `translate(${p.ex}px, ${p.ey}px) rotate(${randomBetween(-180, 180)}deg) scale(0)`,
            '--confetti-duration': `${p.duration}s`,
            marginLeft: -p.size / 2,
            marginTop: -p.size / 2,
          }}
        />
      ))}
    </>
  );
}

/* ── XPBarSparkle ─────────────────────────────────────────────────────────── */

function XPBarSparkle({ barEl, fromProgress, toProgress, onDone }) {
  const [particles, setParticles] = useState([]);
  const frameRef = useRef(null);
  const startRef = useRef(null);

  useEffect(() => {
    if (!barEl) { onDone(); return; }

    const DURATION = 900; // ms for the bar to fill
    const PARTICLE_INTERVAL = 50; // ms between particle spawns

    let lastParticle = 0;
    const spawned = [];

    const tick = (ts) => {
      if (!startRef.current) startRef.current = ts;
      const elapsed = ts - startRef.current;
      const progress = Math.min(elapsed / DURATION, 1);
      const currentFill = fromProgress + (toProgress - fromProgress) * progress;

      // Position at tip of XP bar
      const rect = barEl.getBoundingClientRect();
      const tipX = rect.left + rect.width * (currentFill / 100);
      const tipY = rect.top + rect.height / 2;

      if (ts - lastParticle > PARTICLE_INTERVAL) {
        lastParticle = ts;
        const count = 3;
        for (let i = 0; i < count; i++) {
          const angle = randomBetween(-150, -30); // mostly upward
          const dist = randomBetween(12, 28);
          const rad = (angle * Math.PI) / 180;
          const ex = Math.cos(rad) * dist;
          const ey = Math.sin(rad) * dist;
          spawned.push({
            id: uid(),
            x: tipX + randomBetween(-4, 4),
            y: tipY,
            ex,
            ey,
            dur: randomBetween(0.35, 0.65),
            size: randomBetween(3, 6),
            color: CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)],
          });
        }
        setParticles([...spawned]);
      }

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      } else {
        setTimeout(() => {
          onDone();
        }, 700);
      }
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [barEl, fromProgress, toProgress, onDone]);

  return (
    <>
      {particles.map(p => (
        <div
          key={p.id}
          className="animate-sparkle fixed z-[195] pointer-events-none rounded-full"
          style={{
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            '--sparkle-end': `translate(${p.ex}px, ${p.ey}px)`,
            '--sparkle-dur': `${p.dur}s`,
            marginLeft: -p.size / 2,
            marginTop: -p.size / 2,
          }}
        />
      ))}
    </>
  );
}

/* ── LevelUpOverlay ──────────────────────────────────────────────────────── */

const STAR_COUNT = 16;

function LevelUpOverlay({ oldLevel, newLevel, onDone }) {
  const [exiting, setExiting] = useState(false);

  const stars = useRef(
    Array.from({ length: STAR_COUNT }, () => ({
      x: randomBetween(10, 90),
      sy: randomBetween(60, 90),
      ey: randomBetween(-10, 30),
      dur: randomBetween(1.0, 2.0),
      delay: randomBetween(0, 0.8),
      size: randomBetween(14, 26),
      emoji: ['⭐', '✨', '🌟', '💫'][Math.floor(Math.random() * 4)],
    }))
  ).current;

  const dismiss = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    setTimeout(onDone, 400);
  }, [exiting, onDone]);

  return (
    <div
      className={`fixed inset-0 z-[210] flex flex-col items-center justify-center
                  bg-black/80 backdrop-blur-sm cursor-pointer
                  ${exiting ? 'animate-level-up-exit' : ''}`}
      onClick={dismiss}
    >
      {stars.map((s, i) => (
        <div
          key={i}
          className="animate-star fixed pointer-events-none text-center leading-none"
          style={{
            left: `${s.x}%`,
            top: `${s.sy}%`,
            fontSize: s.size,
            '--sx': '0px',
            '--sy': '0px',
            '--ex': `${randomBetween(-40, 40)}px`,
            '--ey': `${-(s.sy - s.ey) * 4}px`,
            '--star-dur': `${s.dur}s`,
            animationDelay: `${s.delay}s`,
          }}
        >
          {s.emoji}
        </div>
      ))}

      <div className="animate-level-up-enter text-center px-10 py-8 rounded-3xl
                      bg-gradient-to-b from-amber-500/20 to-yellow-600/10
                      border-2 border-amber-400/50 shadow-2xl shadow-amber-500/30">
        <div className="text-5xl mb-2">🏆</div>
        <div className="text-4xl font-black text-amber-400 mb-1 tracking-wide">LEVEL UP!</div>
        <div className="text-gray-300 text-lg mb-4">
          <span className="text-gray-400 line-through mr-2">Lv {oldLevel}</span>
          <span className="text-amber-300 text-2xl font-bold">→ Lv {newLevel}</span>
        </div>
        <div className="text-xs text-gray-500 mt-2">Tap to continue</div>
      </div>
    </div>
  );
}

/* ── BadgeEarnedCard ─────────────────────────────────────────────────────── */

function BadgeEarnedCard({ badge, remaining, onDone }) {
  const [exiting, setExiting] = useState(false);

  const dismiss = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    setTimeout(onDone, 400);
  }, [exiting, onDone]);

  return (
    <div
      className="fixed inset-0 z-[205] flex items-center justify-center bg-black/60 backdrop-blur-sm cursor-pointer pointer-events-auto"
      onClick={dismiss}
    >
      <div
        className={`relative ${exiting ? 'animate-badge-exit' : 'animate-badge-enter'}`}
        style={{ width: 'min(320px, 90vw)' }}
      >
        <div className="relative overflow-hidden rounded-2xl border-2 border-amber-400/60
                        bg-gray-900 shadow-2xl shadow-amber-500/20 p-5 text-center">
          <div className="animate-shimmer absolute inset-0 rounded-2xl pointer-events-none" />

          <div className="text-xs font-bold text-amber-400 uppercase tracking-widest mb-2">
            🎖️ Badge Earned!
          </div>
          <div className="text-6xl mb-3">{badge.icon}</div>
          <div className="text-xl font-bold text-white mb-1">{badge.name}</div>
          <div className="text-sm text-gray-400">{badge.description}</div>
          <div className="text-xs text-gray-600 mt-3">
            {remaining > 1 ? `Tap to continue (${remaining - 1} more)` : 'Tap to dismiss'}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── PowerUpEarnedCard ───────────────────────────────────────────────────── */

function PowerUpEarnedCard({ powerup, remaining, onDone }) {
  const [exiting, setExiting] = useState(false);

  const dismiss = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    setTimeout(onDone, 400);
  }, [exiting, onDone]);

  return (
    <div
      className="fixed inset-0 z-[205] flex items-center justify-center bg-black/60 backdrop-blur-sm cursor-pointer pointer-events-auto"
      onClick={dismiss}
    >
      <div
        className={`relative ${exiting ? 'animate-powerup-exit' : 'animate-powerup-enter'}`}
        style={{ width: 'min(340px, 90vw)' }}
      >
        <div className="animate-golden-sparkle relative overflow-hidden rounded-2xl bg-gray-900 shadow-2xl p-5 text-center">
          <div className="text-xs font-bold text-purple-300 uppercase tracking-widest mb-2">
            ⚡ Power-up Unlocked!
          </div>
          <div className="text-6xl mb-3">{powerup.icon}</div>
          <div className="text-xl font-bold text-white mb-1">{powerup.name}</div>
          <div className="text-sm text-gray-300 mb-2">{powerup.description}</div>
          <div className="text-xs text-gray-500 mt-1">
            Valid for {powerup.uses_remaining} use{powerup.uses_remaining !== 1 ? 's' : ''} · Expires in 7 days
          </div>
          <div className="text-xs text-gray-600 mt-3">
            {remaining > 1 ? `Tap to continue (${remaining - 1} more)` : 'Tap to dismiss'}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── MonthEndOverlay ─────────────────────────────────────────────────────── */

const MEDAL = ['🥇', '🥈', '🥉'];

function MonthEndOverlay({ monthName, entries, onDone }) {
  const [exiting, setExiting] = useState(false);

  const stars = useRef(
    Array.from({ length: STAR_COUNT }, () => ({
      x: randomBetween(10, 90),
      sy: randomBetween(60, 90),
      ey: randomBetween(-10, 30),
      dur: randomBetween(1.0, 2.0),
      delay: randomBetween(0, 0.8),
      size: randomBetween(14, 26),
      emoji: ['🏆', '⭐', '✨', '🌟'][Math.floor(Math.random() * 4)],
    }))
  ).current;

  const dismiss = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    setTimeout(onDone, 400);
  }, [exiting, onDone]);

  const top3 = entries.slice(0, 3);
  // Podium order: 2nd, 1st, 3rd
  const podiumOrder = [1, 0, 2];
  const podiumHeight = (rank) => rank === 1 ? 'h-24' : rank === 2 ? 'h-16' : 'h-10';

  return (
    <div
      className={`fixed inset-0 z-[210] flex flex-col items-center justify-center
                  bg-black/85 backdrop-blur-sm cursor-pointer overflow-y-auto py-6
                  ${exiting ? 'animate-level-up-exit' : ''}`}
      onClick={dismiss}
    >
      {stars.map((s, i) => (
        <div
          key={i}
          className="animate-star fixed pointer-events-none text-center leading-none"
          style={{
            left: `${s.x}%`,
            top: `${s.sy}%`,
            fontSize: s.size,
            '--sx': '0px',
            '--sy': '0px',
            '--ex': `${randomBetween(-40, 40)}px`,
            '--ey': `${-(s.sy - s.ey) * 4}px`,
            '--star-dur': `${s.dur}s`,
            animationDelay: `${s.delay}s`,
          }}
        >
          {s.emoji}
        </div>
      ))}

      <div
        className="animate-level-up-enter text-center px-8 py-7 rounded-3xl mx-4 w-full max-w-sm
                    bg-gradient-to-b from-amber-500/20 to-yellow-600/10
                    border-2 border-amber-400/50 shadow-2xl shadow-amber-500/30"
        onClick={e => e.stopPropagation()}
      >
        <div className="text-4xl mb-1">🏆</div>
        <div className="text-2xl font-black text-amber-400 tracking-wide">Month End!</div>
        <div className="text-gray-300 text-base mb-4">{monthName} — Final Results</div>

        {/* Podium */}
        {top3.length > 0 && (
          <div className="flex justify-center items-end gap-3 mb-5">
            {podiumOrder.map(idx => {
              const entry = top3[idx];
              if (!entry) return <div key={idx} className="w-20" />;
              return (
                <div key={entry.entity_id} className="flex flex-col items-center">
                  <div className="text-2xl mb-0.5">{MEDAL[idx] || ''}</div>
                  <div className="w-9 h-9 rounded-full bg-gray-700 flex items-center justify-center overflow-hidden mb-0.5">
                    {entry.avatar_url
                      ? <img src={entry.avatar_url} className="w-full h-full object-cover" alt="" />
                      : <span className="text-base">👤</span>}
                  </div>
                  <div className="text-xs font-medium truncate max-w-[72px] text-center">{entry.name}</div>
                  <div className={`${podiumHeight(entry.rank)} w-16 bg-gradient-to-t from-amber-700 to-amber-500 rounded-t-lg mt-1 flex items-end justify-center pb-1`}>
                    <span className="text-xs font-bold">{entry.xp_month} XP</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Full ranked list */}
        <div className="space-y-1.5 text-left">
          {entries.map(entry => (
            <div key={entry.entity_id} className="flex items-center gap-3 bg-gray-800/60 rounded-lg px-3 py-2">
              <span className="text-sm font-bold text-gray-400 w-6 text-center">
                {MEDAL[entry.rank - 1] || `#${entry.rank}`}
              </span>
              <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center overflow-hidden shrink-0">
                {entry.avatar_url
                  ? <img src={entry.avatar_url} className="w-full h-full object-cover" alt="" />
                  : <span className="text-sm">👤</span>}
              </div>
              <div className="flex-1 text-sm truncate">{entry.name}</div>
              <div className="text-amber-400 text-sm font-bold">{entry.xp_month} XP</div>
            </div>
          ))}
        </div>

        <div className="text-xs text-gray-500 mt-4">Tap to continue</div>
      </div>
    </div>
  );
}

/* ── Provider ────────────────────────────────────────────────────────────── */

export function GameEffectsProvider({ children }) {
  const [floatingXPs, setFloatingXPs] = useState([]);
  const [confettiBursts, setConfettiBursts] = useState([]);
  const [xpSparkle, setXpSparkle] = useState(null);
  // Unified modal queue: items are { type: 'levelup', oldLevel, newLevel } | { type: 'badge', ...badge }
  const [modalQueue, setModalQueue] = useState([]);

  const removeFloating = useCallback((id) => {
    setFloatingXPs(prev => prev.filter(f => f.id !== id));
  }, []);

  const removeConfetti = useCallback((id) => {
    setConfettiBursts(prev => prev.filter(c => c.id !== id));
  }, []);

  const removeXpSparkle = useCallback(() => setXpSparkle(null), []);

  const dismissModal = useCallback(() => {
    setModalQueue(prev => {
      const current = prev[0];
      if (current?.type === 'monthend') current.onSeen?.();
      return prev.slice(1);
    });
  }, []);

  const triggerEffects = useCallback((result, buttonEl, xpBarEl, oldXPProgress, newXPProgress) => {
    const { xp_awarded, leveled_up, old_level, new_level, new_badges, powerup_earned } = result;

    // Floating XP number
    if (buttonEl && xp_awarded > 0) {
      const rect = buttonEl.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top;
      setFloatingXPs(prev => [...prev, { id: uid(), xp: xp_awarded, x, y }]);
      setConfettiBursts(prev => [...prev, { id: uid(), x, y: rect.top + rect.height / 2 }]);
    }

    // XP bar sparkle
    if (xpBarEl) {
      setXpSparkle({ barEl: xpBarEl, fromProgress: oldXPProgress, toProgress: leveled_up ? 100 : newXPProgress });
    }

    // Build modal queue entries: level-up first, then badges, then power-up
    const entries = [];
    if (leveled_up) {
      entries.push({ type: 'levelup', oldLevel: old_level, newLevel: new_level });
    }
    if (new_badges?.length > 0) {
      new_badges.forEach(b => entries.push({ type: 'badge', ...b }));
    }
    if (powerup_earned) {
      entries.push({ type: 'powerup', ...powerup_earned });
    }
    if (entries.length > 0) {
      // Delay so XP sparkle plays first
      setTimeout(() => {
        setModalQueue(prev => [...prev, ...entries]);
      }, leveled_up ? 700 : 400);
    }
  }, []);

  const triggerMonthEnd = useCallback((data) => {
    setModalQueue(prev => [...prev, { type: 'monthend', ...data }]);
  }, []);

  const ctx = { triggerEffects, triggerMonthEnd };

  const currentModal = modalQueue[0] ?? null;

  return (
    <GameEffectsContext.Provider value={ctx}>
      {children}

      {floatingXPs.map(f => (
        <FloatingXP key={f.id} xp={f.xp} x={f.x} y={f.y} onDone={() => removeFloating(f.id)} />
      ))}

      {confettiBursts.map(c => (
        <ConfettiBurst key={c.id} x={c.x} y={c.y} onDone={() => removeConfetti(c.id)} />
      ))}

      {xpSparkle && (
        <XPBarSparkle
          key={xpSparkle.barEl?.dataset?.sparkleKey || 'sparkle'}
          barEl={xpSparkle.barEl}
          fromProgress={xpSparkle.fromProgress}
          toProgress={xpSparkle.toProgress}
          onDone={removeXpSparkle}
        />
      )}

      {currentModal?.type === 'levelup' && (
        <LevelUpOverlay
          key={`lu-${currentModal.newLevel}`}
          oldLevel={currentModal.oldLevel}
          newLevel={currentModal.newLevel}
          onDone={dismissModal}
        />
      )}

      {currentModal?.type === 'badge' && (
        <BadgeEarnedCard
          key={`badge-${currentModal.id}-${modalQueue.length}`}
          badge={currentModal}
          remaining={modalQueue.length}
          onDone={dismissModal}
        />
      )}

      {currentModal?.type === 'powerup' && (
        <PowerUpEarnedCard
          key={`powerup-${currentModal.id}`}
          powerup={currentModal}
          remaining={modalQueue.length}
          onDone={dismissModal}
        />
      )}

      {currentModal?.type === 'monthend' && (
        <MonthEndOverlay
          key={`monthend-${currentModal.month}`}
          monthName={currentModal.month_name}
          entries={currentModal.entries}
          onDone={dismissModal}
        />
      )}
    </GameEffectsContext.Provider>
  );
}
