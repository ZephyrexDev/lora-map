import { describe, it, expect } from 'vitest';
import type { Site, SplatParams } from '../types';

describe('Site interface', () => {
  it('can construct a valid Site object', () => {
    const site: Site = {
      params: {
        transmitter: {
          name: 'test',
          tx_lat: 51.0,
          tx_lon: -114.0,
          tx_power: 0.1,
          tx_freq: 907.0,
          tx_height: 2.0,
          tx_gain: 2.0,
          tx_swr: 1.0,
          tx_color: '#ff0000',
        },
        receiver: {
          rx_sensitivity: -130.0,
          rx_height: 1.0,
          rx_gain: 2.0,
          rx_loss: 2.0,
        },
        environment: {
          radio_climate: 'continental_temperate',
          polarization: 'vertical',
          clutter_height: 1.0,
          ground_dielectric: 15.0,
          ground_conductivity: 0.005,
          atmosphere_bending: 301.0,
        },
        simulation: {
          situation_fraction: 95.0,
          time_fraction: 95.0,
          simulation_extent: 30.0,
          high_resolution: false,
        },
        display: {
          color_scale: 'plasma',
          min_dbm: -130.0,
          max_dbm: -80.0,
          overlay_transparency: 50,
        },
      },
      taskId: 'abc-123',
      raster: null,
      visible: true,
      color: '#ff0000',
    };

    expect(site.taskId).toBe('abc-123');
    expect(site.visible).toBe(true);
    expect(site.color).toBe('#ff0000');
    expect(site.params.transmitter.tx_swr).toBe(1.0);
    expect(site.layer).toBeUndefined();
  });
});

describe('SplatParams interface', () => {
  it('has all five sections', () => {
    const params: SplatParams = {
      transmitter: { name: '', tx_lat: 0, tx_lon: 0, tx_power: 0, tx_freq: 0, tx_height: 0, tx_gain: 0, tx_swr: 1, tx_color: '' },
      receiver: { rx_sensitivity: 0, rx_height: 0, rx_gain: 0, rx_loss: 0 },
      environment: { radio_climate: '', polarization: '', clutter_height: 0, ground_dielectric: 0, ground_conductivity: 0, atmosphere_bending: 0 },
      simulation: { situation_fraction: 0, time_fraction: 0, simulation_extent: 0, high_resolution: false },
      display: { color_scale: '', min_dbm: 0, max_dbm: 0, overlay_transparency: 0 },
    };

    expect(Object.keys(params)).toEqual(
      expect.arrayContaining(['transmitter', 'receiver', 'environment', 'simulation', 'display'])
    );
  });
});
