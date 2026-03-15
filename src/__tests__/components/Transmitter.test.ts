// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Transmitter from "../../components/Transmitter.vue";
import { useStore } from "../../store";
import { HARDWARE_PRESETS } from "../../presets/hardware";
import { FREQUENCY_PRESETS } from "../../presets/frequencies";
import { ANTENNA_PRESETS } from "../../presets/antennas";
import { HEIGHT_PRESETS } from "../../presets/heights";

describe("Transmitter.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function mountTransmitter() {
    return mount(Transmitter);
  }

  // -----------------------------------------------------------------------
  // Rendering
  // -----------------------------------------------------------------------

  it("renders site name input with default value from store", () => {
    const wrapper = mountTransmitter();
    const input = wrapper.find<HTMLInputElement>("#name");
    expect(input.exists()).toBe(true);
    expect(input.element.value).toBeTruthy(); // randanimal name
  });

  it("renders latitude and longitude inputs", () => {
    const wrapper = mountTransmitter();
    expect(wrapper.find("#tx_lat").exists()).toBe(true);
    expect(wrapper.find("#tx_lon").exists()).toBe(true);
  });

  it("renders hardware preset dropdown with Custom + all presets", () => {
    const wrapper = mountTransmitter();
    const options = wrapper.findAll("#hardwarePreset option");
    // Custom + each HARDWARE_PRESETS entry
    expect(options.length).toBe(1 + HARDWARE_PRESETS.length);
    expect(options[0].text()).toBe("Custom");
  });

  it("renders region preset dropdown with Custom + all frequencies", () => {
    const wrapper = mountTransmitter();
    const options = wrapper.findAll("#regionPreset option");
    expect(options.length).toBe(1 + FREQUENCY_PRESETS.length);
  });

  it("renders antenna preset dropdown with Custom + all antennas", () => {
    const wrapper = mountTransmitter();
    const options = wrapper.findAll("#antennaPreset option");
    expect(options.length).toBe(1 + ANTENNA_PRESETS.length);
  });

  it("renders height preset dropdown with Custom + all heights", () => {
    const wrapper = mountTransmitter();
    const options = wrapper.findAll("#heightPreset option");
    expect(options.length).toBe(1 + HEIGHT_PRESETS.length);
  });

  it("renders color picker and auto checkbox", () => {
    const wrapper = mountTransmitter();
    expect(wrapper.find("#tx_color").exists()).toBe(true);
    expect(wrapper.find("#tx_color_auto").exists()).toBe(true);
  });

  it("renders 'Set with Map' and 'Center map' buttons", () => {
    const wrapper = mountTransmitter();
    expect(wrapper.find("#setWithMap").text()).toContain("Set with Map");
    const buttons = wrapper.findAll("button");
    const centerBtn = buttons.find((b) => b.text().includes("Center map"));
    expect(centerBtn).toBeDefined();
  });

  // -----------------------------------------------------------------------
  // v-model bindings
  // -----------------------------------------------------------------------

  it("updates store transmitter name on input", async () => {
    const wrapper = mountTransmitter();
    const store = useStore();
    await wrapper.find("#name").setValue("My Tower");
    expect(store.splatParams.transmitter.name).toBe("My Tower");
  });

  it("updates store latitude on input", async () => {
    const wrapper = mountTransmitter();
    const store = useStore();
    await wrapper.find("#tx_lat").setValue("45.5");
    expect(Number(store.splatParams.transmitter.tx_lat)).toBe(45.5);
  });

  // -----------------------------------------------------------------------
  // Hardware preset
  // -----------------------------------------------------------------------

  it("populates tx_power when hardware preset selected", async () => {
    const wrapper = mountTransmitter();
    const store = useStore();
    const nonCustom = HARDWARE_PRESETS.find((h) => !h.is_custom);
    if (!nonCustom) return;
    await wrapper.find("#hardwarePreset").setValue(nonCustom.name);
    await wrapper.vm.$nextTick();
    const expectedWatts = parseFloat(Math.pow(10, (nonCustom.max_power_dbm - 30) / 10).toFixed(4));
    expect(store.splatParams.transmitter.tx_power).toBeCloseTo(expectedWatts, 3);
  });

  it("disables tx_power field when hardware preset active", async () => {
    const wrapper = mountTransmitter();
    const nonCustom = HARDWARE_PRESETS.find((h) => !h.is_custom);
    if (!nonCustom) return;
    await wrapper.find("#hardwarePreset").setValue(nonCustom.name);
    await wrapper.vm.$nextTick();
    expect(wrapper.find<HTMLInputElement>("#tx_power").element.disabled).toBe(true);
  });

  it("enables tx_power when set to Custom", async () => {
    const wrapper = mountTransmitter();
    await wrapper.find("#hardwarePreset").setValue("");
    await wrapper.vm.$nextTick();
    expect(wrapper.find<HTMLInputElement>("#tx_power").element.disabled).toBe(false);
  });

  // -----------------------------------------------------------------------
  // Region preset
  // -----------------------------------------------------------------------

  it("populates tx_freq when region preset selected", async () => {
    const wrapper = mountTransmitter();
    const store = useStore();
    await wrapper.find("#regionPreset").setValue(FREQUENCY_PRESETS[0].code);
    await wrapper.vm.$nextTick();
    expect(store.splatParams.transmitter.tx_freq).toBe(FREQUENCY_PRESETS[0].frequency_mhz);
  });

  it("disables tx_freq when region preset active", async () => {
    const wrapper = mountTransmitter();
    await wrapper.find("#regionPreset").setValue(FREQUENCY_PRESETS[0].code);
    await wrapper.vm.$nextTick();
    expect(wrapper.find<HTMLInputElement>("#tx_freq").element.disabled).toBe(true);
  });

  // -----------------------------------------------------------------------
  // Antenna preset
  // -----------------------------------------------------------------------

  it("populates tx_gain when antenna preset selected", async () => {
    const wrapper = mountTransmitter();
    const store = useStore();
    await wrapper.find("#antennaPreset").setValue(ANTENNA_PRESETS[0].name);
    await wrapper.vm.$nextTick();
    expect(store.splatParams.transmitter.tx_gain).toBe(ANTENNA_PRESETS[0].gain_dbi);
  });

  it("shows mismatch loss badge when antenna preset selected", async () => {
    const wrapper = mountTransmitter();
    await wrapper.find("#antennaPreset").setValue(ANTENNA_PRESETS[0].name);
    await wrapper.vm.$nextTick();
    const badge = wrapper.find(".badge.bg-warning");
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toContain("dB");
  });

  it("hides mismatch loss badge when set to Custom", () => {
    const wrapper = mountTransmitter();
    expect(wrapper.find(".badge.bg-warning").exists()).toBe(false);
  });

  // -----------------------------------------------------------------------
  // Height preset
  // -----------------------------------------------------------------------

  it("populates tx_height when height preset selected", async () => {
    const wrapper = mountTransmitter();
    const store = useStore();
    await wrapper.find("#heightPreset").setValue(HEIGHT_PRESETS[0].label);
    await wrapper.vm.$nextTick();
    expect(store.splatParams.transmitter.tx_height).toBe(HEIGHT_PRESETS[0].height_m);
  });

  // -----------------------------------------------------------------------
  // Auto color toggle
  // -----------------------------------------------------------------------

  it("toggles auto color on checkbox change", async () => {
    const store = useStore();
    store.splatParams.transmitter.tx_color = "";
    const wrapper = mountTransmitter();
    const checkbox = wrapper.find("#tx_color_auto");
    await checkbox.trigger("change");
    // Was "" (auto), should now be "#4a90d9" (manual)
    expect(store.splatParams.transmitter.tx_color).toBe("#4a90d9");
  });
});
