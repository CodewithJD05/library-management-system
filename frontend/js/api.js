
"use strict";

import { API_BASE_URL } from "./config.js";

export function getToken() {
    return sessionStorage.getItem("access_token");
}

export function clearToken() {
    sessionStorage.removeItem("access_token");
}

export async function apiRequest(path, options = {}) {
    const token = getToken();

    if (!token) {
        clearToken();
        window.dispatchEvent(new Event("auth-required"));
        throw new Error("Your session has expired. Please sign in again.");
    }

    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    headers.set("Authorization", `Bearer ${token}`);

    if (
        options.body !== undefined &&
        options.body !== null &&
        !(options.body instanceof FormData) &&
        !headers.has("Content-Type")
    ) {
        headers.set("Content-Type", "application/json");
    }

    const requestOptions = {
        ...options,
        headers,
    };

    if (
        options.body !== undefined &&
        options.body !== null &&
        !(options.body instanceof FormData)
    ) {
        requestOptions.body =
            typeof options.body === "string"
                ? options.body
                : JSON.stringify(options.body);
    }

    let response;

    try {
        response = await fetch(
            `${API_BASE_URL}${path}`,
            requestOptions
        );
    } catch (error) {
        console.error("API network error:", error);

        throw new Error(
            "Could not connect to FastAPI. Check that the backend is running."
        );
    }

    if (response.status === 401) {
        clearToken();
        window.dispatchEvent(new Event("auth-required"));
        throw new Error("Your session has expired. Please sign in again.");
    }

    if (response.status === 403) {
        const error = new Error(
            "You are not authorized to access this page."
        );

        window.dispatchEvent(
            new CustomEvent("authorization-denied", {
                detail: { message: error.message },
            })
        );

        throw error;
    }

    // Read the response body once. A successful DELETE may have no body.
    const responseText = await response.text();
    let data = null;

    if (responseText.trim()) {
        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            try {
                data = JSON.parse(responseText);
            } catch {
                if (response.ok) {
                    throw new Error("The server returned invalid JSON.");
                }
            }
        } else {
            data = responseText;
        }
    }

    if (!response.ok) {
        let message = `Request failed with HTTP ${response.status}.`;

        if (typeof data?.detail === "string") {
            message = data.detail;
        } else if (Array.isArray(data?.detail)) {
            message = data.detail
                .map((item) => item.msg || "Invalid input")
                .join("; ");
        }

        throw new Error(message);
    }

    return data;
}
