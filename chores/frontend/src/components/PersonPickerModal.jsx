import { useEffect, useRef } from 'react';

export default function PersonPickerModal({ title, persons, onSelect, onCancel }) {
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onCancel();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onCancel]);

  // Trap Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCancel(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div ref={ref} className="bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-center">{title}</h2>
        </div>
        <div className="py-2 max-h-80 overflow-y-auto">
          {persons.map(p => (
            <button
              key={p.entity_id}
              onClick={() => onSelect(p.entity_id)}
              className="w-full text-left px-5 py-3 hover:bg-gray-700 active:bg-gray-600 transition-colors flex items-center gap-3"
            >
              <span className="w-10 h-10 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-lg shrink-0">
                {p.name.charAt(0).toUpperCase()}
              </span>
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-gray-500">Level {p.level || 1}</div>
              </div>
            </button>
          ))}
        </div>
        <div className="px-5 py-3 border-t border-gray-700">
          <button
            onClick={onCancel}
            className="w-full py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
