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
      x: randomBetween(10, 90),   // % of viewport width
      sy: randomBetween(60, 90),  // start y%
      ey: randomBetween(-10, 30), // end y%
      dur: randomBetween(1.0, 2.0),
      delay: randomBetween(0, 0.8),
      size: randomBetween(14, 26),
      emoji: ['⭐', '✨', '🌟', '💫'][Math.floor(Math.random() * 4)],
    }))
  ).current;

  useEffect(() => {
    const exitT = setTimeout(() => setExiting(true), 2800);
    const doneT = setTimeout(onDone, 3300);
    return () => { clearTimeout(exitT); clearTimeout(doneT); };
  }, [onDone]);

  return (
    <div
      className={`fixed inset-0 z-[210] flex flex-col items-center justify-center
                  bg-black/80 backdrop-blur-sm transition-opacity
                  ${exiting ? 'animate-level-up-exit' : ''}`}
      onClick={() => { setExiting(true); setTimeout(onDone, 400); }}
    >
      {/* Star particles */}
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

      {/* Main card */}
      <div className={`animate-level-up-enter text-center px-10 py-8 rounded-3xl
                       bg-gradient-to-b from-amber-500/20 to-yellow-600/10
                       border-2 border-amber-400/50 shadow-2xl shadow-amber-500/30`}>
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

function BadgeEarnedCard({ badge, onDone }) {
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const exitT = setTimeout(() => setExiting(true), 3600);
    const doneT = setTimeout(onDone, 4000);
    return () => { clearTimeout(exitT); clearTimeout(doneT); };
  }, [onDone]);

  return (
    <div
      className={`fixed bottom-24 left-1/2 z-[205] pointer-events-auto cursor-pointer
                  ${exiting ? 'animate-badge-exit' : 'animate-badge-enter'}`}
      style={{ width: 'min(320px, 90vw)' }}
      onClick={() => { setExiting(true); setTimeout(onDone, 400); }}
    >
      <div className="relative overflow-hidden rounded-2xl border-2 border-amber-400/60
                      bg-gray-900 shadow-2xl shadow-amber-500/20 p-5 text-center">
        {/* Shimmer overlay */}
        <div className="animate-shimmer absolute inset-0 rounded-2xl pointer-events-none" />

        <div className="text-xs font-bold text-amber-400 uppercase tracking-widest mb-2">
          🎖️ Badge Earned!
        </div>
        <div className="text-6xl mb-3">{badge.icon}</div>
        <div className="text-xl font-bold text-white mb-1">{badge.name}</div>
        <div className="text-sm text-gray-400">{badge.description}</div>
        <div className="text-xs text-gray-600 mt-3">Tap to dismiss</div>
      </div>
    </div>
  );
}

/* ── Provider ────────────────────────────────────────────────────────────── */

export function GameEffectsProvider({ children }) {
  const [floatingXPs, setFloatingXPs] = useState([]);
  const [confettiBursts, setConfettiBursts] = useState([]);
  const [xpSparkle, setXpSparkle] = useState(null);
  const [levelUp, setLevelUp] = useState(null);
  const [badgeQueue, setBadgeQueue] = useState([]);

  const removeFloating = useCallback((id) => {
    setFloatingXPs(prev => prev.filter(f => f.id !== id));
  }, []);

  const removeConfetti = useCallback((id) => {
    setConfettiBursts(prev => prev.filter(c => c.id !== id));
  }, []);

  const removeXpSparkle = useCallback(() => setXpSparkle(null), []);

  const removeLevelUp = useCallback(() => setLevelUp(null), []);

  const removeTopBadge = useCallback(() => {
    setBadgeQueue(prev => prev.slice(1));
  }, []);

  /**
   * Trigger all effects from a complete response.
   * @param {object} result  — the CompleteResult from the API
   * @param {Element} buttonEl  — the Done button DOM element (for confetti + XP position)
   * @param {Element} xpBarEl  — the XP progress bar container element
   * @param {number} oldXPProgress  — XP bar fill % before completing (0–100)
   * @param {number} newXPProgress  — XP bar fill % after completing (0–100)
   */
  const triggerEffects = useCallback((result, buttonEl, xpBarEl, oldXPProgress, newXPProgress) => {
    const { xp_awarded, leveled_up, old_level, new_level, new_badges } = result;

    // Floating XP number
    if (buttonEl && xp_awarded > 0) {
      const rect = buttonEl.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top;
      setFloatingXPs(prev => [...prev, { id: uid(), xp: xp_awarded, x, y }]);

      // Confetti from button center
      setConfettiBursts(prev => [...prev, { id: uid(), x, y: rect.top + rect.height / 2 }]);
    }

    // XP bar sparkle
    if (xpBarEl && !leveled_up) {
      setXpSparkle({ barEl: xpBarEl, fromProgress: oldXPProgress, toProgress: newXPProgress });
    } else if (xpBarEl && leveled_up) {
      // Fill to 100 then show level-up
      setXpSparkle({ barEl: xpBarEl, fromProgress: oldXPProgress, toProgress: 100 });
    }

    // Level up overlay (slight delay so the bar completes first)
    if (leveled_up) {
      setTimeout(() => {
        setLevelUp({ oldLevel: old_level, newLevel: new_level });
      }, 700);
    }

    // Badge queue
    if (new_badges?.length > 0) {
      setBadgeQueue(prev => [...prev, ...new_badges]);
    }
  }, []);

  const ctx = { triggerEffects };

  return (
    <GameEffectsContext.Provider value={ctx}>
      {children}

      {/* Floating XP labels */}
      {floatingXPs.map(f => (
        <FloatingXP key={f.id} xp={f.xp} x={f.x} y={f.y} onDone={() => removeFloating(f.id)} />
      ))}

      {/* Confetti bursts */}
      {confettiBursts.map(c => (
        <ConfettiBurst key={c.id} x={c.x} y={c.y} onDone={() => removeConfetti(c.id)} />
      ))}

      {/* XP bar sparkle */}
      {xpSparkle && (
        <XPBarSparkle
          key={xpSparkle.barEl?.dataset?.sparkleKey || 'sparkle'}
          barEl={xpSparkle.barEl}
          fromProgress={xpSparkle.fromProgress}
          toProgress={xpSparkle.toProgress}
          onDone={removeXpSparkle}
        />
      )}

      {/* Level up overlay */}
      {levelUp && (
        <LevelUpOverlay
          oldLevel={levelUp.oldLevel}
          newLevel={levelUp.newLevel}
          onDone={removeLevelUp}
        />
      )}

      {/* Badge earned (show one at a time) */}
      {badgeQueue.length > 0 && (
        <BadgeEarnedCard
          key={badgeQueue[0].id}
          badge={badgeQueue[0]}
          onDone={removeTopBadge}
        />
      )}
    </GameEffectsContext.Provider>
  );
}
