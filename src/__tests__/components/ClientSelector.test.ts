// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import ClientSelector from "../../components/ClientSelector.vue";
import { useStore } from "../../store";

describe("ClientSelector.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // Stub fetch so loadMatrixConfig doesn't fail in jsdom
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              hardware: ["v3", "v4"],
              antennas: ["bingfu_whip", "slinkdsco_omni"],
              terrain: ["bare_earth", "dsm"],
            }),
        }),
      ),
    );
  });

  function mountWithConfig() {
    const store = useStore();
    // Pre-populate matrixConfig so the component doesn't need to fetch
    store.matrixConfig = {
      hardware: { v3: true, v4: true },
      antennas: { bingfu_whip: true, slinkdsco_omni: true, duck_stubby: false, ribbed_spring_helical: false },
      terrain: { bare_earth: true, dsm: true, lulc_clutter: false },
    };
    return mount(ClientSelector);
  }

  it("renders hardware select with enabled options", () => {
    const wrapper = mountWithConfig();
    const options = wrapper.findAll("#client-hardware option");
    expect(options).toHaveLength(2);
    expect(options[0].text()).toContain("Heltec V3");
    expect(options[1].text()).toContain("Heltec V4");
  });

  it("renders antenna select with enabled options only", () => {
    const wrapper = mountWithConfig();
    const options = wrapper.findAll("#client-antenna option");
    expect(options).toHaveLength(2);
    expect(options[0].text()).toContain("Bingfu Whip");
    expect(options[1].text()).toContain("Slinkdsco Omni");
  });

  it("renders terrain select with enabled options", () => {
    const wrapper = mountWithConfig();
    const options = wrapper.findAll("#client-terrain option");
    expect(options).toHaveLength(2);
  });

  it("defaults store.clientHardware to first enabled option if current is invalid", async () => {
    const store = useStore();
    store.clientHardware = "nonexistent";
    mountWithConfig();
    await Promise.resolve(); // flush onMounted
    expect(store.clientHardware).toBe("v3");
  });

  it("defaults store.clientAntenna to first enabled option if current is invalid", async () => {
    const store = useStore();
    store.clientAntenna = "nonexistent";
    mountWithConfig();
    await Promise.resolve();
    expect(store.clientAntenna).toBe("bingfu_whip");
  });

  it("preserves store.clientHardware if it is in the enabled list", async () => {
    const store = useStore();
    store.clientHardware = "v4";
    mountWithConfig();
    await Promise.resolve();
    expect(store.clientHardware).toBe("v4");
  });

  it("shows no pending message initially", () => {
    const wrapper = mountWithConfig();
    expect(wrapper.find(".text-warning").exists()).toBe(false);
  });

  it("updates store.clientHardware on select change", async () => {
    const wrapper = mountWithConfig();
    const store = useStore();
    await wrapper.find("#client-hardware").setValue("v4");
    expect(store.clientHardware).toBe("v4");
  });

  it("renders labels from shared label maps", () => {
    const wrapper = mountWithConfig();
    expect(wrapper.text()).toContain("Heltec V3");
    expect(wrapper.text()).toContain("Bingfu Whip");
  });
});
