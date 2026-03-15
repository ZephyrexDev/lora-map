// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Display from "../../components/Display.vue";
import { useStore } from "../../store";

describe("Display.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function mountDisplay() {
    return mount(Display);
  }

  it("renders min and max dBm inputs with default values", () => {
    const wrapper = mountDisplay();
    const minInput = wrapper.find<HTMLInputElement>("#min_dbm");
    const maxInput = wrapper.find<HTMLInputElement>("#max_dbm");
    expect(minInput.element.value).toBe("-130");
    expect(maxInput.element.value).toBe("-80");
  });

  it("renders color scale selector with default 'plasma'", () => {
    const wrapper = mountDisplay();
    const select = wrapper.find<HTMLSelectElement>("#color_scale");
    expect(select.element.value).toBe("plasma");
  });

  it("renders all six color scale options", () => {
    const wrapper = mountDisplay();
    const options = wrapper.findAll("#color_scale option");
    expect(options).toHaveLength(6);
    const values = options.map((o) => o.attributes("value"));
    expect(values).toEqual(expect.arrayContaining(["plasma", "CMRmap", "cool", "viridis", "turbo", "jet"]));
  });

  it("renders transparency input with default 50", () => {
    const wrapper = mountDisplay();
    const input = wrapper.find<HTMLInputElement>("#overlay_transparency");
    expect(input.element.value).toBe("50");
  });

  it("renders overlap mode selector with default 'hatch'", () => {
    const wrapper = mountDisplay();
    const select = wrapper.find<HTMLSelectElement>("#overlap_mode");
    expect(select.element.value).toBe("hatch");
  });

  it("renders colorbar image with correct src", () => {
    const wrapper = mountDisplay();
    const img = wrapper.find("img[alt='Colorbar']");
    expect(img.attributes("src")).toBe("/colormaps/plasma.png");
  });

  it("updates colorbar image src when color_scale changes", async () => {
    const wrapper = mountDisplay();
    const store = useStore();
    store.splatParams.display.color_scale = "viridis";
    await wrapper.vm.$nextTick();
    const img = wrapper.find("img[alt='Colorbar']");
    expect(img.attributes("src")).toBe("/colormaps/viridis.png");
  });

  it("renders dBm badges with current values", () => {
    const wrapper = mountDisplay();
    const badges = wrapper.findAll(".badge.bg-primary");
    expect(badges).toHaveLength(2);
    expect(badges[0].text()).toContain("-130");
    expect(badges[1].text()).toContain("-80");
  });

  it("deadzone toggle is disabled with fewer than 2 sites", () => {
    const wrapper = mountDisplay();
    const toggle = wrapper.find<HTMLInputElement>("#deadzoneToggle");
    expect(toggle.element.disabled).toBe(true);
  });

  it("shows 'Requires at least 2' message with fewer than 2 sites", () => {
    const wrapper = mountDisplay();
    expect(wrapper.text()).toContain("Requires at least 2 completed simulations");
  });

  it("deadzone toggle is enabled when 2+ sites exist", () => {
    const store = useStore();
    store.localSites = [
      { params: store.splatParams, taskId: "a", raster: {} as never, color: "#f00", visible: true },
      { params: store.splatParams, taskId: "b", raster: {} as never, color: "#0f0", visible: true },
    ];
    const wrapper = mountDisplay();
    const toggle = wrapper.find<HTMLInputElement>("#deadzoneToggle");
    expect(toggle.element.disabled).toBe(false);
  });

  it("displays coverage stats when deadzones are shown", () => {
    const store = useStore();
    store.localSites = [
      { params: store.splatParams, taskId: "a", raster: {} as never, color: "#f00", visible: true },
      { params: store.splatParams, taskId: "b", raster: {} as never, color: "#0f0", visible: true },
    ];
    store.showDeadzones = true;
    store.deadzoneAnalysis = {
      bounds: { north: 52, south: 50, east: -113, west: -115 },
      total_coverage_km2: 100,
      total_deadzone_km2: 25,
      coverage_fraction: 0.8,
      regions: [],
      suggestions: [],
      tower_count: 2,
    };
    const wrapper = mountDisplay();
    expect(wrapper.text()).toContain("80.0%");
    expect(wrapper.text()).toContain("100.0");
    expect(wrapper.text()).toContain("25.0");
    expect(wrapper.text()).toContain("0 suggested sites");
  });

  it("updates store when min_dbm is changed", async () => {
    const wrapper = mountDisplay();
    const store = useStore();
    await wrapper.find("#min_dbm").setValue("-120");
    expect(store.splatParams.display.min_dbm).toBe(-120);
  });

  it("updates store when color_scale is changed", async () => {
    const wrapper = mountDisplay();
    const store = useStore();
    await wrapper.find("#color_scale").setValue("turbo");
    expect(store.splatParams.display.color_scale).toBe("turbo");
  });
});
