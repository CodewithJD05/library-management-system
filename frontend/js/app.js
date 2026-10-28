
"use strict";

import { API_BASE_URL } from "./config.js";
import { getToken } from "./api.js";
import { showLogin, showApplication } from "./auth.js";
import { loadDashboardSummary } from "./dashboard.js";

import {
    loadBooks,
    setDashboardRefresh,
} from "./books.js";

import {
    loadMembers,
    setMembersDashboardRefresh,
} from "./members.js";

import {
    loadBorrowings,
    setBorrowingsDashboardRefresh,
} from "./borrowings.js";

import {
    loadFines,
    setFinesDashboardRefresh,
} from "./fines.js";

import {
    loadStaff,
    setStaffDashboardRefresh,
} from "./staff.js";

// ---------- Application elements ----------

const loginScreen = document.getElementById("login-screen");
const dashboardScreen = document.getElementById("dashboard-screen");

const apiDot = document.getElementById("api-dot");
const apiStatus = document.getElementById("api-status");
const backendDot = document.getElementById("backend-dot");
const backendHealth = document.getElementById("backend-health");
const systemMessage = document.getElementById("system-message");

const dashboardPage = document.getElementById("dashboard-page");
const booksPage = document.getElementById("books-page");
const membersPage = document.getElementById("members-page");
const borrowingsPage = document.getElementById("borrowings-page");
const finesPage = document.getElementById("fines-page");
const staffPage = document.getElementById("staff-page");

// ---------- API health ----------

async function checkApiConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`, {
            headers: {
                Accept: "application/json",
            },
        });

        if (!response.ok) {
            throw new Error(
                `Health endpoint returned HTTP ${response.status}`
            );
        }

        await response.json();

        setApiStatus(true, "FastAPI is responding.");

        return true;
    } catch (error) {
        setApiStatus(
            false,
            "Cannot reach FastAPI. Start the backend and refresh this page."
        );

        console.error("API connection failed:", error);

        return false;
    }
}

function setApiStatus(isOnline, message) {
    apiDot?.classList.toggle("online", isOnline);
    apiDot?.classList.toggle("offline", !isOnline);

    if (apiStatus) {
        apiStatus.textContent = isOnline
            ? "Connected"
            : "Unavailable";
    }

    backendDot?.classList.toggle("online", isOnline);
    backendDot?.classList.toggle("offline", !isOnline);

    if (backendHealth) {
        backendHealth.textContent = isOnline ? "Online" : "Offline";
        backendHealth.className =
            `status-text ${isOnline ? "good" : "bad"}`;
    }

    if (systemMessage) {
        systemMessage.textContent = message;
    }
}

// ---------- Navigation ----------

const pages = {
    Dashboard: dashboardPage,
    Books: booksPage,
    Members: membersPage,
    Borrowings: borrowingsPage,
    Fines: finesPage,
    Staff: staffPage,
};

async function navigateTo(pageName) {
    const selectedPage = pages[pageName];

    if (!selectedPage) {
        console.error(`Page "${pageName}" is not registered.`);
        return;
    }

    document.querySelectorAll(".app-page").forEach((page) => {
        page.hidden = true;
    });

    selectedPage.hidden = false;

    document.querySelectorAll(".nav-item[data-page]").forEach((item) => {
        item.classList.toggle(
            "active",
            item.dataset.page === pageName
        );
    });

    try {
        switch (pageName) {
            case "Dashboard":
                await loadDashboardSummary();
                break;

            case "Books":
                await loadBooks();
                break;

            case "Members":
                await loadMembers();
                break;

            case "Borrowings":
                await loadBorrowings();
                break;

            case "Fines":
                await loadFines();
                break;

            case "Staff":
                await loadStaff();
                break;

            default:
                console.warn(`No loader configured for "${pageName}".`);
        }
    } catch (error) {
        console.error(`Failed to load ${pageName} page:`, error);
    }
}

document.querySelectorAll("[data-page]").forEach((element) => {
    element.addEventListener("click", (event) => {
        event.preventDefault();

        const pageName = element.dataset.page;

        if (pageName) {
            void navigateTo(pageName);
        }
    });
});

// ---------- Shared dialog closing ----------

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
        const dialog = document.getElementById(
            button.dataset.closeDialog
        );

        if (dialog?.open) {
            dialog.close();
        }
    });
});

// ---------- Shared refresh callbacks ----------

setDashboardRefresh(loadDashboardSummary);
setMembersDashboardRefresh(loadDashboardSummary);
setBorrowingsDashboardRefresh(loadDashboardSummary);
setFinesDashboardRefresh(loadDashboardSummary);
setStaffDashboardRefresh(loadDashboardSummary);

// ---------- Login success ----------

window.addEventListener("login-success", async () => {
    showApplication();

    await loadDashboardSummary();
    await loadBooks();
});

// ---------- Authorization handling ----------

window.addEventListener("authorization-denied", (event) => {
    window.alert(
        event.detail?.message ||
        "You are not authorized to access this page."
    );

    void navigateTo("Dashboard");
});

// ---------- Initialization ----------

async function initializeApplication() {
    showLogin();

    const apiIsAvailable = await checkApiConnection();

    if (!apiIsAvailable) {
        return;
    }

    if (getToken()) {
        showApplication();

        await loadDashboardSummary();
        await loadBooks();
    }
}

void initializeApplication();
