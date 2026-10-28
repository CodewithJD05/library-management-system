
"use strict";

import { apiRequest } from "./api.js";

function setMetric(id, value) {
    const element = document.getElementById(id);

    if (element && value !== undefined && value !== null) {
        element.textContent = Number(value).toLocaleString();
    }
}

function setMetricMessage(message) {
    ["total-books", "total-copies", "active-members", "active-loans"]
        .forEach((id) => {
            const element = document.getElementById(id);
            if (element) element.textContent = message;
        });
}

export async function loadDashboardSummary() {
    setMetricMessage("…");

    try {
        const data = await apiRequest("/dashboard/summary");

        setMetric("total-books", data.total_books);
        setMetric("total-copies", data.total_copies);
        setMetric("active-members", data.active_members);
        setMetric("active-loans", data.active_loans);

        const systemMessage = document.getElementById("system-message");

        if (systemMessage) {
            systemMessage.textContent =
                `${Number(data.available_copies ?? 0).toLocaleString()} copies available; ` +
                `${Number(data.overdue_loans ?? 0).toLocaleString()} loans overdue.`;
        }
    } catch (error) {
        if (sessionStorage.getItem("access_token")) {
            const systemMessage = document.getElementById("system-message");

            if (systemMessage) {
                systemMessage.textContent = error.message;
            }

            console.error("Dashboard request failed:", error);
        }
    }
}
