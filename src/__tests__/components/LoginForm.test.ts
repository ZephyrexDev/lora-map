// @vitest-environment jsdom
import "../setup";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import LoginForm from "../../components/LoginForm.vue";
import { useStore } from "../../store";

describe("LoginForm.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function mountLoginForm() {
    return mount(LoginForm);
  }

  it("renders login form when not admin", () => {
    const wrapper = mountLoginForm();
    expect(wrapper.find("#passwordInput").exists()).toBe(true);
    expect(wrapper.find("button[type='submit']").text()).toContain("Login");
  });

  it("renders modal title 'Admin Login' when not admin", () => {
    const wrapper = mountLoginForm();
    expect(wrapper.find("#loginModalLabel").text()).toBe("Admin Login");
  });

  it("renders 'Logged In' title and logout button when admin", () => {
    const store = useStore();
    store.isAdmin = true;
    const wrapper = mountLoginForm();
    expect(wrapper.find("#loginModalLabel").text()).toBe("Logged In");
    expect(wrapper.text()).toContain("You are logged in as admin");
    expect(wrapper.find("button.btn-outline-danger").text()).toContain("Logout");
  });

  it("hides login form when admin", () => {
    const store = useStore();
    store.isAdmin = true;
    const wrapper = mountLoginForm();
    expect(wrapper.find("#passwordInput").exists()).toBe(false);
  });

  it("binds password input to local ref via v-model", async () => {
    const wrapper = mountLoginForm();
    const input = wrapper.find<HTMLInputElement>("#passwordInput");
    await input.setValue("secret123");
    expect(input.element.value).toBe("secret123");
  });

  it("calls store.login with password on submit", async () => {
    const store = useStore();
    store.login = vi.fn().mockResolvedValue(false);
    const wrapper = mountLoginForm();
    await wrapper.find("#passwordInput").setValue("mypass");
    await wrapper.find("form").trigger("submit");
    expect(store.login).toHaveBeenCalledWith("mypass");
  });

  it("shows error message on failed login", async () => {
    const store = useStore();
    store.login = vi.fn().mockResolvedValue(false);
    const wrapper = mountLoginForm();
    await wrapper.find("#passwordInput").setValue("wrong");
    await wrapper.find("form").trigger("submit");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".alert-danger").text()).toContain("Invalid password");
  });

  it("clears error on new submit attempt", async () => {
    const store = useStore();
    store.login = vi.fn().mockResolvedValue(false);
    const wrapper = mountLoginForm();

    // First failed attempt
    await wrapper.find("#passwordInput").setValue("wrong");
    await wrapper.find("form").trigger("submit");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".alert-danger").exists()).toBe(true);

    // Second attempt — error should clear during submission
    store.login = vi.fn().mockResolvedValue(true);
    await wrapper.find("form").trigger("submit");
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".alert-danger").exists()).toBe(false);
  });

  it("disables login button while loading", async () => {
    const store = useStore();
    // Never resolve to keep loading state
    store.login = vi.fn().mockReturnValue(new Promise(() => {}));
    const wrapper = mountLoginForm();
    await wrapper.find("#passwordInput").setValue("test");
    await wrapper.find("form").trigger("submit");
    await wrapper.vm.$nextTick();
    expect(wrapper.find<HTMLButtonElement>("button[type='submit']").element.disabled).toBe(true);
  });

  it("calls store.logout when logout button clicked", async () => {
    const store = useStore();
    store.isAdmin = true;
    store.logout = vi.fn();
    const wrapper = mountLoginForm();
    await wrapper.find("button.btn-outline-danger").trigger("click");
    expect(store.logout).toHaveBeenCalled();
  });
});
