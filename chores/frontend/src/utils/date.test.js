// Run with `npm test` (Node's built-in runner). TZ must be set before any Date is built.
process.env.TZ = 'Europe/Helsinki';

import test from 'node:test';
import assert from 'node:assert/strict';
import { localISODate } from './date.js';

test('localISODate gives the local date after midnight, not the UTC one', () => {
  assert.equal(localISODate(new Date('2026-11-16T23:30:00Z')), '2026-11-17'); // 01:30 EET
  assert.equal(localISODate(new Date('2026-07-15T22:30:00Z')), '2026-07-16'); // 01:30 EEST
  assert.equal(localISODate(new Date('2026-11-16T21:30:00Z')), '2026-11-16'); // 23:30 EET
});
