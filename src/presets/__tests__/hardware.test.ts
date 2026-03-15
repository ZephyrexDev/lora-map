import { describe, it, expect } from 'vitest';
import { HARDWARE_PRESETS } from '../hardware';

describe('HARDWARE_PRESETS', () => {
  it('has 3 entries', () => {
    expect(HARDWARE_PRESETS).toHaveLength(3);
  });

  it('V3 has is_custom=false', () => {
    const v3 = HARDWARE_PRESETS.find(h => h.name === 'Heltec V3');
    expect(v3).toBeDefined();
    expect(v3!.is_custom).toBe(false);
  });

  it('V4 has is_custom=false', () => {
    const v4 = HARDWARE_PRESETS.find(h => h.name === 'Heltec V4');
    expect(v4).toBeDefined();
    expect(v4!.is_custom).toBe(false);
  });

  it('Custom has is_custom=true', () => {
    const custom = HARDWARE_PRESETS.find(h => h.name === 'Custom');
    expect(custom).toBeDefined();
    expect(custom!.is_custom).toBe(true);
  });

  it('all presets have required fields', () => {
    for (const preset of HARDWARE_PRESETS) {
      expect(typeof preset.name).toBe('string');
      expect(typeof preset.max_power_dbm).toBe('number');
      expect(typeof preset.chip).toBe('string');
      expect(typeof preset.is_custom).toBe('boolean');
    }
  });
});
