
"use strict";

import { PAGE_SIZE } from "./config.js";
import { apiRequest } from "./api.js";
import {
    setMessage,
    makeCell,
    makeEmptyRow,
    createStatusBadge,
} from "./helpers.js";

// ---------- State ----------

let currentPage = 0;
let staffList = [];
let dashboardRefreshCallback = null;
let isLoading = false;

// ---------- DOM elements ----------

const staffTableBody = document.getElementById("staff-table-body");
const staffMessage = document.getElementById("staff-message");
const staffCount = document.getElementById("staff-count");
const activeStaffCount = document.getElementById("active-staff-count");
const refreshStaffButton = document.getElementById("refresh-staff");

const staffDialog = document.getElementById("staff-dialog");
const staffForm = document.getElementById("staff-form");
const staffDialogTitle = document.getElementById("staff-dialog-title");
const staffIdInput = document.getElementById("staff-id");
const staffNameInput = document.getElementById("staff-name");
const staffEmailInput = document.getElementById("staff-email");
const staffPasswordInput = document.getElementById("staff-password");
const staffRoleInput = document.getElementById("staff-role");
const staffFormError = document.getElementById("staff-form-error");
const saveStaffButton = document.getElementById("save-staff-button");

const createStaffButton = document.getElementById("create-staff-button");
const closeStaffButton = document.getElementById("close-staff-dialog");
const cancelStaffButton = document.getElementById("cancel-staff-dialog");
const previousStaffButton = document.getElementById("previous-staff-page");
const nextStaffButton = document.getElementById("next-staff-page");
const paginationInfo = document.getElementById("staff-pagination-info");

// ---------- Helpers ----------

function isStaffActive(staff) {
    return staff.is_active === true;
}

function updateStaffMetrics() {
    if (staffCount) {
        staffCount.textContent = String(staffList.length);
    }

    if (activeStaffCount) {
        activeStaffCount.textContent = String(
            staffList.filter(isStaffActive).length
        );
    }
}

function showTableMessage(message) {
    if (!staffTableBody) {
        return;
    }

    makeEmptyRow(staffTableBody, 6, message);
}

function updatePagination() {
    if (paginationInfo) {
        paginationInfo.textContent =
            `Page ${currentPage + 1} · ${staffList.length} staff account(s)`;
    }

    if (previousStaffButton) {
        previousStaffButton.disabled =
            currentPage === 0 || isLoading;
    }

    if (nextStaffButton) {
        nextStaffButton.disabled =
            staffList.length < PAGE_SIZE || isLoading;
    }
}

// ---------- Render staff ----------

function renderStaff() {
    if (!staffTableBody) {
        console.error("Staff table body was not found in the HTML.");
        return;
    }

    staffTableBody.replaceChildren();

    if (staffList.length === 0) {
        showTableMessage("No staff accounts found.");
        updateStaffMetrics();
        return;
    }

    for (const staff of staffList) {
        const row = document.createElement("tr");

        row.appendChild(makeCell(staff.id));
        row.appendChild(makeCell(staff.full_name));
        row.appendChild(makeCell(staff.email));
        row.appendChild(makeCell(staff.role));

        const statusCell = document.createElement("td");
        statusCell.appendChild(
            createStatusBadge(
                isStaffActive(staff) ? "Active" : "Inactive"
            )
        );
        row.appendChild(statusCell);

        const actionsCell = document.createElement("td");
        actionsCell.className = "table-actions";

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "secondary-button";
        editButton.textContent = "Edit";

        editButton.addEventListener("click", () => {
            openEditDialog(staff);
        });

        const statusButton = document.createElement("button");
        statusButton.type = "button";
        statusButton.className = "secondary-button";
        statusButton.textContent = isStaffActive(staff)
            ? "Deactivate"
            : "Activate";

        statusButton.addEventListener("click", () => {
            void toggleStaffStatus(staff, statusButton);
        });

        actionsCell.append(editButton, statusButton);
        row.appendChild(actionsCell);
        staffTableBody.appendChild(row);
    }

    updateStaffMetrics();
}

// ---------- Load staff ----------

export async function loadStaff() {
    if (isLoading) {
        return;
    }

    isLoading = true;

    if (refreshStaffButton) {
        refreshStaffButton.disabled = true;
    }

    updatePagination();
    setMessage(staffMessage, "Loading staff accounts…", "info");
    showTableMessage("Loading staff accounts…");

    try {
        const staff = await apiRequest(
            `/staff/?skip=${currentPage * PAGE_SIZE}&limit=${PAGE_SIZE}`
        );

        if (!Array.isArray(staff)) {
            throw new Error(
                "The staff API returned an unexpected response."
            );
        }

        staffList = staff;

        renderStaff();
        updatePagination();

        setMessage(
            staffMessage,
            staffList.length === 0
                ? "No staff accounts found."
                : "Staff accounts loaded successfully.",
            "success"
        );
    } catch (error) {
        staffList = [];
        updateStaffMetrics();
        showTableMessage("Could not load staff accounts.");

        setMessage(
            staffMessage,
            error.message || "Failed to load staff accounts.",
            "error"
        );

        console.error("Loading staff accounts failed:", error);
    } finally {
        isLoading = false;

        if (refreshStaffButton) {
            refreshStaffButton.disabled = false;
        }

        updatePagination();
    }
}

// ---------- Create staff ----------

function openCreateDialog() {
    if (!staffDialog || !staffForm) {
        return;
    }

    staffForm.reset();

    staffIdInput.value = "";
    staffPasswordInput.required = true;
    staffPasswordInput.placeholder = "";
    staffDialogTitle.textContent = "Create Staff Account";
    staffFormError.textContent = "";

    staffDialog.showModal();
}

// ---------- Edit staff ----------

function openEditDialog(staff) {
    if (!staffDialog || !staffForm) {
        return;
    }

    staffForm.reset();

    staffIdInput.value = String(staff.id);
    staffNameInput.value = staff.full_name || "";
    staffEmailInput.value = staff.email || "";
    staffRoleInput.value = staff.role || "librarian";

    staffPasswordInput.value = "";
    staffPasswordInput.required = false;
    staffPasswordInput.placeholder =
        "Leave blank to keep current password";

    staffDialogTitle.textContent = "Edit Staff Account";
    staffFormError.textContent = "";

    staffDialog.showModal();
}

// ---------- Save staff ----------

async function saveStaff(event) {
    event.preventDefault();

    if (!staffForm) {
        return;
    }

    staffFormError.textContent = "";

    const staffId = staffIdInput.value.trim();
    const password = staffPasswordInput.value;

    const payload = {
        full_name: staffNameInput.value.trim(),
        email: staffEmailInput.value.trim(),
        role: staffRoleInput.value,
    };

    if (password) {
        if (password.length < 12) {
            staffFormError.textContent =
                "Password must contain at least 12 characters.";
            return;
        }

        payload.password = password;
    }

    if (!staffId && !password) {
        staffFormError.textContent =
            "A password of at least 12 characters is required.";
        return;
    }

    if (saveStaffButton) {
        saveStaffButton.disabled = true;
        saveStaffButton.textContent = "Saving…";
    }

    try {
        if (staffId) {
            await apiRequest(`/staff/${staffId}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });
        } else {
            await apiRequest("/staff/", {
                method: "POST",
                body: JSON.stringify(payload),
            });
        }

        staffDialog.close();
        currentPage = 0;

        await loadStaff();

        if (dashboardRefreshCallback) {
            await dashboardRefreshCallback();
        }
    } catch (error) {
        staffFormError.textContent =
            error.message || "Failed to save staff account.";

        console.error("Saving staff account failed:", error);
    } finally {
        if (saveStaffButton) {
            saveStaffButton.disabled = false;
            saveStaffButton.textContent = "Save staff";
        }
    }
}

// ---------- Activate / deactivate ----------

async function toggleStaffStatus(staff, button) {
    const action = isStaffActive(staff) ? "deactivate" : "activate";

    const confirmed = window.confirm(
        `Are you sure you want to ${action} ${staff.full_name}'s account?`
    );

    if (!confirmed) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(`/staff/${staff.id}/status`, {
            method: "PATCH",
            body: JSON.stringify({
                is_active: !staff.is_active,
            }),
        });

        await loadStaff();

        if (dashboardRefreshCallback) {
            await dashboardRefreshCallback();
        }
    } catch (error) {
        setMessage(
            staffMessage,
            error.message || `Failed to ${action} staff account.`,
            "error"
        );

        console.error(`Failed to ${action} staff account:`, error);
    } finally {
        button.disabled = false;
    }
}

// ---------- Dialog closing ----------

function closeStaffDialog() {
    if (staffDialog?.open) {
        staffDialog.close();
    }
}

// ---------- Dashboard refresh callback ----------

export function setStaffDashboardRefresh(callback) {
    dashboardRefreshCallback = callback;
}

// ---------- Event listeners ----------

refreshStaffButton?.addEventListener("click", () => {
    void loadStaff();
});

createStaffButton?.addEventListener("click", openCreateDialog);
closeStaffButton?.addEventListener("click", closeStaffDialog);
cancelStaffButton?.addEventListener("click", closeStaffDialog);

staffForm?.addEventListener("submit", saveStaff);

previousStaffButton?.addEventListener("click", async () => {
    if (currentPage > 0 && !isLoading) {
        currentPage--;
        await loadStaff();
    }
});

nextStaffButton?.addEventListener("click", async () => {
    if (staffList.length === PAGE_SIZE && !isLoading) {
        currentPage++;
        await loadStaff();
    }
});
