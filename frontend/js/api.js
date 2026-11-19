"use strict";
import { API_BASE_URL } from "./config.js";

let refreshInProgress = null;
let authEpoch = 0;

export function getToken() { return sessionStorage.getItem("access_token"); }
export function getRefreshToken() { return sessionStorage.getItem("refresh_token"); }
export function saveTokens(data) {
    if (!data.access_token || !data.refresh_token) throw new Error("Token pair missing from response");
    sessionStorage.setItem("access_token", data.access_token);
    sessionStorage.setItem("refresh_token", data.refresh_token);
}
export function clearToken() {
    authEpoch++;
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
}

async function refreshAccess() {
    if (refreshInProgress) return refreshInProgress;
    const refresh = getRefreshToken();
    if (!refresh) throw new Error("Session has expired");
    const epoch = authEpoch;
    refreshInProgress = (async () => {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!response.ok) throw new Error("Session expired. Please sign in again.");
        const pair = await response.json();
        if (epoch !== authEpoch) throw new Error("Session was signed out");
        saveTokens(pair);
        return pair.access_token;
    })();
    try { return await refreshInProgress; }
    finally { refreshInProgress = null; }
}

function forceLogin() {
    clearToken();
    window.dispatchEvent(new Event("auth-required"));
}

export async function apiRequest(path, options = {}) {
    let token = getToken();
    if (!token) {
        try { token = await refreshAccess(); }
        catch { forceLogin(); throw new Error("Your session has expired. Please sign in again."); }
    }
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.body != null && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
    const prepared = { ...options, headers };
    if (options.body != null && !(options.body instanceof FormData)) {
        prepared.body = typeof options.body === "string" ? options.body : JSON.stringify(options.body);
    }
    let response;
    try {
        headers.set("Authorization", `Bearer ${token}`);
        response = await fetch(`${API_BASE_URL}${path}`, prepared);
        if (response.status === 401) {
            token = await refreshAccess();
            headers.set("Authorization", `Bearer ${token}`);
            response = await fetch(`${API_BASE_URL}${path}`, prepared);
        }
    } catch (error) {
        if (/session/i.test(error.message)) {
            forceLogin();
            throw new Error("Your session has expired. Please sign in again.");
        }
        throw new Error("Could not connect to FastAPI. Check that the backend is running.");
    }
    if (response.status === 401) {
        forceLogin();
        throw new Error("Your session has expired. Please sign in again.");
    }
    if (response.status === 403) {
        const error = new Error("You are not authorized to perform this action.");
        window.dispatchEvent(new CustomEvent("authorization-denied", { detail: { message: error.message } }));
        throw error;
    }
    const text = await response.text();
    let data = null;
    if (text.trim()) {
        if ((response.headers.get("content-type") || "").includes("application/json")) {
            try { data = JSON.parse(text); }
            catch { if (response.ok) throw new Error("Server returned invalid JSON."); }
        } else data = text;
    }
    if (!response.ok) {
        let message = `Request failed with HTTP ${response.status}.`;
        if (typeof data?.detail === "string") message = data.detail;
        else if (Array.isArray(data?.detail)) message = data.detail.map(x => x.msg || "Invalid input").join("; ");
        throw new Error(message);
    }
    return data;
}
