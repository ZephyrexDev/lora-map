/**
 * Shared test setup for Vue component integration tests.
 * Provides mocks for Leaflet, Bootstrap, and other external dependencies
 * that components initialize in lifecycle hooks.
 */
import { vi } from "vitest";
import { config } from "@vue/test-utils";

// ---------------------------------------------------------------------------
// Mock Leaflet — components import L and call map/marker/divIcon methods
// ---------------------------------------------------------------------------
const mockMap = {
  setView: vi.fn().mockReturnThis(),
  getZoom: vi.fn(() => 10),
  removeLayer: vi.fn(),
  addTo: vi.fn().mockReturnThis(),
  once: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  dragging: { enable: vi.fn(), disable: vi.fn() },
  eachLayer: vi.fn(),
  getSize: vi.fn(() => ({ x: 800, y: 600 })),
  getPane: vi.fn(() => document.createElement("div")),
  containerPointToLayerPoint: vi.fn(() => ({ x: 0, y: 0 })),
  latLngToContainerPoint: vi.fn(() => ({ x: 0, y: 0 })),
  unproject: vi.fn(() => ({ lat: 0, lng: 0 })),
};

const mockMarker = {
  addTo: vi.fn().mockReturnThis(),
  bindPopup: vi.fn().mockReturnThis(),
  removeFrom: vi.fn().mockReturnThis(),
};

vi.mock("leaflet", () => ({
  default: {
    map: vi.fn(() => mockMap),
    marker: vi.fn(() => mockMarker),
    divIcon: vi.fn(() => ({})),
    control: {
      zoom: vi.fn(() => ({ addTo: vi.fn() })),
      layers: vi.fn(() => ({ addTo: vi.fn() })),
    },
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    point: vi.fn((x: number, y: number) => ({ x, y })),
    latLng: vi.fn((lat: number, lng: number) => ({ lat, lng, toBounds: vi.fn(() => ({ getNorth: () => lat })) })),
    DomUtil: {
      create: vi.fn(() => document.createElement("canvas")),
      setPosition: vi.fn(),
    },
    Layer: class {},
    GridLayer: {
      extend: vi.fn(() => class {}),
    },
    Util: { setOptions: vi.fn() },
    polygon: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
      setLatLngs: vi.fn(),
    })),
    circleMarker: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
      setLatLng: vi.fn(),
      on: vi.fn(),
    })),
    polyline: vi.fn(() => ({ addTo: vi.fn(), bindPopup: vi.fn() })),
    easyPrint: vi.fn(() => ({ addTo: vi.fn() })),
  },
  DivIcon: class {},
}));

// ---------------------------------------------------------------------------
// Mock Bootstrap — Popover/Modal initialized in component lifecycle hooks
// ---------------------------------------------------------------------------
vi.mock("bootstrap", () => ({
  Popover: class {
    show = vi.fn();
    hide = vi.fn();
    dispose = vi.fn();
  },
  Modal: {
    getInstance: vi.fn(() => ({ hide: vi.fn() })),
  },
}));

// Mock the dynamic bootstrap import used by LoginForm
vi.mock("bootstrap/dist/js/bootstrap.bundle.min.js", () => ({
  Modal: {
    getInstance: vi.fn(() => ({ hide: vi.fn() })),
  },
}));

// ---------------------------------------------------------------------------
// Mock georaster + georaster-layer-for-leaflet
// ---------------------------------------------------------------------------
vi.mock("georaster", () => ({
  default: vi.fn(() => Promise.resolve({ values: [[[0]]], xmin: 0, xmax: 1, ymin: 0, ymax: 1 })),
}));

vi.mock("georaster-layer-for-leaflet", () => ({
  default: class {
    addTo = vi.fn().mockReturnThis();
    bringToFront = vi.fn();
    setOpacity = vi.fn();
  },
}));

// ---------------------------------------------------------------------------
// Mock randanimal
// ---------------------------------------------------------------------------
vi.mock("randanimal", () => ({
  randanimalSync: vi.fn(() => "test-animal"),
}));

// ---------------------------------------------------------------------------
// Mock leaflet-easyprint (side-effect import)
// ---------------------------------------------------------------------------
vi.mock("leaflet-easyprint", () => ({}));

// ---------------------------------------------------------------------------
// Stub global fetch so relative URLs (/towers, /tower-paths) don't fail in jsdom
// ---------------------------------------------------------------------------
vi.stubGlobal(
  "fetch",
  vi.fn(() =>
    Promise.resolve({
      ok: false,
      json: () => Promise.resolve({}),
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    }),
  ),
);

// ---------------------------------------------------------------------------
// Suppress Vue warnings for missing global components
// ---------------------------------------------------------------------------
config.global.stubs = {};

export { mockMap, mockMarker };
