// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import MatrixConfig from "../../components/MatrixConfig.vue";
import { useStore } from "../../store";

describe("MatrixConfig.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // Default: mock fetch to return a config
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              hardware: ["v3", "v4"],
              antennas: ["bingfu_whip", "duck_stubby", "ribbed_spring_helical", "slinkdsco_omni"],
              terrain: ["bare_earth"],
            }),
        }),
      ),
    );
  });

  async function mountMatrixConfig() {
    const wrapper = mount(MatrixConfig);
    await flushPromises();
    return wrapper;
  }

  it("renders hardware checkboxes", async () => {
    const wrapper = await mountMatrixConfig();
    expect(wrapper.find("#hw-v3").exists()).toBe(true);
    expect(wrapper.find("#hw-v4").exists()).toBe(true);
  });

  it("renders antenna checkboxes", async () => {
    const wrapper = await mountMatrixConfig();
    expect(wrapper.find("#ant-bingfu_whip").exists()).toBe(true);
    expect(wrapper.find("#ant-duck_stubby").exists()).toBe(true);
    expect(wrapper.find("#ant-ribbed_spring_helical").exists()).toBe(true);
    expect(wrapper.find("#ant-slinkdsco_omni").exists()).toBe(true);
  });

  it("renders terrain checkboxes", async () => {
    const wrapper = await mountMatrixConfig();
    expect(wrapper.find("#ter-bare_earth").exists()).toBe(true);
  });

  it("initializes checkboxes from fetched config", async () => {
    const wrapper = await mountMatrixConfig();
    expect(wrapper.find<HTMLInputElement>("#hw-v3").element.checked).toBe(true);
    expect(wrapper.find<HTMLInputElement>("#hw-v4").element.checked).toBe(true);
  });

  it("sends PUT request when checkbox toggled", async () => {
    const store = useStore();
    store.adminToken = "test-token";
    const wrapper = await mountMatrixConfig();

    // Clear initial GET call
    vi.mocked(fetch).mockClear();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) } as Response);

    await wrapper.find("#hw-v3").trigger("change");
    await flushPromises();

    expect(fetch).toHaveBeenCalledWith("/matrix/config", expect.objectContaining({ method: "PUT" }));
  });

  it("PUT request includes Bearer token", async () => {
    const store = useStore();
    store.adminToken = "my-token-123";
    const wrapper = await mountMatrixConfig();

    vi.mocked(fetch).mockClear();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) } as Response);

    await wrapper.find("#hw-v3").trigger("change");
    await flushPromises();

    const callArgs = vi.mocked(fetch).mock.calls[0];
    const options = callArgs[1] as RequestInit;
    expect((options.headers as Record<string, string>)["Authorization"]).toBe("Bearer my-token-123");
  });

  it("PUT body converts config to arrays of enabled keys", async () => {
    const store = useStore();
    store.adminToken = "tok";
    const wrapper = await mountMatrixConfig();

    vi.mocked(fetch).mockClear();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) } as Response);

    // Toggle v3 off (it was checked)
    await wrapper.find("#hw-v3").trigger("change");
    await flushPromises();

    const callArgs = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((callArgs[1] as RequestInit).body as string);
    // v3 was toggled off, so only v4 should remain
    expect(body.hardware).not.toContain("v3");
    expect(body.hardware).toContain("v4");
  });

  it("shows 'Saved' badge after successful PUT", async () => {
    const store = useStore();
    store.adminToken = "tok";
    const wrapper = await mountMatrixConfig();

    vi.mocked(fetch).mockClear();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) } as Response);

    await wrapper.find("#hw-v3").trigger("change");
    await flushPromises();

    expect(wrapper.find(".badge.bg-success").exists()).toBe(true);
    expect(wrapper.find(".badge.bg-success").text()).toBe("Saved");
  });

  it("excludes derived terrain models (weighted_aggregate, worst_case)", async () => {
    const wrapper = await mountMatrixConfig();
    expect(wrapper.find("#ter-weighted_aggregate").exists()).toBe(false);
    expect(wrapper.find("#ter-worst_case").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Weighted Aggregate");
    expect(wrapper.text()).not.toContain("Worst Case");
  });

  it("renders correct labels from shared label maps", async () => {
    const wrapper = await mountMatrixConfig();
    expect(wrapper.text()).toContain("Heltec V3");
    expect(wrapper.text()).toContain("Heltec V4");
    expect(wrapper.text()).toContain("Bingfu Whip");
    expect(wrapper.text()).toContain("Bare Earth (SRTM)");
  });
});
