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

const SPRITE_SIZE = 160;

const MOOD_TONE = {
  ecstatic: 'text-emerald-300',
  happy:    'text-emerald-400',
  meh:      'text-amber-400',
  sad:      'text-rose-400',
};

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

function SpriteFrame({ design, state, size = SPRITE_SIZE }) {
  const src = SPRITES[design]?.[state] || SPRITES.orange_black.idle;
  const anim = STATE_ANIM[state] || STATE_ANIM.idle;
  return (
    <img
      key={`${design}-${state}`}
      src={src}
      alt=""
      width={size}
      height={size}
      className={`pixelated ${anim}`}
      style={{ width: `${size}px`, height: `${size}px`, objectFit: 'contain' }}
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

function MessPile({ category, count, position }) {
  if (count <= 0) return null;
  const src = MESS_IMG[category] || MESS_IMG.other;
  const size = Math.min(count, 5);
  return (
    <div
      className="absolute flex gap-0.5 items-end"
      style={position}
      title={`${count} overdue ${CATEGORY_LABEL[category].toLowerCase()}`}
    >
      {Array.from({ length: size }).map((_, i) => (
        <img
          key={i}
          src={src}
          alt=""
          className="w-8 h-8 pixelated animate-[mess-jitter_2.4s_ease-in-out_infinite]"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
      {count > 5 && (
        <span className="text-xs text-gray-400 self-end ml-1">+{count - 5}</span>
      )}
    </div>
  );
}

const CORNER_POSITIONS = {
  dishes:   { left: '12px', bottom: '12px' },
  laundry:  { right: '12px', bottom: '12px' },
  trash:    { right: '12px', top: '12px' },
  cooking:  { left: '12px', top: '12px' },
  cleaning: { left: '50%', bottom: '12px', transform: 'translateX(-50%)' },
  other:    { left: '50%', top: '12px',    transform: 'translateX(-50%)' },
};

function stateFor(pet, celebrating) {
  if (celebrating) return 'happy';
  if (pet.mood === 'sad') return 'sad';
  return 'idle';
}

function PetScene({ pet, onOpenPicker, celebrating }) {
  const design = DESIGNS.includes(pet.pet_design) ? pet.pet_design : 'orange_black';
  const state = stateFor(pet, celebrating);
  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-4">
      <div
        className="relative aspect-[4/3] rounded-md overflow-hidden bg-gray-900"
        style={{
          backgroundImage: `url(${houseBg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        {Object.entries(pet.mess_counts).map(([cat, count]) => (
          <MessPile
            key={cat}
            category={cat}
            count={count}
            position={CORNER_POSITIONS[cat] || CORNER_POSITIONS.other}
          />
        ))}

        <div className="absolute inset-0 flex items-center justify-center">
          <button
            type="button"
            onClick={onOpenPicker}
            className="p-1 rounded hover:bg-white/10"
            title="Tap to change your axolotl"
          >
            <SpriteFrame design={design} state={state} />
          </button>
        </div>

        <div className="absolute top-2 left-2 text-xs uppercase tracking-widest bg-gray-900/70 px-2 py-0.5 rounded">
          <span className={MOOD_TONE[pet.mood] || 'text-gray-300'}>{pet.mood}</span>
        </div>
      </div>

      <Bar value={pet.happiness} label="❤️ Happiness"  color="bg-pink-500" />
      <Bar value={pet.cleanliness} label="🛁 Cleanliness" color="bg-sky-500" />
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

function HouseholdScene({ data, onSelectPerson, personsById }) {
  return (
    <div className="space-y-4">
      <HouseholdShared shared={data.shared} />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {data.pets.map(pet => {
          const p = personsById.get(pet.person_id);
          const design = DESIGNS.includes(pet.pet_design) ? pet.pet_design : 'orange_black';
          return (
            <button
              key={pet.person_id}
              onClick={() => onSelectPerson?.(pet.person_id)}
              className="bg-gray-800 hover:bg-gray-750 rounded-lg p-3 text-left transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold truncate">{p?.name || pet.person_id}</span>
                <span className={`text-[10px] uppercase ${MOOD_TONE[pet.mood] || 'text-gray-400'}`}>
                  {pet.mood}
                </span>
              </div>
              <div className="flex items-center justify-center my-2">
                <StaticPreview design={design} size={64} />
              </div>
              <div className="space-y-1 text-[10px] text-gray-400">
                <div className="flex justify-between"><span>❤️</span><span>{pet.happiness}</span></div>
                <div className="flex justify-between"><span>🛁</span><span>{pet.cleanliness}</span></div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function Pet({ activePerson, persons = [], isHouseholdMode, setActivePerson }) {
  const isHousehold = isHouseholdMode && !activePerson;
  const [pet, setPet] = useState(null);
  const [household, setHousehold] = useState(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const celebrateTimer = useRef(null);
  const personsById = useMemo(
    () => new Map(persons.map(p => [p.entity_id, p])),
    [persons],
  );

  const load = useCallback(async () => {
    try {
      if (isHousehold) {
        const data = await api.getHouseholdPets();
        setHousehold(data);
      } else if (activePerson) {
        const data = await api.getMyPet();
        setPet(data);
      }
    } catch { /* ignore */ }
  }, [isHousehold, activePerson]);

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
      const { person_id, pet_delta, pet_happiness } = e.detail || {};
      if (!isHousehold && person_id === activePerson) {
        setPet(prev => prev ? {
          ...prev,
          happiness: pet_happiness ?? Math.min(100, prev.happiness + (pet_delta || 0)),
        } : prev);
        setCelebrating(true);
        if (celebrateTimer.current) clearTimeout(celebrateTimer.current);
        celebrateTimer.current = setTimeout(() => setCelebrating(false), 1300);
      }
      setTimeout(load, 800);
    };
    window.addEventListener('chore-completed', onCompleted);
    return () => window.removeEventListener('chore-completed', onCompleted);
  }, [activePerson, isHousehold, load]);

  const handlePickDesign = async (design) => {
    if (!activePerson) return;
    setPickerOpen(false);
    setPet(prev => prev ? { ...prev, pet_design: design } : prev);
    try {
      const updated = await api.setPetDesign(activePerson, design);
      setPet(updated);
    } catch { /* rollback handled by next poll */ }
  };

  if (isHousehold) {
    if (!household) return <div className="text-gray-400 text-sm">Loading…</div>;
    return <HouseholdScene data={household} personsById={personsById} onSelectPerson={setActivePerson} />;
  }

  if (!activePerson) {
    return <div className="text-gray-400 text-sm">Pick a profile from the header to meet your axolotl.</div>;
  }
  if (!pet) return <div className="text-gray-400 text-sm">Loading your axolotl…</div>;

  return (
    <div className="space-y-4">
      <PetScene
        pet={pet}
        onOpenPicker={() => setPickerOpen(true)}
        celebrating={celebrating}
      />
      {pickerOpen && (
        <DesignPicker
          current={pet.pet_design}
          onPick={handlePickDesign}
          onClose={() => setPickerOpen(false)}
        />
      )}
    </div>
  );
}
