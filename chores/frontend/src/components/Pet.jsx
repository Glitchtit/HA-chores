import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as api from '../api';

import houseBg        from '../assets/pets/house/background.png';
import orangeIdle     from '../assets/pets/orange_black/idle.png';
import orangeHappy    from '../assets/pets/orange_black/happy.png';
import orangeSad      from '../assets/pets/orange_black/sad.png';
import blueIdle       from '../assets/pets/blue_black/idle.png';
import blueHappy      from '../assets/pets/blue_black/happy.png';
import blueSad        from '../assets/pets/blue_black/sad.png';
import messDishes      from '../assets/pets/mess/dishes.png';
import messLaundry     from '../assets/pets/mess/laundry.png';
import messCleaning    from '../assets/pets/mess/cleaning.png';
import messTrash       from '../assets/pets/mess/trash.png';
import messCooking     from '../assets/pets/mess/cooking.png';
import messOther       from '../assets/pets/mess/other.png';

const CATEGORY_LABEL = {
  dishes: 'Dishes',
  laundry: 'Laundry',
  cleaning: 'Cleaning',
  trash: 'Trash',
  cooking: 'Cooking',
  other: 'Other',
};

const MESS_IMG = {
  dishes: messDishes,
  laundry: messLaundry,
  cleaning: messCleaning,
  trash: messTrash,
  cooking: messCooking,
  other: messOther,
};

const DESIGNS = ['orange_black', 'blue_black'];
const DESIGN_LABEL = {
  orange_black: 'Orange',
  blue_black: 'Blue',
};

const SPRITES = {
  orange_black: { idle: orangeIdle, happy: orangeHappy, sad: orangeSad },
  blue_black:   { idle: blueIdle,   happy: blueHappy,   sad: blueSad   },
};

const STATE_ANIM = {
  idle:  'animate-[pet-breathe_2.4s_ease-in-out_infinite]',
  happy: 'animate-[pet-bounce_0.6s_ease-in-out_infinite]',
  sad:   'animate-[pet-droop_2.6s_ease-in-out_infinite]',
};

const MOOD_TONE = {
  ecstatic: 'text-emerald-300',
  happy:    'text-emerald-400',
  meh:      'text-amber-400',
  sad:      'text-rose-400',
};

// Spots in the background image where pets can sit (% from top-left).
// Derived from the pixel-art cabin layout: floor areas, furniture surfaces, loft.
const PET_SPOTS = [
  { left: 10, top: 78 },   // on the rug
  { left: 28, top: 75 },   // in front of bookshelf
  { left: 42, top: 74 },   // center floor (sunlight patch)
  { left: 56, top: 78 },   // right of center floor
  { left: 72, top: 72 },   // by the fireplace
  { left: 85, top: 80 },   // on the pet bed
  { left: 46, top: 64 },   // at ladder base
  { left: 18, top: 52 },   // on the windowsill
  { left: 62, top: 24 },   // up in the loft
  { left: 78, top: 86 },   // by the water bowl
  { left: 6,  top: 86 },   // on the floor pillow
];

// Spots where mess piles appear — edges, corners, surfaces that don't
// overlap with any pet spot.
const MESS_SPOTS = [
  { left: 3,  top: 82 },   // left wall floor
  { left: 15, top: 60 },   // below the window
  { left: 30, top: 42 },   // top of bookshelf
  { left: 48, top: 20 },   // upper ladder / loft rail
  { left: 86, top: 44 },   // right wall near lantern
  { left: 92, top: 76 },   // fireplace hearth edge
  { left: 92, top: 90 },   // bottom-right corner
  { left: 4,  top: 92 },   // bottom-left corner
  { left: 55, top: 10 },   // near string lights
  { left: 80, top: 38 },   // above fireplace mantle
];

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function Bar({ value, label, color }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        <span>{value}/100</span>
      </div>
      <div className="bg-gray-700 h-3 rounded-full overflow-hidden">
        <div className={`${color} h-full transition-all duration-500`}
             style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function SpriteFrame({ design, state, className = '', style = {} }) {
  const src = SPRITES[design]?.[state] || SPRITES.orange_black.idle;
  const anim = STATE_ANIM[state] || STATE_ANIM.idle;
  return (
    <img
      key={`${design}-${state}`}
      src={src}
      alt=""
      className={`pixelated ${anim} ${className}`}
      style={{ objectFit: 'contain', ...style }}
    />
  );
}

function StaticPreview({ design, size = 48 }) {
  const src = SPRITES[design]?.idle || SPRITES.orange_black.idle;
  return (
    <img
      src={src}
      alt=""
      width={size}
      height={size}
      className="pixelated"
      style={{ width: `${size}px`, height: `${size}px`, objectFit: 'contain' }}
    />
  );
}

function MessPile({ category, count, spot }) {
  if (count <= 0) return null;
  const src = MESS_IMG[category] || MESS_IMG.other;
  const size = Math.min(count, 5);
  return (
    <div
      className="absolute flex gap-0.5 items-end pointer-events-none"
      style={{
        left: `${spot.left}%`,
        top: `${spot.top}%`,
        transform: 'translate(-50%, -100%)',
      }}
      title={`${count} overdue ${CATEGORY_LABEL[category].toLowerCase()}`}
    >
      {Array.from({ length: size }).map((_, i) => (
        <img
          key={i}
          src={src}
          alt=""
          className="w-6 h-6 sm:w-8 sm:h-8 pixelated animate-[mess-jitter_2.4s_ease-in-out_infinite]"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
      {count > 5 && (
        <span className="text-[9px] sm:text-xs text-gray-400 self-end ml-0.5">+{count - 5}</span>
      )}
    </div>
  );
}

function stateFor(pet, celebrating) {
  if (celebrating) return 'happy';
  if (pet.mood === 'sad') return 'sad';
  return 'idle';
}

function HouseScene({ household, petSpots, messSpots, personsById, activePerson, celebratingId, onPetClick }) {
  if (!household) return <div className="text-gray-400 text-sm">Loading…</div>;

  const { pets, shared } = household;
  const activeMessCategories = Object.entries(shared.mess_counts).filter(([, v]) => v > 0);

  return (
    <div className="bg-gray-800 rounded-lg p-2 sm:p-4">
      <div
        className="relative aspect-[4/3] rounded-md overflow-hidden bg-gray-900"
        style={{
          backgroundImage: `url(${houseBg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        {/* Mess piles at randomized positions */}
        {activeMessCategories.map(([cat, count], i) => (
          <MessPile
            key={cat}
            category={cat}
            count={count}
            spot={messSpots[i % messSpots.length]}
          />
        ))}

        {/* All pets at randomized positions */}
        {pets.map((pet, i) => {
          const spot = petSpots[i % petSpots.length];
          const design = DESIGNS.includes(pet.pet_design) ? pet.pet_design : 'orange_black';
          const isActive = pet.person_id === activePerson;
          const state = stateFor(pet, pet.person_id === celebratingId);
          const personName = personsById.get(pet.person_id)?.name || pet.person_id;
          const flip = i % 2 === 1;

          return (
            <div
              key={pet.person_id}
              className="absolute group"
              style={{
                left: `${spot.left}%`,
                top: `${spot.top}%`,
                transform: 'translate(-50%, -100%)',
              }}
            >
              <button
                type="button"
                onClick={() => onPetClick?.(pet.person_id)}
                className={`block p-0.5 rounded transition-all hover:bg-white/10
                  ${isActive ? 'ring-2 ring-amber-400/60 rounded-lg' : ''}`}
                title={personName}
              >
                <SpriteFrame
                  design={design}
                  state={state}
                  className="w-[clamp(48px,18vw,120px)]"
                  style={flip ? { transform: 'scaleX(-1)' } : undefined}
                />
              </button>
              {/* Name label: visible on hover (desktop) or always on mobile */}
              <div className="flex justify-center mt-0.5 pointer-events-none
                              opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                <span className="text-[9px] sm:text-[10px] bg-gray-900/80 px-1.5 py-0.5 rounded text-gray-200 whitespace-nowrap">
                  {personName}
                </span>
              </div>
            </div>
          );
        })}

        {/* Mood badge for active person */}
        {(() => {
          const myPet = pets.find(p => p.person_id === activePerson);
          if (!myPet) return null;
          return (
            <div className="absolute top-2 left-2 text-xs uppercase tracking-widest bg-gray-900/70 px-2 py-0.5 rounded">
              <span className={MOOD_TONE[myPet.mood] || 'text-gray-300'}>{myPet.mood}</span>
            </div>
          );
        })()}
      </div>
    </div>
  );
}

function DesignPicker({ current, onPick, onClose }) {
  return (
    <div className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4"
         onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        className="bg-gray-800 rounded-lg p-5 w-full max-w-md space-y-4"
      >
        <h3 className="text-lg font-semibold">Pick your axolotl</h3>
        <div className="grid grid-cols-2 gap-3">
          {DESIGNS.map(d => (
            <button
              key={d}
              onClick={() => onPick(d)}
              className={`aspect-square rounded border-2 transition-all flex flex-col items-center justify-center gap-2 py-3
                          ${d === current
                            ? 'border-amber-400 bg-gray-700'
                            : 'border-transparent hover:border-gray-600 hover:bg-gray-700'}`}
            >
              <StaticPreview design={d} size={96} />
              <span className="text-sm text-gray-200">{DESIGN_LABEL[d]}</span>
            </button>
          ))}
        </div>
        <button
          onClick={onClose}
          className="w-full bg-gray-700 hover:bg-gray-600 rounded py-2 text-sm"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function HouseholdShared({ shared }) {
  const nonZero = Object.entries(shared.mess_counts).filter(([, v]) => v > 0);
  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">🏡 Common area</h3>
        <span className="text-xs text-gray-500">Unclaimed + all overdue</span>
      </div>
      {nonZero.length === 0 ? (
        <p className="text-sm text-gray-500">All clean. Nice.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {nonZero.map(([cat, v]) => (
            <span key={cat} className="bg-gray-700 rounded-full px-3 py-1 text-xs flex items-center gap-1">
              <img src={MESS_IMG[cat] || MESS_IMG.other} alt="" className="w-4 h-4 pixelated" />
              <span className="text-gray-300">{CATEGORY_LABEL[cat]}</span>
              <span className="text-amber-400 font-bold">×{v}</span>
            </span>
          ))}
        </div>
      )}
      <Bar value={shared.cleanliness} label="🛁 Shared cleanliness" color="bg-sky-500" />
    </div>
  );
}

export default function Pet({ activePerson, persons = [], isHouseholdMode, setActivePerson }) {
  const [household, setHousehold] = useState(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [celebratingId, setCelebratingId] = useState(null);
  const celebrateTimer = useRef(null);
  const personsById = useMemo(
    () => new Map(persons.map(p => [p.entity_id, p])),
    [persons],
  );

  // Randomize positions on mount — re-shuffled each time user navigates to pet tab
  const [petSpots] = useState(() => shuffle(PET_SPOTS));
  const [messSpots] = useState(() => shuffle(MESS_SPOTS));

  const load = useCallback(async () => {
    try {
      const data = await api.getHouseholdPets();
      setHousehold(data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let cancelled = false;
    const id = setInterval(() => {
      if (!cancelled && document.visibilityState === 'visible') load();
    }, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, [load]);

  useEffect(() => {
    const onCompleted = (e) => {
      const { person_id } = e.detail || {};
      if (person_id) {
        setCelebratingId(person_id);
        if (celebrateTimer.current) clearTimeout(celebrateTimer.current);
        celebrateTimer.current = setTimeout(() => setCelebratingId(null), 1300);
      }
      setTimeout(load, 800);
    };
    window.addEventListener('chore-completed', onCompleted);
    return () => window.removeEventListener('chore-completed', onCompleted);
  }, [load]);

  const handlePickDesign = async (design) => {
    if (!activePerson) return;
    setPickerOpen(false);
    setHousehold(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        pets: prev.pets.map(p =>
          p.person_id === activePerson ? { ...p, pet_design: design } : p
        ),
      };
    });
    try {
      await api.setPetDesign(activePerson, design);
      load();
    } catch { /* rollback handled by next poll */ }
  };

  const handlePetClick = (personId) => {
    if (personId === activePerson) {
      setPickerOpen(true);
    } else if (setActivePerson) {
      setActivePerson(personId);
    }
  };

  const myPet = household?.pets?.find(p => p.person_id === activePerson);

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <HouseScene
        household={household}
        petSpots={petSpots}
        messSpots={messSpots}
        personsById={personsById}
        activePerson={activePerson}
        celebratingId={celebratingId}
        onPetClick={handlePetClick}
      />

      {/* Personal stats for the active person */}
      {myPet && (
        <div className="bg-gray-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm text-gray-300">
            <StaticPreview design={myPet.pet_design} size={28} />
            <span className="font-semibold">{personsById.get(activePerson)?.name || 'Your pet'}</span>
            <span className={`ml-auto text-xs uppercase ${MOOD_TONE[myPet.mood] || 'text-gray-400'}`}>
              {myPet.mood}
            </span>
          </div>
          <Bar value={myPet.happiness}   label="❤️ Happiness"   color="bg-pink-500" />
          <Bar value={myPet.cleanliness} label="🛁 Cleanliness" color="bg-sky-500" />
        </div>
      )}

      {/* Shared household mess summary */}
      {household && <HouseholdShared shared={household.shared} />}

      {pickerOpen && myPet && (
        <DesignPicker
          current={myPet.pet_design}
          onPick={handlePickDesign}
          onClose={() => setPickerOpen(false)}
        />
      )}
    </div>
  );
}
