import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '../api';

const CATEGORY_EMOJI = {
  dishes: '🍽',
  laundry: '👕',
  cleaning: '🧹',
  trash: '🗑',
  cooking: '🍳',
  other: '📦',
};

const CATEGORY_LABEL = {
  dishes: 'Dishes',
  laundry: 'Laundry',
  cleaning: 'Cleaning',
  trash: 'Trash',
  cooking: 'Cooking',
  other: 'Other',
};

const PET_EMOJI_CHOICES = ['🐶','🐱','🐰','🐻','🐼','🐸','🦊','🐵','🐷','🐔','🐧','🦄'];

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

function MessPile({ category, count, position }) {
  if (count <= 0) return null;
  const emoji = CATEGORY_EMOJI[category] || '❓';
  const size = Math.min(count, 5);
  return (
    <div
      className="absolute flex gap-0.5"
      style={position}
      title={`${count} overdue ${CATEGORY_LABEL[category].toLowerCase()}`}
    >
      {Array.from({ length: size }).map((_, i) => (
        <span
          key={i}
          className="text-2xl leading-none animate-[mess-jitter_2.4s_ease-in-out_infinite]"
          style={{ animationDelay: `${i * 0.15}s` }}
        >
          {emoji}
        </span>
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

function PetScene({ pet, onPickEmoji, celebrating }) {
  const moodAnim = pet.mood === 'sad'
    ? 'animate-[sad-droop_2.8s_ease-in-out_infinite]'
    : 'animate-[idle-breath_3s_ease-in-out_infinite]';
  const celebAnim = celebrating
    ? 'animate-[celebration-bounce_1.2s_ease-out]'
    : moodAnim;

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-4">
      <div className="relative aspect-[4/3] bg-gradient-to-b from-gray-700 to-gray-800 rounded-md overflow-hidden">
        {/* Mess piles in corners */}
        {Object.entries(pet.mess_counts).map(([cat, count]) => (
          <MessPile
            key={cat}
            category={cat}
            count={count}
            position={CORNER_POSITIONS[cat] || CORNER_POSITIONS.other}
          />
        ))}

        {/* Pet emoji, centered */}
        <div className="absolute inset-0 flex items-center justify-center">
          <button
            type="button"
            onClick={onPickEmoji}
            className={`text-[5rem] leading-none ${celebAnim}`}
            title="Tap to change your pet"
          >
            {pet.pet_emoji}
          </button>
        </div>

        {/* Mood tag, top-left */}
        <div className="absolute top-2 left-2 text-xs uppercase tracking-widest bg-gray-900/70 px-2 py-0.5 rounded">
          <span className={MOOD_TONE[pet.mood] || 'text-gray-300'}>{pet.mood}</span>
        </div>
      </div>

      <Bar value={pet.happiness} label="❤️ Happiness"  color="bg-pink-500" />
      <Bar value={pet.cleanliness} label="🛁 Cleanliness" color="bg-sky-500" />
    </div>
  );
}

function EmojiPicker({ current, onPick, onClose }) {
  return (
    <div className="fixed inset-0 z-40 bg-black/60 flex items-center justify-center p-4"
         onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        className="bg-gray-800 rounded-lg p-5 w-full max-w-sm space-y-4"
      >
        <h3 className="text-lg font-semibold">Pick your pet</h3>
        <div className="grid grid-cols-4 gap-2">
          {PET_EMOJI_CHOICES.map(e => (
            <button
              key={e}
              onClick={() => onPick(e)}
              className={`aspect-square text-3xl rounded border-2 transition-all
                          ${e === current
                            ? 'border-amber-400 bg-gray-700'
                            : 'border-transparent hover:border-gray-600 hover:bg-gray-700'}`}
            >
              {e}
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
              <span className="text-base">{CATEGORY_EMOJI[cat]}</span>
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
              <div className="flex items-center justify-center text-5xl my-2 animate-[idle-breath_3s_ease-in-out_infinite]">
                {pet.pet_emoji}
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
  const personsById = new Map(persons.map(p => [p.entity_id, p]));

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

  // Poll every 10s while the tab is visible.
  useEffect(() => {
    let cancelled = false;
    const id = setInterval(() => {
      if (!cancelled && document.visibilityState === 'visible') load();
    }, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, [load]);

  // Optimistic happiness update when a completion event fires.
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
      // refresh after the server has updated
      setTimeout(load, 800);
    };
    window.addEventListener('chore-completed', onCompleted);
    return () => window.removeEventListener('chore-completed', onCompleted);
  }, [activePerson, isHousehold, load]);

  const handlePickEmoji = async (emoji) => {
    if (!activePerson) return;
    setPickerOpen(false);
    setPet(prev => prev ? { ...prev, pet_emoji: emoji } : prev);
    try {
      const updated = await api.setPetEmoji(activePerson, emoji);
      setPet(updated);
    } catch { /* rollback handled by next poll */ }
  };

  if (isHousehold) {
    if (!household) return <div className="text-gray-400 text-sm">Loading…</div>;
    return <HouseholdScene data={household} personsById={personsById} onSelectPerson={setActivePerson} />;
  }

  if (!activePerson) {
    return <div className="text-gray-400 text-sm">Pick a profile from the header to meet your pet.</div>;
  }
  if (!pet) return <div className="text-gray-400 text-sm">Loading your pet…</div>;

  return (
    <div className="space-y-4">
      <PetScene
        pet={pet}
        onPickEmoji={() => setPickerOpen(true)}
        celebrating={celebrating}
      />
      {pickerOpen && (
        <EmojiPicker
          current={pet.pet_emoji}
          onPick={handlePickEmoji}
          onClose={() => setPickerOpen(false)}
        />
      )}
    </div>
  );
}
