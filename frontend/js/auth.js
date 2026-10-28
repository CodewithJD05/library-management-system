
"use strict";

import { API_BASE_URL } from "./config.js";
import { clearToken } from "./api.js";

const loginScreen = document.getElementById("login-screen");
const dashboardScreen = document.getElementById("dashboard-screen");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const loginButton = document.getElementById("login-button");
const logoutButton = document.getElementById("logout-button");

export function showLogin() {
    loginScreen.hidden = false;
    dashboardScreen.hidden = true;
}

export function showApplication() {
    loginScreen.hidden = true;
    dashboardScreen.hidden = false;
}

window.addEventListener("auth-required", () => {
    showLogin();

    if (loginError) {
        loginError.textContent =
            "Your session is invalid or your account lacks access. Please sign in again.";
    }
});

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginError.textContent = "";
    loginButton.disabled = true;
    loginButton.textContent = "Signing in…";

    try {
        const formData = new FormData(loginForm);

        const body = new URLSearchParams({
            username: String(formData.get("username") || "").trim(),
            password: String(formData.get("password") || ""),
        });

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                Accept: "application/json",
            },
            body: body.toString(),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : "Login failed. Check your email and password."
            );
        }

        if (!data.access_token) {
            throw new Error("The server did not return an access token.");
        }

        sessionStorage.setItem("access_token", data.access_token);

        // app.js listens for this event to load application data.
        window.dispatchEvent(new Event("login-success"));
    } catch (error) {
        loginError.textContent = error.message || "Login failed.";
        console.error("Login failed:", error);
    } finally {
        loginButton.disabled = false;
        loginButton.textContent = "Sign in";
    }
});

logoutButton.addEventListener("click", () => {
    clearToken();
    loginForm.reset();
    loginError.textContent = "";
    showLogin();
});
