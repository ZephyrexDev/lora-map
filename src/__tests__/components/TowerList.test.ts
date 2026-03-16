// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import TowerList from "../../components/TowerList.vue";
import { useStore } from "../../store";
import type { SplatParams } from "../../types";

function makeSplatParams(): SplatParams {
  return {
    transmitter: { name: "Tower A", tx_lat: 51, tx_lon: -114, tx_power: 0.1, tx_freq: 907, tx_height: 10, tx_gain: 2 },
    receiver: {
      rx_sensitivity: -130,
      rx_height: 1,
      rx_gain: 2,
      rx_loss: 2,
      window_mode: false,
      window_azimuth: 0,
      window_fov: 90,
      glass_type: "double",
      structural_material: "brick",
    },
    environment: {
      radio_climate: "continental_temperate",
      polarization: "vertical",
      clutter_height: 1,
      ground_dielectric: 15,
      ground_conductivity: 0.005,
      atmosphere_bending: 301,
    },
    simulation: { situation_fraction: 95, time_fraction: 95, simulation_extent: 30, high_resolution: false },
    display: { color_scale: "plasma", min_dbm: -130, max_dbm: -80, overlay_transparency: 50, overlapMode: "hatch" },
  };
}

describe("TowerList.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false })),
    );
  });

  function mountTowerList() {
    return mount(TowerList);
  }

  it("shows 'No towers' message when list is empty", () => {
    const wrapper = mountTowerList();
    expect(wrapper.text()).toContain("No towers");
  });

  it("hides 'No towers' message when towers exist", () => {
    const store = useStore();
    store.localSites = [
      { params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#e6194b", visible: true },
    ];
    const wrapper = mountTowerList();
    expect(wrapper.text()).not.toContain("No towers");
  });

  it("renders tower name from params", () => {
    const store = useStore();
    store.localSites = [
      { params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#e6194b", visible: true },
    ];
    const wrapper = mountTowerList();
    expect(wrapper.text()).toContain("Tower A");
  });

  it("renders tower color indicator", () => {
    const store = useStore();
    store.localSites = [
      { params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#3cb44b", visible: true },
    ];
    const wrapper = mountTowerList();
    const dot = wrapper.find(".rounded-circle");
    expect(dot.attributes("style")).toContain("background-color: rgb(60, 180, 75)");
  });

  it("shows eye emoji for visible site", () => {
    const store = useStore();
    store.localSites = [{ params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true }];
    const wrapper = mountTowerList();
    // Eye emoji: 👁️
    expect(wrapper.find("button.btn-outline-light").text()).toContain("👁️");
  });

  it("shows prohibition emoji for hidden site", () => {
    const store = useStore();
    store.localSites = [
      { params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: false },
    ];
    const wrapper = mountTowerList();
    expect(wrapper.find("button.btn-outline-light .text-muted").exists()).toBe(true);
  });

  it("calls toggleSiteVisibility on eye button click", async () => {
    const store = useStore();
    store.localSites = [{ params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true }];
    store.toggleSiteVisibility = vi.fn();
    const wrapper = mountTowerList();
    await wrapper.find("button.btn-outline-light").trigger("click");
    expect(store.toggleSiteVisibility).toHaveBeenCalledWith(0);
  });

  it("hides delete button for non-admin", () => {
    const store = useStore();
    store.isAdmin = false;
    store.localSites = [{ params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true }];
    const wrapper = mountTowerList();
    expect(wrapper.find("button.btn-outline-danger").exists()).toBe(false);
  });

  it("shows delete button for admin", () => {
    const store = useStore();
    store.isAdmin = true;
    store.localSites = [{ params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true }];
    const wrapper = mountTowerList();
    expect(wrapper.find("button.btn-outline-danger").exists()).toBe(true);
  });

  it("calls removeSite on delete button click", async () => {
    const store = useStore();
    store.isAdmin = true;
    store.localSites = [{ params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true }];
    store.removeSite = vi.fn();
    const wrapper = mountTowerList();
    await wrapper.find("button.btn-outline-danger").trigger("click");
    expect(store.removeSite).toHaveBeenCalledWith(0);
  });

  it("hides mesh paths button when fewer than 2 towers", () => {
    const store = useStore();
    store.localSites = [{ params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true }];
    const wrapper = mountTowerList();
    expect(wrapper.find("button.btn-outline-secondary, button.btn-outline-info").exists()).toBe(false);
  });

  it("shows mesh paths button when 2+ towers exist", () => {
    const store = useStore();
    store.localSites = [
      { params: makeSplatParams(), taskId: "t1", raster: {} as never, color: "#f00", visible: true },
      { params: makeSplatParams(), taskId: "t2", raster: {} as never, color: "#0f0", visible: true },
    ];
    const wrapper = mountTowerList();
    const pathBtn = wrapper.findAll("button").find((b) => b.text().includes("Mesh Paths"));
    expect(pathBtn).toBeDefined();
  });

  it("renders multiple towers in correct order", () => {
    const store = useStore();
    const params1 = makeSplatParams();
    params1.transmitter.name = "Alpha";
    const params2 = makeSplatParams();
    params2.transmitter.name = "Bravo";
    store.localSites = [
      { params: params1, taskId: "t1", raster: {} as never, color: "#f00", visible: true },
      { params: params2, taskId: "t2", raster: {} as never, color: "#0f0", visible: true },
    ];
    const wrapper = mountTowerList();
    const items = wrapper.findAll(".list-group-item");
    expect(items).toHaveLength(2);
    expect(items[0].text()).toContain("Alpha");
    expect(items[1].text()).toContain("Bravo");
  });
});
