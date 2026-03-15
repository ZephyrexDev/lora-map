import { describe, it, expect } from 'vitest';
import { HEIGHT_PRESETS } from '../heights';

describe('HEIGHT_PRESETS', () => {
  it('has 7 entries', () => {
    expect(HEIGHT_PRESETS).toHaveLength(7);
  });

  it('heights are in ascending order', () => {
    for (let i = 1; i < HEIGHT_PRESETS.length; i++) {
      expect(HEIGHT_PRESETS[i].height_m).toBeGreaterThan(HEIGHT_PRESETS[i - 1].height_m);
    }
  });

  it('all have label and height_m', () => {
    for (const preset of HEIGHT_PRESETS) {
      expect(typeof preset.label).toBe('string');
      expect(preset.label.length).toBeGreaterThan(0);
      expect(typeof preset.height_m).toBe('number');
      expect(preset.height_m).toBeGreaterThan(0);
    }
  });
});
