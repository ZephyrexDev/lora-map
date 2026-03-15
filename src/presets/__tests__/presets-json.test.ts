import { describe, it, expect } from 'vitest';
import presets from '../presets.json';

describe('presets.json', () => {
  it('has all 4 top-level keys', () => {
    expect(presets).toHaveProperty('hardware');
    expect(presets).toHaveProperty('antennas');
    expect(presets).toHaveProperty('frequencies');
    expect(presets).toHaveProperty('heights');
    expect(Object.keys(presets)).toHaveLength(4);
  });

  it('no empty arrays', () => {
    expect(presets.hardware.length).toBeGreaterThan(0);
    expect(presets.antennas.length).toBeGreaterThan(0);
    expect(presets.frequencies.length).toBeGreaterThan(0);
    expect(presets.heights.length).toBeGreaterThan(0);
  });
});
