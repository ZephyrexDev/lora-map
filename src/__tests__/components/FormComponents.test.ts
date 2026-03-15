// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import Receiver from "../../components/Receiver.vue";
import Environment from "../../components/Environment.vue";
import Simulation from "../../components/Simulation.vue";
import { useStore } from "../../store";

// ---------------------------------------------------------------------------
// Receiver.vue
// ---------------------------------------------------------------------------
describe("Receiver.vue", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders sensitivity input with default -130", () => {
    const wrapper = mount(Receiver);
    expect(wrapper.find<HTMLInputElement>("#rx_sensitivity").element.value).toBe("-130");
  });

  it("renders height input with default 1", () => {
    const wrapper = mount(Receiver);
    expect(wrapper.find<HTMLInputElement>("#rx_height").element.value).toBe("1");
  });

  it("renders gain input with default 2", () => {
    const wrapper = mount(Receiver);
    expect(wrapper.find<HTMLInputElement>("#rx_gain").element.value).toBe("2");
  });

  it("renders loss input with default 2", () => {
    const wrapper = mount(Receiver);
    expect(wrapper.find<HTMLInputElement>("#rx_loss").element.value).toBe("2");
  });

  it("updates store on sensitivity change", async () => {
    const wrapper = mount(Receiver);
    const store = useStore();
    await wrapper.find("#rx_sensitivity").setValue("-120");
    // v-model with type=number may set string in jsdom; check coerced value
    expect(Number(store.splatParams.receiver.rx_sensitivity)).toBe(-120);
  });

  it("updates store on height change", async () => {
    const wrapper = mount(Receiver);
    const store = useStore();
    await wrapper.find("#rx_height").setValue("5");
    expect(Number(store.splatParams.receiver.rx_height)).toBe(5);
  });

  it("renders all four form fields", () => {
    const wrapper = mount(Receiver);
    expect(wrapper.findAll("input")).toHaveLength(4);
  });
});

// ---------------------------------------------------------------------------
// Environment.vue
// ---------------------------------------------------------------------------
describe("Environment.vue", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders radio climate select with default 'continental_temperate'", () => {
    const wrapper = mount(Environment);
    expect(wrapper.find<HTMLSelectElement>("#radio_climate").element.value).toBe("continental_temperate");
  });

  it("renders all 7 radio climate options", () => {
    const wrapper = mount(Environment);
    const options = wrapper.findAll("#radio_climate option");
    expect(options).toHaveLength(7);
  });

  it("renders polarization select with default 'vertical'", () => {
    const wrapper = mount(Environment);
    expect(wrapper.find<HTMLSelectElement>("#polarization").element.value).toBe("vertical");
  });

  it("renders clutter height input with default 1", () => {
    const wrapper = mount(Environment);
    expect(wrapper.find<HTMLInputElement>("#clutter_height").element.value).toBe("1");
  });

  it("renders ground dielectric input with default 15", () => {
    const wrapper = mount(Environment);
    expect(wrapper.find<HTMLInputElement>("#ground_dielectric").element.value).toBe("15");
  });

  it("renders ground conductivity input with default 0.005", () => {
    const wrapper = mount(Environment);
    expect(wrapper.find<HTMLInputElement>("#ground_conductivity").element.value).toBe("0.005");
  });

  it("renders atmospheric bending input with default 301", () => {
    const wrapper = mount(Environment);
    expect(wrapper.find<HTMLInputElement>("#atmosphere_bending").element.value).toBe("301");
  });

  it("updates store on radio climate change", async () => {
    const wrapper = mount(Environment);
    const store = useStore();
    await wrapper.find("#radio_climate").setValue("desert");
    expect(store.splatParams.environment.radio_climate).toBe("desert");
  });

  it("updates store on polarization change", async () => {
    const wrapper = mount(Environment);
    const store = useStore();
    await wrapper.find("#polarization").setValue("horizontal");
    expect(store.splatParams.environment.polarization).toBe("horizontal");
  });
});

// ---------------------------------------------------------------------------
// Simulation.vue
// ---------------------------------------------------------------------------
describe("Simulation.vue", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders situation fraction input with default 95", () => {
    const wrapper = mount(Simulation);
    expect(wrapper.find<HTMLInputElement>("#situation_fraction").element.value).toBe("95");
  });

  it("renders time fraction input with default 95", () => {
    const wrapper = mount(Simulation);
    expect(wrapper.find<HTMLInputElement>("#time_fraction").element.value).toBe("95");
  });

  it("renders simulation extent input with default 30", () => {
    const wrapper = mount(Simulation);
    expect(wrapper.find<HTMLInputElement>("#simulation_extent").element.value).toBe("30");
  });

  it("updates store on extent change", async () => {
    const wrapper = mount(Simulation);
    const store = useStore();
    await wrapper.find("#simulation_extent").setValue("50");
    expect(Number(store.splatParams.simulation.simulation_extent)).toBe(50);
  });

  it("has min=1 and max=100 on fraction inputs", () => {
    const wrapper = mount(Simulation);
    const sitInput = wrapper.find<HTMLInputElement>("#situation_fraction");
    expect(sitInput.element.min).toBe("1");
    expect(sitInput.element.max).toBe("100");
  });

  it("has min=1 and max=100 on extent input", () => {
    const wrapper = mount(Simulation);
    const extInput = wrapper.find<HTMLInputElement>("#simulation_extent");
    expect(extInput.element.min).toBe("1");
    expect(extInput.element.max).toBe("100");
  });
});
