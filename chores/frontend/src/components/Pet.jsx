import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as api from '../api';
import PetShop from './PetShop';

import houseBgDay            from '../assets/pets/house/background-day.png';
import houseBgDayRain        from '../assets/pets/house/background-day-rain.png';
import houseBgDayFilthy      from '../assets/pets/house/background-day-filthy.png';
import houseBgDayRainFilthy  from '../assets/pets/house/background-day-rain-filthy.png';
import houseBgNight          from '../assets/pets/house/background-night.png';
import houseBgNightRain      from '../assets/pets/house/background-night-rain.png';
import houseBgNightFilthy    from '../assets/pets/house/background-night-filthy.png';
import houseBgNightRainFilthy from '../assets/pets/house/background-night-rain-filthy.png';
// Seasonal house backgrounds (v0.6.0) — 4 seasons × 8 day/night×rain×filthy variants
import spring_day                   from '../assets/pets/house/seasons/spring/day.png';
import spring_dayRain                from '../assets/pets/house/seasons/spring/day-rain.png';
import spring_dayFilthy              from '../assets/pets/house/seasons/spring/day-filthy.png';
import spring_dayRainFilthy          from '../assets/pets/house/seasons/spring/day-rain-filthy.png';
import spring_night                  from '../assets/pets/house/seasons/spring/night.png';
import spring_nightRain              from '../assets/pets/house/seasons/spring/night-rain.png';
import spring_nightFilthy            from '../assets/pets/house/seasons/spring/night-filthy.png';
import spring_nightRainFilthy        from '../assets/pets/house/seasons/spring/night-rain-filthy.png';
import summer_day                    from '../assets/pets/house/seasons/summer/day.png';
import summer_dayRain                 from '../assets/pets/house/seasons/summer/day-rain.png';
import summer_dayFilthy               from '../assets/pets/house/seasons/summer/day-filthy.png';
import summer_dayRainFilthy           from '../assets/pets/house/seasons/summer/day-rain-filthy.png';
import summer_night                   from '../assets/pets/house/seasons/summer/night.png';
import summer_nightRain               from '../assets/pets/house/seasons/summer/night-rain.png';
import summer_nightFilthy             from '../assets/pets/house/seasons/summer/night-filthy.png';
import summer_nightRainFilthy         from '../assets/pets/house/seasons/summer/night-rain-filthy.png';
import autumn_day                     from '../assets/pets/house/seasons/autumn/day.png';
import autumn_dayRain                  from '../assets/pets/house/seasons/autumn/day-rain.png';
import autumn_dayFilthy                from '../assets/pets/house/seasons/autumn/day-filthy.png';
import autumn_dayRainFilthy            from '../assets/pets/house/seasons/autumn/day-rain-filthy.png';
import autumn_night                    from '../assets/pets/house/seasons/autumn/night.png';
import autumn_nightRain                from '../assets/pets/house/seasons/autumn/night-rain.png';
import autumn_nightFilthy              from '../assets/pets/house/seasons/autumn/night-filthy.png';
import autumn_nightRainFilthy          from '../assets/pets/house/seasons/autumn/night-rain-filthy.png';
import winter_day                      from '../assets/pets/house/seasons/winter/day.png';
import winter_dayRain                   from '../assets/pets/house/seasons/winter/day-rain.png';
import winter_dayFilthy                 from '../assets/pets/house/seasons/winter/day-filthy.png';
import winter_dayRainFilthy             from '../assets/pets/house/seasons/winter/day-rain-filthy.png';
import winter_night                     from '../assets/pets/house/seasons/winter/night.png';
import winter_nightRain                 from '../assets/pets/house/seasons/winter/night-rain.png';
import winter_nightFilthy               from '../assets/pets/house/seasons/winter/night-filthy.png';
import winter_nightRainFilthy           from '../assets/pets/house/seasons/winter/night-rain-filthy.png';
import orangeIdle     from '../assets/pets/orange_black/idle.png';
import orangeHappy    from '../assets/pets/orange_black/happy.png';
import orangeSad      from '../assets/pets/orange_black/sad.png';
import orangePetted   from '../assets/pets/orange_black/petted.png';
import blueIdle       from '../assets/pets/blue_black/idle.png';
import blueHappy      from '../assets/pets/blue_black/happy.png';
import blueSad        from '../assets/pets/blue_black/sad.png';
import bluePetted     from '../assets/pets/blue_black/petted.png';
// Evolution stage sprites (idle/happy/petted per stage, v0.5.2)
import stageOrangeEggIdle      from '../assets/pets/orange_black/stages/egg/idle.png';
import stageOrangeEggHappy     from '../assets/pets/orange_black/stages/egg/happy.png';
import stageOrangeEggPetted    from '../assets/pets/orange_black/stages/egg/petted.png';
import stageOrangeBabyIdle     from '../assets/pets/orange_black/stages/baby/idle.png';
import stageOrangeBabyHappy    from '../assets/pets/orange_black/stages/baby/happy.png';
import stageOrangeBabyPetted   from '../assets/pets/orange_black/stages/baby/petted.png';
import stageOrangeTeenIdle     from '../assets/pets/orange_black/stages/teen/idle.png';
import stageOrangeTeenHappy    from '../assets/pets/orange_black/stages/teen/happy.png';
import stageOrangeTeenPetted   from '../assets/pets/orange_black/stages/teen/petted.png';
import stageOrangeAdultIdle    from '../assets/pets/orange_black/stages/adult/idle.png';
import stageOrangeAdultHappy   from '../assets/pets/orange_black/stages/adult/happy.png';
import stageOrangeAdultPetted  from '../assets/pets/orange_black/stages/adult/petted.png';
import stageOrangeMythicIdle   from '../assets/pets/orange_black/stages/mythic/idle.png';
import stageOrangeMythicHappy  from '../assets/pets/orange_black/stages/mythic/happy.png';
import stageOrangeMythicPetted from '../assets/pets/orange_black/stages/mythic/petted.png';
import stageBlueEggIdle        from '../assets/pets/blue_black/stages/egg/idle.png';
import stageBlueEggHappy       from '../assets/pets/blue_black/stages/egg/happy.png';
import stageBlueEggPetted      from '../assets/pets/blue_black/stages/egg/petted.png';
import stageBlueBabyIdle       from '../assets/pets/blue_black/stages/baby/idle.png';
import stageBlueBabyHappy      from '../assets/pets/blue_black/stages/baby/happy.png';
import stageBlueBabyPetted     from '../assets/pets/blue_black/stages/baby/petted.png';
import stageBlueTeenIdle       from '../assets/pets/blue_black/stages/teen/idle.png';
import stageBlueTeenHappy      from '../assets/pets/blue_black/stages/teen/happy.png';
import stageBlueTeenPetted     from '../assets/pets/blue_black/stages/teen/petted.png';
import stageBlueAdultIdle      from '../assets/pets/blue_black/stages/adult/idle.png';
import stageBlueAdultHappy     from '../assets/pets/blue_black/stages/adult/happy.png';
import stageBlueAdultPetted    from '../assets/pets/blue_black/stages/adult/petted.png';
import stageBlueMythicIdle     from '../assets/pets/blue_black/stages/mythic/idle.png';
import stageBlueMythicHappy    from '../assets/pets/blue_black/stages/mythic/happy.png';
import stageBlueMythicPetted   from '../assets/pets/blue_black/stages/mythic/petted.png';
// Cosmetic overlays (v0.5.1, v0.6.1 expansion)
import hatParty       from '../assets/pets/cosmetics/hats/hat_party.png';
import hatCrown       from '../assets/pets/cosmetics/hats/hat_crown.png';
import hatChef        from '../assets/pets/cosmetics/hats/hat_chef.png';
import hatTop         from '../assets/pets/cosmetics/hats/hat_top.png';
import hatWizard      from '../assets/pets/cosmetics/hats/hat_wizard.png';
import hatBeanie      from '../assets/pets/cosmetics/hats/hat_beanie.png';
import hatCowboy      from '../assets/pets/cosmetics/hats/hat_cowboy.png';
import hatPirate      from '../assets/pets/cosmetics/hats/hat_pirate.png';
import hatViking      from '../assets/pets/cosmetics/hats/hat_viking.png';
import hatPropeller   from '../assets/pets/cosmetics/hats/hat_propeller.png';
import hatCatEars     from '../assets/pets/cosmetics/hats/hat_cat_ears.png';
import hatFoxEars     from '../assets/pets/cosmetics/hats/hat_fox_ears.png';
import hatBunnyEars   from '../assets/pets/cosmetics/hats/hat_bunny_ears.png';
import hatFlowerCrown from '../assets/pets/cosmetics/hats/hat_flower_crown.png';
import hatSanta       from '../assets/pets/cosmetics/hats/hat_santa.png';
import hatSun         from '../assets/pets/cosmetics/hats/hat_sun.png';
import hatBeret       from '../assets/pets/cosmetics/hats/hat_beret.png';
import particleSparkle  from '../assets/pets/cosmetics/particles/particle_sparkle.png';
import particleHearts   from '../assets/pets/cosmetics/particles/particle_hearts.png';
import particleFire     from '../assets/pets/cosmetics/particles/particle_fire.png';
import particleSnow     from '../assets/pets/cosmetics/particles/particle_snow.png';
import particleLeaves   from '../assets/pets/cosmetics/particles/particle_leaves.png';
import particleBlossoms from '../assets/pets/cosmetics/particles/particle_blossoms.png';
import particleLightning from '../assets/pets/cosmetics/particles/particle_lightning.png';
import particleMusic    from '../assets/pets/cosmetics/particles/particle_music.png';
import particleBubbles  from '../assets/pets/cosmetics/particles/particle_bubbles.png';
import particlePaws     from '../assets/pets/cosmetics/particles/particle_paws.png';
import particleRainbow  from '../assets/pets/cosmetics/particles/particle_rainbow.png';
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

/* ── Seasonal house backgrounds (v0.6.0) ───────────────────────────────────
 * Northern-hemisphere calendar: Mar–May=spring, Jun–Aug=summer,
 * Sep–Nov=autumn, Dec–Feb=winter. Returns one of 'spring'|'summer'|'autumn'|
 * 'winter' for the given Date (defaults to now). */
function getCurrentSeason(now = new Date()) {
  const m = now.getMonth(); // 0-indexed
  if (m >= 2 && m <= 4)  return 'spring';
  if (m >= 5 && m <= 7)  return 'summer';
  if (m >= 8 && m <= 10) return 'autumn';
  return 'winter';
}

// state key uses the same {day|night}{-rain}{-filthy} naming as the asset files
const SEASONAL_BG = {
  spring: {
    'day':                spring_day,
    'day-rain':           spring_dayRain,
    'day-filthy':         spring_dayFilthy,
    'day-rain-filthy':    spring_dayRainFilthy,
    'night':              spring_night,
    'night-rain':         spring_nightRain,
    'night-filthy':       spring_nightFilthy,
    'night-rain-filthy':  spring_nightRainFilthy,
  },
  summer: {
    'day':                summer_day,
    'day-rain':           summer_dayRain,
    'day-filthy':         summer_dayFilthy,
    'day-rain-filthy':    summer_dayRainFilthy,
    'night':              summer_night,
    'night-rain':         summer_nightRain,
    'night-filthy':       summer_nightFilthy,
    'night-rain-filthy':  summer_nightRainFilthy,
  },
  autumn: {
    'day':                autumn_day,
    'day-rain':           autumn_dayRain,
    'day-filthy':         autumn_dayFilthy,
    'day-rain-filthy':    autumn_dayRainFilthy,
    'night':              autumn_night,
    'night-rain':         autumn_nightRain,
    'night-filthy':       autumn_nightFilthy,
    'night-rain-filthy':  autumn_nightRainFilthy,
  },
  winter: {
    'day':                winter_day,
    'day-rain':           winter_dayRain,
    'day-filthy':         winter_dayFilthy,
    'day-rain-filthy':    winter_dayRainFilthy,
    'night':              winter_night,
    'night-rain':         winter_nightRain,
    'night-filthy':       winter_nightFilthy,
    'night-rain-filthy':  winter_nightRainFilthy,
  },
};

// Non-seasonal fallback (used when seasonal asset isn't available — currently never)
const DEFAULT_BG = {
  'day':                houseBgDay,
  'day-rain':           houseBgDayRain,
  'day-filthy':         houseBgDayFilthy,
  'day-rain-filthy':    houseBgDayRainFilthy,
  'night':              houseBgNight,
  'night-rain':         houseBgNightRain,
  'night-filthy':       houseBgNightFilthy,
  'night-rain-filthy':  houseBgNightRainFilthy,
};

function bgStateKey(isDay, isRaining, isFilthy) {
  const parts = [isDay ? 'day' : 'night'];
  if (isRaining) parts.push('rain');
  if (isFilthy)  parts.push('filthy');
  return parts.join('-');
}

function getHouseBackground(isDay, isRaining, isFilthy, season = getCurrentSeason()) {
  const key = bgStateKey(isDay, isRaining, isFilthy);
  return SEASONAL_BG[season]?.[key] || DEFAULT_BG[key] || houseBgDay;
}

const SPRITES = {
  orange_black: { idle: orangeIdle, happy: orangeHappy, sad: orangeSad, petted: orangePetted },
  blue_black:   { idle: blueIdle,   happy: blueHappy,   sad: blueSad,   petted: bluePetted   },
};

// Stage-specific sprites keyed [design][stage][state]. Missing states fall back
// to the base SPRITES map (which only has the adult form for happy/sad/petted).
// `sad` is intentionally not generated per-stage — it falls back gracefully.
const STAGE_SPRITES = {
  orange_black: {
    egg:    { idle: stageOrangeEggIdle,    happy: stageOrangeEggHappy,    petted: stageOrangeEggPetted    },
    baby:   { idle: stageOrangeBabyIdle,   happy: stageOrangeBabyHappy,   petted: stageOrangeBabyPetted   },
    teen:   { idle: stageOrangeTeenIdle,   happy: stageOrangeTeenHappy,   petted: stageOrangeTeenPetted   },
    adult:  { idle: stageOrangeAdultIdle,  happy: stageOrangeAdultHappy,  petted: stageOrangeAdultPetted  },
    mythic: { idle: stageOrangeMythicIdle, happy: stageOrangeMythicHappy, petted: stageOrangeMythicPetted },
  },
  blue_black: {
    egg:    { idle: stageBlueEggIdle,    happy: stageBlueEggHappy,    petted: stageBlueEggPetted    },
    baby:   { idle: stageBlueBabyIdle,   happy: stageBlueBabyHappy,   petted: stageBlueBabyPetted   },
    teen:   { idle: stageBlueTeenIdle,   happy: stageBlueTeenHappy,   petted: stageBlueTeenPetted   },
    adult:  { idle: stageBlueAdultIdle,  happy: stageBlueAdultHappy,  petted: stageBlueAdultPetted  },
    mythic: { idle: stageBlueMythicIdle, happy: stageBlueMythicHappy, petted: stageBlueMythicPetted },
  },
};

// Cosmetic id → image asset. Items without an asset fall back to their emoji
// icon, so adding a catalog entry doesn't require an image to be present.
const COSMETIC_IMG = {
  hat_party:         hatParty,
  hat_crown:         hatCrown,
  hat_chef:          hatChef,
  hat_top:           hatTop,
  hat_wizard:        hatWizard,
  hat_beanie:        hatBeanie,
  hat_cowboy:        hatCowboy,
  hat_pirate:        hatPirate,
  hat_viking:        hatViking,
  hat_propeller:     hatPropeller,
  hat_cat_ears:      hatCatEars,
  hat_fox_ears:      hatFoxEars,
  hat_bunny_ears:    hatBunnyEars,
  hat_flower_crown:  hatFlowerCrown,
  hat_santa:         hatSanta,
  hat_sun:           hatSun,
  hat_beret:         hatBeret,
  particle_sparkle:  particleSparkle,
  particle_hearts:   particleHearts,
  particle_fire:     particleFire,
  particle_snow:     particleSnow,
  particle_leaves:   particleLeaves,
  particle_blossoms: particleBlossoms,
  particle_lightning: particleLightning,
  particle_music:    particleMusic,
  particle_bubbles:  particleBubbles,
  particle_paws:     particlePaws,
  particle_rainbow:  particleRainbow,
};

const STATE_ANIM = {
  idle:   'animate-[pet-breathe_2.4s_ease-in-out_infinite]',
  happy:  'animate-[pet-bounce_0.6s_ease-in-out_infinite]',
  sad:    'animate-[pet-droop_2.6s_ease-in-out_infinite]',
  petted: 'animate-[pet-petted_0.5s_ease-in-out]',
};

const MOOD_TONE = {
  ecstatic: 'text-emerald-300',
  happy:    'text-emerald-400',
  meh:      'text-amber-400',
  sad:      'text-rose-400',
};

// Sprite sizing class shared by pets and mess piles
const SPRITE_CLS = 'w-[clamp(31px,11.7vw,78px)]';

// Default spots derived from the background image layout.
const DEFAULT_PET_SPOTS = [
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

const DEFAULT_MESS_SPOTS = [
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

/* ── Shared small components ──────────────────────────────────────────────── */

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

function SpriteFrame({ design, state, stage, className = '', style = {} }) {
  // Pick the stage+state sprite when available, otherwise fall back to the
  // base SPRITES map (which only has the adult-form happy/sad/petted).
  const stageSrc = stage && STAGE_SPRITES[design]?.[stage]?.[state];
  const src = stageSrc
    || SPRITES[design]?.[state]
    || SPRITES.orange_black.idle;
  const anim = STATE_ANIM[state] || STATE_ANIM.idle;
  return (
    <img
      key={`${design}-${state}-${stage || ''}`}
      src={src}
      alt=""
      className={`pixelated ${anim} ${className}`}
      style={{ objectFit: 'contain', ...style }}
    />
  );
}

function StaticPreview({ design, stage, size = 48 }) {
  const src =
    (stage && STAGE_SPRITES[design]?.[stage]?.idle)
    || SPRITES[design]?.idle
    || SPRITES.orange_black.idle;
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

/* Wraps a SpriteFrame with equipped-cosmetic overlays (hat on top, particle
 * orbiting around). Falls back to nothing when no cosmetics are equipped. */
function PetWithCosmetics({ design, state, stage, equipped, flip, className = '' }) {
  const hat = equipped?.hat;
  const particle = equipped?.particle;
  const hatImg = hat && COSMETIC_IMG[hat.id];
  const particleImg = particle && COSMETIC_IMG[particle.id];

  return (
    <div className={`relative inline-block ${className}`}>
      <SpriteFrame
        design={design}
        state={state}
        stage={stage}
        className="w-full"
        style={flip ? { transform: 'scaleX(-1)' } : undefined}
      />
      {/* Particle overlay — soft float animation, doesn't flip with the pet */}
      {particle && (
        particleImg ? (
          <img
            src={particleImg}
            alt=""
            className="pixelated absolute inset-0 w-full h-full pointer-events-none animate-[pet-breathe_2.4s_ease-in-out_infinite] opacity-90"
            style={{ objectFit: 'contain' }}
          />
        ) : (
          <span className="absolute inset-0 flex items-start justify-end text-base pointer-events-none">
            {particle.icon || '✨'}
          </span>
        )
      )}
      {/* Hat overlay — positioned at top-center of the sprite, follows the flip */}
      {hat && (
        <div
          className="absolute pointer-events-none"
          style={{
            // Anchor: top center of the sprite, sized ~45% of the sprite width
            left: '50%',
            top: '-12%',
            width: '55%',
            transform: `translateX(-50%) ${flip ? 'scaleX(-1)' : ''}`,
          }}
        >
          {hatImg ? (
            <img
              src={hatImg}
              alt=""
              className="pixelated w-full"
              style={{ objectFit: 'contain' }}
            />
          ) : (
            <span className="text-lg leading-none">{hat.icon || '👑'}</span>
          )}
        </div>
      )}
    </div>
  );
}

function stateFor(pet, celebrating, pettedId) {
  if (pettedId === pet.person_id) return 'petted';
  if (celebrating) return 'happy';
  if (pet.last_bump_at) {
    // SQLite CURRENT_TIMESTAMP is UTC without a timezone suffix — append Z before parsing
    const bumpedAt = new Date(pet.last_bump_at.replace(' ', 'T') + 'Z');
    if (Date.now() - bumpedAt.getTime() < 60 * 60 * 1000) return 'happy';
  }
  if (pet.mood === 'sad') return 'sad';
  return 'idle';
}

/* ── Mess pile (single large image + count badge) ─────────────────────────── */

function MessPile({ category, spot }) {
  const src = MESS_IMG[category] || MESS_IMG.other;
  return (
    <div
      className="absolute pointer-events-none"
      style={{
        left: `${spot.left}%`,
        top: `${spot.top}%`,
        transform: 'translate(-50%, -100%)',
      }}
    >
      <img
        src={src}
        alt=""
        className={`${SPRITE_CLS} pixelated animate-[mess-jitter_2.4s_ease-in-out_infinite]`}
      />
    </div>
  );
}

/* ── Edit-mode ghost sprite (draggable) ───────────────────────────────────── */

function Ghost({ spot, type, index, onDragStart }) {
  const isPet = type === 'pet';
  const src = isPet ? orangeIdle : messOther;
  const badge = isPet ? `🐾 ${index + 1}` : `🗑️ ${index + 1}`;
  const badgeCls = isPet
    ? 'bg-blue-900/70 text-blue-300'
    : 'bg-rose-900/70 text-rose-300';

  return (
    <div
      className="absolute z-20 cursor-grab active:cursor-grabbing select-none touch-none"
      style={{
        left: `${spot.left}%`,
        top: `${spot.top}%`,
        transform: 'translate(-50%, -100%)',
      }}
      onPointerDown={e => { e.preventDefault(); onDragStart(e, type, index); }}
    >
      <div className="relative pointer-events-none">
        <img
          src={src}
          alt=""
          className={`${SPRITE_CLS} pixelated opacity-40 grayscale`}
        />
        <span className={`absolute -top-4 left-1/2 -translate-x-1/2 whitespace-nowrap text-[9px] px-1.5 py-0.5 rounded ${badgeCls}`}>
          {badge}
        </span>
      </div>
    </div>
  );
}

/* ── Household shared summary ─────────────────────────────────────────────── */

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

/* ── Toggle switch ────────────────────────────────────────────────────────── */

function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative w-10 h-5 rounded-full transition-colors ${checked ? 'bg-amber-500' : 'bg-gray-600'}`}
      >
        <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${checked ? 'translate-x-5' : ''}`} />
      </button>
      <span className="text-xs text-gray-300">{label}</span>
    </label>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   Main Pet component
   ══════════════════════════════════════════════════════════════════════════════ */

export default function Pet({ activePerson, persons = [], isHouseholdMode, setActivePerson }) {
  const sceneRef = useRef(null);

  const [household, setHousehold] = useState(null);
  const [celebratingId, setCelebratingId] = useState(null);
  const celebrateTimer = useRef(null);
  const [pettedId, setPettedId] = useState(null);
  const [pettedKey, setPettedKey] = useState(0);
  const pettedTimer = useRef(null);

  // viewedPerson tracks whose stats are shown in the pet tab.
  // It defaults to activePerson but can be changed locally by clicking other pets
  // without affecting the global activePerson used by chores/settings.
  const [viewedPerson, setViewedPerson] = useState(activePerson);
  useEffect(() => { setViewedPerson(activePerson); }, [activePerson]);

  // Spot state: loaded from backend (fixed) or shuffled defaults (random)
  const [spots, setSpots] = useState(null);        // { pet: [...], mess: [...] }
  const [spotsLoaded, setSpotsLoaded] = useState(false);

  // Edit mode
  const [editMode, setEditMode] = useState(false);
  const [editDraft, setEditDraft] = useState(null); // working copy during edit
  const [dragging, setDragging] = useState(null);   // { type: 'pet'|'mess', index }

  // Day/night background + rain
  const [isDay, setIsDay] = useState(true);
  const [isRaining, setIsRaining] = useState(false);

  // v0.4.3 sub-tab: house | shop | wardrobe
  const [subTab, setSubTab] = useState('house');

  const personsById = useMemo(
    () => new Map(persons.map(p => [p.entity_id, p])),
    [persons],
  );

  /* ── Load sun state (on mount + every 5 min) ───────────────────────────── */
  useEffect(() => {
    const fetchSun = () => api.getSunState().then(d => { setIsDay(d.is_day); setIsRaining(d.is_raining); }).catch(() => {});
    fetchSun();
    const id = setInterval(fetchSun, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  /* ── Preload all pet sprites on mount so swaps are instant ─────────────── */
  useEffect(() => {
    const stageUrls = Object.values(STAGE_SPRITES)
      .flatMap(designStages => Object.values(designStages))
      .flatMap(stateMap => Object.values(stateMap));
    const urls = [
      ...Object.values(SPRITES).flatMap(s => Object.values(s)),
      ...stageUrls,
      ...Object.values(COSMETIC_IMG),
    ];
    urls.forEach(src => { const img = new Image(); img.src = src; });
  }, []);

  /* ── Load saved layout (once on mount) ─────────────────────────────────── */
  useEffect(() => {
    api.getLayout()
      .then(saved => {
        if (saved?.pet_spots?.length && saved?.mess_spots?.length) {
          setSpots({ pet: shuffle(saved.pet_spots), mess: shuffle(saved.mess_spots) });
        } else {
          setSpots({ pet: shuffle(DEFAULT_PET_SPOTS), mess: shuffle(DEFAULT_MESS_SPOTS) });
        }
      })
      .catch(() => {
        setSpots({ pet: shuffle(DEFAULT_PET_SPOTS), mess: shuffle(DEFAULT_MESS_SPOTS) });
      })
      .finally(() => setSpotsLoaded(true));
  }, []);

  /* ── Load household data ───────────────────────────────────────────────── */
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

  /* ── Chore-completion celebration ──────────────────────────────────────── */
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

  /* ── Drag-and-drop (document-level listeners while dragging) ───────────── */
  useEffect(() => {
    if (!dragging) return;
    const handleMove = (e) => {
      e.preventDefault();
      const rect = sceneRef.current?.getBoundingClientRect();
      if (!rect) return;
      const left = Math.max(2, Math.min(98, ((e.clientX - rect.left) / rect.width) * 100));
      const top = Math.max(2, Math.min(98, ((e.clientY - rect.top) / rect.height) * 100));
      setEditDraft(prev => {
        if (!prev) return prev;
        const key = dragging.type;
        const arr = [...prev[key]];
        arr[dragging.index] = { left: Math.round(left * 10) / 10, top: Math.round(top * 10) / 10 };
        return { ...prev, [key]: arr };
      });
    };
    const handleUp = () => setDragging(null);
    document.addEventListener('pointermove', handleMove, { passive: false });
    document.addEventListener('pointerup', handleUp);
    return () => {
      document.removeEventListener('pointermove', handleMove);
      document.removeEventListener('pointerup', handleUp);
    };
  }, [dragging]);

  /* ── Edit mode actions ─────────────────────────────────────────────────── */
  const enterEdit = () => {
    if (!spots) return;
    setEditDraft({ pet: spots.pet.map(s => ({ ...s })), mess: spots.mess.map(s => ({ ...s })) });
    setEditMode(true);
  };

  const saveEdit = async () => {
    if (editDraft) {
      setSpots(editDraft);
      try { await api.saveLayout({ pet_spots: editDraft.pet, mess_spots: editDraft.mess }); } catch { /* ok */ }
    }
    setEditMode(false);
    setEditDraft(null);
    setDragging(null);
  };

  const cancelEdit = () => {
    setEditMode(false);
    setEditDraft(null);
    setDragging(null);
  };

  const resetToDefaults = async () => {
    const fresh = { pet: shuffle(DEFAULT_PET_SPOTS), mess: shuffle(DEFAULT_MESS_SPOTS) };
    setSpots(fresh);
    setEditDraft(null);
    setEditMode(false);
    setDragging(null);
    try { await api.deleteLayout(); } catch { /* ok */ }
  };

  /* ── Pet click ─────────────────────────────────────────────────────────── */
  const handlePetClick = (personId) => {
    if (editMode) return;
    setPettedId(personId);
    setPettedKey(k => k + 1);
    clearTimeout(pettedTimer.current);
    pettedTimer.current = setTimeout(() => setPettedId(null), 3000);
    // Always update local viewed pet — never change global activePerson
    setViewedPerson(personId);
  };

  /* ── Derived data ──────────────────────────────────────────────────────── */
  const displaySpots = editMode && editDraft ? editDraft : spots;
  const myPet = household?.pets?.find(p => p.person_id === viewedPerson);
  const activeMessCategories = household
    ? Object.entries(household.shared.mess_counts).filter(([, v]) => v > 0)
    : [];

  if (!spotsLoaded) return <div className="text-gray-400 text-sm">Loading…</div>;

  /* ── Tab strip (House / Shop / Wardrobe) ───────────────────────────────── */
  const tabStrip = (
    <div className="flex gap-1 bg-gray-800 rounded-xl p-1 text-sm">
      {[
        { id: 'house', label: '🏠 House' },
        { id: 'shop', label: '🛒 Shop' },
        { id: 'wardrobe', label: '👕 Wardrobe' },
      ].map(t => (
        <button
          key={t.id}
          onClick={() => setSubTab(t.id)}
          className={`flex-1 rounded-lg px-3 py-1.5 transition-colors ${
            subTab === t.id
              ? 'bg-orange-500 text-white'
              : 'text-gray-300 hover:bg-gray-700'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );

  if (subTab !== 'house') {
    return (
      <div className="space-y-4 max-w-3xl mx-auto">
        {tabStrip}
        <PetShop
          personId={viewedPerson}
          viewMode={subTab}
          onChange={load}
        />
      </div>
    );
  }

  /* ── Render ────────────────────────────────────────────────────────────── */
  return (
    <div className="space-y-4 max-w-2xl mx-auto">

      {tabStrip}

      {/* Toggle bar */}
      <div className="flex items-center justify-between">
        <Toggle
          checked={editMode}
          onChange={v => v ? enterEdit() : saveEdit()}
          label="Change placement"
        />
        {editMode && (
          <div className="flex gap-2">
            <button onClick={resetToDefaults}
                    className="text-[11px] bg-gray-700 hover:bg-gray-600 px-2.5 py-1 rounded text-gray-300">
              ↺ Reset
            </button>
            <button onClick={cancelEdit}
                    className="text-[11px] bg-gray-700 hover:bg-gray-600 px-2.5 py-1 rounded text-gray-300">
              ✕ Cancel
            </button>
          </div>
        )}
      </div>

      {/* House scene */}
      <div className="bg-gray-800 rounded-lg p-2 sm:p-4">
        <div
          ref={sceneRef}
          className={`relative aspect-[4/3] rounded-md overflow-hidden bg-gray-900 ${editMode ? 'ring-2 ring-amber-400/40' : ''}`}
          style={{
            backgroundImage: `url(${getHouseBackground(
              isDay,
              isRaining,
              (household?.shared?.cleanliness ?? 100) < 30,
            )})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        >
          {editMode && editDraft ? (
            /* ── Edit mode: draggable ghost sprites at every spot ──────── */
            <>
              {editDraft.pet.map((spot, i) => (
                <Ghost key={`pg-${i}`} spot={spot} type="pet" index={i}
                       onDragStart={(e, t, idx) => setDragging({ type: t, index: idx })} />
              ))}
              {editDraft.mess.map((spot, i) => (
                <Ghost key={`mg-${i}`} spot={spot} type="mess" index={i}
                       onDragStart={(e, t, idx) => setDragging({ type: t, index: idx })} />
              ))}
              <div className="absolute inset-x-0 bottom-2 z-30 flex justify-center pointer-events-none">
                <span className="pointer-events-auto text-[10px] sm:text-xs bg-gray-900/80 text-gray-300 px-3 py-1.5 rounded-lg">
                  Drag 🐾 pet or 🗑️ mess sprites to reposition
                </span>
              </div>
            </>
          ) : household && displaySpots ? (
            /* ── Normal mode: live pets + mess piles ───────────────────── */
            <>
              {/* Mess piles — one pile per individual overdue chore */}
              {activeMessCategories
                .flatMap(([cat, count]) => Array.from({ length: count }, (_, j) => ({ cat, j })))
                .map(({ cat, j }, i) => (
                  <MessPile
                    key={`${cat}-${j}`}
                    category={cat}
                    spot={displaySpots.mess[i % displaySpots.mess.length]}
                  />
                ))
              }

              {/* All pets */}
              {household.pets.map((pet, i) => {
                const spot = displaySpots.pet[i % displaySpots.pet.length];
                const design = DESIGNS.includes(pet.pet_design) ? pet.pet_design : 'orange_black';
                const state = stateFor(pet, pet.person_id === celebratingId, pettedId);
                const personName = pet.pet_name || personsById.get(pet.person_id)?.name || pet.person_id;
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
                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => handlePetClick(pet.person_id)}
                        className="block rounded transition-all hover:bg-white/10"
                        title={personName}
                      >
                        <PetWithCosmetics
                          design={design}
                          state={state}
                          stage={pet.stage}
                          equipped={pet.equipped}
                          flip={flip}
                          className={SPRITE_CLS}
                        />
                      </button>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-0.5 pointer-events-none
                                      opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                        <span className="text-[9px] sm:text-[10px] bg-gray-900/80 px-1.5 py-0.5 rounded text-gray-200 whitespace-nowrap">
                          {personName}
                        </span>
                      </div>
                      {pet.person_id === pettedId && (
                        <div key={pettedKey} className="absolute inset-x-0 bottom-full pointer-events-none flex justify-center gap-2">
                          <span className="text-lg animate-[heart-float_1s_ease-out_0.1s_forwards] opacity-0">❤️</span>
                          <span className="text-sm animate-[heart-float_1s_ease-out_0.3s_forwards] opacity-0" style={{ marginLeft: '-6px', marginTop: '4px' }}>❤️</span>
                          <span className="text-base animate-[heart-float_1s_ease-out_0s_forwards] opacity-0" style={{ marginLeft: '-4px' }}>❤️</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Mood badge */}
              {myPet && (
                <div className="absolute top-2 left-2 text-xs uppercase tracking-widest bg-gray-900/70 px-2 py-0.5 rounded">
                  <span className={MOOD_TONE[myPet.mood] || 'text-gray-300'}>{myPet.mood}</span>
                </div>
              )}
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">Loading…</div>
          )}
        </div>
      </div>

      {/* Personal stats */}
      {!editMode && myPet && (
        <div className="bg-gray-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm text-gray-300">
            <StaticPreview design={myPet.pet_design} stage={myPet.stage} size={32} />
            <span className="font-semibold">{myPet.pet_name || personsById.get(viewedPerson)?.name || 'Your pet'}</span>
            {myPet.stage && (
              <span className="text-[10px] uppercase tracking-wider bg-gray-700 text-gray-200 px-1.5 py-0.5 rounded">
                {myPet.stage}
              </span>
            )}
            <span className={`ml-auto text-xs uppercase ${MOOD_TONE[myPet.mood] || 'text-gray-400'}`}>
              {myPet.mood}
            </span>
          </div>
          <Bar value={myPet.happiness}   label="❤️ Happiness"   color="bg-pink-500" />
          <Bar value={myPet.cleanliness} label="🛁 Cleanliness" color="bg-sky-500" />
        </div>
      )}

      {/* Shared household summary */}
      {!editMode && household && <HouseholdShared shared={household.shared} />}
    </div>
  );
}
