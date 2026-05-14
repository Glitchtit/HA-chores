import { useCallback, useEffect, useMemo, useState } from 'react';
import * as api from '../api';
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
import hatGraduate    from '../assets/pets/cosmetics/hats/hat_graduate.png';
import hatHalo        from '../assets/pets/cosmetics/hats/hat_halo.png';
import hatLaurel      from '../assets/pets/cosmetics/hats/hat_laurel.png';
import particleSparkle   from '../assets/pets/cosmetics/particles/particle_sparkle.png';
import particleHearts    from '../assets/pets/cosmetics/particles/particle_hearts.png';
import particleFire      from '../assets/pets/cosmetics/particles/particle_fire.png';
import particleSnow      from '../assets/pets/cosmetics/particles/particle_snow.png';
import particleLeaves    from '../assets/pets/cosmetics/particles/particle_leaves.png';
import particleBlossoms  from '../assets/pets/cosmetics/particles/particle_blossoms.png';
import particleLightning from '../assets/pets/cosmetics/particles/particle_lightning.png';
import particleMusic     from '../assets/pets/cosmetics/particles/particle_music.png';
import particleBubbles   from '../assets/pets/cosmetics/particles/particle_bubbles.png';
import particlePaws      from '../assets/pets/cosmetics/particles/particle_paws.png';
import particleRainbow   from '../assets/pets/cosmetics/particles/particle_rainbow.png';
import particleStars     from '../assets/pets/cosmetics/particles/particle_stars.png';
import bgMeadow          from '../assets/pets/cosmetics/backgrounds/bg_meadow.png';
import bgBeach           from '../assets/pets/cosmetics/backgrounds/bg_beach.png';
import bgSpace           from '../assets/pets/cosmetics/backgrounds/bg_space.png';
import bgForest          from '../assets/pets/cosmetics/backgrounds/bg_forest.png';
import bgAurora          from '../assets/pets/cosmetics/backgrounds/bg_aurora.png';
import plateGold         from '../assets/pets/cosmetics/nameplates/plate_gold.png';
import plateSilver       from '../assets/pets/cosmetics/nameplates/plate_silver.png';

const COSMETIC_IMG = {
  hat_party:          hatParty,
  hat_crown:          hatCrown,
  hat_chef:           hatChef,
  hat_top:            hatTop,
  hat_wizard:         hatWizard,
  hat_beanie:         hatBeanie,
  hat_cowboy:         hatCowboy,
  hat_pirate:         hatPirate,
  hat_viking:         hatViking,
  hat_propeller:      hatPropeller,
  hat_cat_ears:       hatCatEars,
  hat_fox_ears:       hatFoxEars,
  hat_bunny_ears:     hatBunnyEars,
  hat_flower_crown:   hatFlowerCrown,
  hat_santa:          hatSanta,
  hat_sun:            hatSun,
  hat_beret:          hatBeret,
  hat_graduate:       hatGraduate,
  hat_halo:           hatHalo,
  hat_laurel:         hatLaurel,
  particle_sparkle:   particleSparkle,
  particle_hearts:    particleHearts,
  particle_fire:      particleFire,
  particle_snow:      particleSnow,
  particle_leaves:    particleLeaves,
  particle_blossoms:  particleBlossoms,
  particle_lightning: particleLightning,
  particle_music:     particleMusic,
  particle_bubbles:   particleBubbles,
  particle_paws:      particlePaws,
  particle_rainbow:   particleRainbow,
  particle_stars:     particleStars,
  bg_meadow:          bgMeadow,
  bg_beach:           bgBeach,
  bg_space:           bgSpace,
  bg_forest:          bgForest,
  bg_aurora:          bgAurora,
  plate_gold:         plateGold,
  plate_silver:       plateSilver,
};

const SLOT_LABEL = {
  hat: 'Hats',
  background: 'Backgrounds',
  particle: 'Particles',
  nameplate: 'Nameplates',
  evolution: 'Evolution',
};

const SLOT_ORDER = ['hat', 'background', 'particle', 'nameplate'];

const UNLOCK_LABEL = {
  shop: 'Shop',
  level: 'Level unlock',
  boss: 'Boss reward',
  gift: 'Gifted',
};

function ItemCard({ item, onPurchase, onEquip, onUnequip, tokens, busy }) {
  const cantAfford = !item.owned && item.unlock_type === 'shop' && item.cost_tokens > tokens;
  const lockedByLevel = !item.owned && item.unlock_type === 'level' && !item.unlocked;
  const bossLocked = !item.owned && item.unlock_type === 'boss';

  let cta;
  if (item.equipped) {
    cta = (
      <button
        className="w-full mt-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-xs text-gray-200 px-2 py-1.5"
        onClick={() => onUnequip(item.slot)}
        disabled={busy}
      >
        Unequip
      </button>
    );
  } else if (item.owned) {
    cta = (
      <button
        className="w-full mt-2 rounded-lg bg-orange-500 hover:bg-orange-400 text-xs text-white px-2 py-1.5"
        onClick={() => onEquip(item.id)}
        disabled={busy}
      >
        Equip
      </button>
    );
  } else if (bossLocked) {
    cta = (
      <button className="w-full mt-2 rounded-lg bg-gray-800 text-[11px] text-gray-500 px-2 py-1.5 cursor-not-allowed" disabled>
        Defeat the boss
      </button>
    );
  } else if (lockedByLevel) {
    cta = (
      <button className="w-full mt-2 rounded-lg bg-gray-800 text-[11px] text-gray-500 px-2 py-1.5 cursor-not-allowed" disabled>
        Lv. {item.unlock_value}
      </button>
    );
  } else {
    cta = (
      <button
        className={`w-full mt-2 rounded-lg text-xs px-2 py-1.5 ${
          cantAfford
            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-500 text-white'
        }`}
        onClick={() => onPurchase(item.id)}
        disabled={busy || cantAfford}
        title={cantAfford ? 'Not enough tokens' : ''}
      >
        {item.cost_tokens > 0 ? `${item.cost_tokens} 🪙` : 'Claim'}
      </button>
    );
  }

  const assetSrc = COSMETIC_IMG[item.id];
  return (
    <div
      className={`rounded-xl border p-3 flex flex-col items-center text-center ${
        item.equipped
          ? 'bg-orange-500/10 border-orange-400/60'
          : item.owned
          ? 'bg-gray-800 border-gray-700'
          : 'bg-gray-800/60 border-gray-700/60'
      }`}
    >
      {assetSrc ? (
        <img
          src={assetSrc}
          alt={item.name}
          className="pixelated h-12 w-12 object-contain"
        />
      ) : (
        <div className="text-3xl">{item.icon || '✨'}</div>
      )}
      <div className="mt-1 text-sm font-medium text-gray-100">{item.name}</div>
      <div className="text-[10px] uppercase tracking-wide text-gray-500 mt-0.5">
        {UNLOCK_LABEL[item.unlock_type] || item.unlock_type}
      </div>
      {cta}
    </div>
  );
}

export default function PetShop({ personId, viewMode = 'shop', onChange }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    if (!personId) return;
    try {
      const d = await api.getMyCosmetics(personId);
      setData(d);
    } catch (e) {
      setError('Failed to load shop');
    }
  }, [personId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const handlePurchase = async (cosmeticId) => {
    setBusy(true);
    setError(null);
    try {
      await api.purchaseCosmetic(personId, cosmeticId);
      await reload();
      onChange?.();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Purchase failed');
    } finally {
      setBusy(false);
    }
  };

  const handleEquip = async (cosmeticId) => {
    setBusy(true);
    setError(null);
    try {
      await api.equipCosmetic(personId, cosmeticId);
      await reload();
      onChange?.();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Equip failed');
    } finally {
      setBusy(false);
    }
  };

  const handleUnequip = async (slot) => {
    setBusy(true);
    setError(null);
    try {
      await api.unequipCosmetic(personId, slot);
      await reload();
      onChange?.();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Unequip failed');
    } finally {
      setBusy(false);
    }
  };

  const filtered = useMemo(() => {
    if (!data?.items) return [];
    return viewMode === 'wardrobe' ? data.items.filter((i) => i.owned) : data.items;
  }, [data, viewMode]);

  const grouped = useMemo(() => {
    const groups = {};
    for (const slot of SLOT_ORDER) groups[slot] = [];
    for (const item of filtered) {
      if (!groups[item.slot]) groups[item.slot] = [];
      groups[item.slot].push(item);
    }
    return groups;
  }, [filtered]);

  if (!data) {
    return <div className="text-gray-400 text-sm">Loading…</div>;
  }

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2">
        <span className="text-sm text-gray-300">
          {viewMode === 'wardrobe' ? 'Your collection' : 'Spend tokens earned from chores'}
        </span>
        <span className="text-base font-semibold text-amber-300">{data.tokens} 🪙</span>
      </div>

      {error && (
        <div className="bg-rose-900/40 border border-rose-700 text-rose-200 text-sm rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {viewMode === 'wardrobe' && filtered.length === 0 && (
        <div className="text-gray-400 text-sm text-center py-8">
          You don't own any cosmetics yet. Head to the shop!
        </div>
      )}

      {SLOT_ORDER.map((slot) =>
        grouped[slot]?.length ? (
          <section key={slot} className="space-y-2">
            <h3 className="text-xs uppercase tracking-widest text-gray-400">
              {SLOT_LABEL[slot] || slot}
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {grouped[slot].map((item) => (
                <ItemCard
                  key={item.id}
                  item={item}
                  tokens={data.tokens}
                  busy={busy}
                  onPurchase={handlePurchase}
                  onEquip={handleEquip}
                  onUnequip={handleUnequip}
                />
              ))}
            </div>
          </section>
        ) : null,
      )}
    </div>
  );
}
