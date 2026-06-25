// App-wide date formatting. All user-facing dates render as DD/MM/YYYY
// (with HH:MM appended for datetimes via formatDateTime).
//
// We pull the Y/M/D (and optional H:M) straight out of the ISO-ish string the
// backend sends ("YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS", or the SQLite
// "YYYY-MM-DD HH:MM:SS" timestamp form) rather than routing through `new Date()`,
// so a date never shifts a day across a timezone boundary. A Date instance (or
// any other string) falls back to the local-time getters.

function pad(n) {
  return String(n).padStart(2, '0');
}

function parts(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'string') {
    const m = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
    if (m) return { y: m[1], mo: m[2], d: m[3], h: m[4], mi: m[5] };
  }
  const dt = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(dt.getTime())) return null;
  return {
    y: String(dt.getFullYear()),
    mo: pad(dt.getMonth() + 1),
    d: pad(dt.getDate()),
    h: pad(dt.getHours()),
    mi: pad(dt.getMinutes()),
  };
}

/** Format a date/datetime value as `DD/MM/YYYY`. Returns '' for empty/invalid input. */
export function formatDate(value) {
  const p = parts(value);
  return p ? `${p.d}/${p.mo}/${p.y}` : '';
}

/** Format as `DD/MM/YYYY HH:MM`, or `DD/MM/YYYY` when the value has no time component. */
export function formatDateTime(value) {
  const p = parts(value);
  if (!p) return '';
  return p.h != null ? `${p.d}/${p.mo}/${p.y} ${p.h}:${p.mi}` : `${p.d}/${p.mo}/${p.y}`;
}
