
"use strict";

import { PAGE_SIZE } from "./config.js";
import { apiRequest } from "./api.js";
import {
    setMessage,
    makeCell,
    makeEmptyRow,
    createStatusBadge,
} from "./helpers.js";

const membersPage = document.getElementById("members-page");
const membersTableBody = document.getElementById("members-table-body");
const membersMessage = document.getElementById("members-message");
const memberSearchForm = document.getElementById("member-search-form");
const memberSearchInput = document.getElementById("member-search");
const clearMemberSearchButton = document.getElementById("clear-member-search");
const previousMembersPageButton = document.getElementById("previous-members-page");
const nextMembersPageButton = document.getElementById("next-members-page");
const membersPaginationInfo = document.getElementById("members-pagination-info");
const membersCount = document.getElementById("members-count");
const activeMembersCount = document.getElementById("active-members-count");

const memberDialog = document.getElementById("member-dialog");
const memberForm = document.getElementById("member-form");
const memberDialogTitle = document.getElementById("member-dialog-title");
const memberFormError = document.getElementById("member-form-error");
const saveMemberButton = document.getElementById("save-member-button");

const memberHistoryDialog = document.getElementById("member-history-dialog");
const memberHistoryTitle = document.getElementById("member-history-title");
const memberHistorySubtitle = document.getElementById("member-history-subtitle");
const memberHistoryMessage = document.getElementById("member-history-message");
const memberHistoryTableBody = document.getElementById("member-history-table-body");

const membersState = {
    search: "",
    skip: 0,
    limit: PAGE_SIZE,
    currentPageCount: 0,
    editingMemberId: null,
    loading: false,
};

let refreshDashboard = async () => {};

export function setMembersDashboardRefresh(callback) {
    refreshDashboard = callback;
}

export async function loadMembers() {
    if (!sessionStorage.getItem("access_token") || membersState.loading) {
        return;
    }

    membersState.loading = true;
    setMessage(membersMessage, "Loading members…");
    makeEmptyRow(membersTableBody, 7, "Loading members…");

    const query = new URLSearchParams({
        skip: String(membersState.skip),
        limit: String(membersState.limit),
    });

    if (membersState.search) {
        query.set("search", membersState.search);
    }

    try {
        const members = await apiRequest(`/members/?${query.toString()}`);

        if (!Array.isArray(members)) {
            throw new Error("Unexpected members response from the server.");
        }

        renderMembers(members);
        membersState.currentPageCount = members.length;

        const pageNumber = Math.floor(membersState.skip / PAGE_SIZE) + 1;

        membersPaginationInfo.textContent = `Page ${pageNumber}`;
        previousMembersPageButton.disabled = membersState.skip === 0;
        nextMembersPageButton.disabled = members.length < PAGE_SIZE;

        membersCount.textContent = members.length.toLocaleString();

        activeMembersCount.textContent = members
            .filter((member) => member.is_active)
            .length.toLocaleString();

        setMessage(
            membersMessage,
            members.length
                ? `${members.length} member(s) loaded on this page.`
                : "No members found."
        );
    } catch (error) {
        makeEmptyRow(membersTableBody, 7, "Could not load members.");
        setMessage(membersMessage, error.message, "error");
        console.error("Loading members failed:", error);
    } finally {
        membersState.loading = false;
    }
}

function renderMembers(members) {
    membersTableBody.replaceChildren();

    if (members.length === 0) {
        makeEmptyRow(membersTableBody, 7, "No members found.");
        return;
    }

    members.forEach((member) => {
        const row = document.createElement("tr");

        // Member ID
        row.appendChild(makeCell(member.id));

        // Member name
        const nameCell = document.createElement("td");
        const name = document.createElement("strong");

        name.textContent = member.full_name;
        nameCell.appendChild(name);
        row.appendChild(nameCell);

        row.appendChild(makeCell(member.email));
        row.appendChild(makeCell(member.phone || "—"));

        const statusCell = document.createElement("td");
        statusCell.appendChild(
            createStatusBadge(member.is_active ? "active" : "inactive")
        );
        row.appendChild(statusCell);

        row.appendChild(
            makeCell(
                member.created_at
                    ? new Date(member.created_at).toLocaleDateString()
                    : "—"
            )
        );

        const actionsCell = document.createElement("td");
        actionsCell.className = "table-actions";

        // Edit button
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "table-button";
        editButton.textContent = "Edit";
        editButton.addEventListener("click", () => openMemberDialog(member));

        // Activate/deactivate button
        const statusButton = document.createElement("button");
        statusButton.type = "button";
        statusButton.className = "table-button";
        statusButton.textContent = member.is_active ? "Deactivate" : "Activate";
        statusButton.addEventListener("click", () => toggleMemberStatus(member));

        // Borrowing history button
        const historyButton = document.createElement("button");
        historyButton.type = "button";
        historyButton.className = "table-button";
        historyButton.textContent = "History";
        historyButton.addEventListener("click", () => openMemberHistory(member));

        // Delete button
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "table-button";
        deleteButton.textContent = "Delete";

        deleteButton.addEventListener("click", async () => {
            const confirmed = window.confirm(
                `Delete member "${member.full_name}" (ID: ${member.id})?\n\n` +
                "Members with borrowing history cannot be deleted."
            );

            if (!confirmed) {
                return;
            }

            deleteButton.disabled = true;

            try {
                await apiRequest(`/members/${member.id}`, {
                    method: "DELETE",
                });

                setMessage(
                    membersMessage,
                    `Member "${member.full_name}" deleted successfully.`,
                    "success"
                );

                // If the last row on a later page was deleted, go back a page.
                if (
                    membersState.skip > 0 &&
                    members.length === 1
                ) {
                    membersState.skip = Math.max(
                        0,
                        membersState.skip - PAGE_SIZE
                    );
                }

                await loadMembers();
                await refreshDashboard();
            } catch (error) {
                setMessage(membersMessage, error.message, "error");
                console.error("Deleting member failed:", error);
            } finally {
                deleteButton.disabled = false;
            }
        });

        actionsCell.append(
            editButton,
            statusButton,
            historyButton,
            deleteButton
        );

        row.appendChild(actionsCell);
        membersTableBody.appendChild(row);
    });
}

function openMemberDialog(member = null) {
    memberForm.reset();
    memberFormError.textContent = "";

    membersState.editingMemberId = member ? member.id : null;

    memberDialogTitle.textContent = member ? "Edit member" : "Add a member";
    saveMemberButton.textContent = member ? "Save changes" : "Save member";

    if (member) {
        memberForm.elements.full_name.value = member.full_name || "";
        memberForm.elements.email.value = member.email || "";
        memberForm.elements.phone.value = member.phone || "";
    }

    memberDialog.showModal();
}

document.getElementById("show-add-member").addEventListener("click", () => {
    openMemberDialog();
});

memberForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    memberFormError.textContent = "";
    saveMemberButton.disabled = true;
    saveMemberButton.textContent = "Saving…";

    const formData = new FormData(memberForm);

    const payload = {
        full_name: String(formData.get("full_name") || "").trim(),
        email: String(formData.get("email") || "").trim(),
        phone: String(formData.get("phone") || "").trim() || null,
    };

    const isEditing = membersState.editingMemberId !== null;

    const path = isEditing
        ? `/members/${membersState.editingMemberId}`
        : "/members/";

    try {
        await apiRequest(path, {
            method: isEditing ? "PUT" : "POST",
            body: JSON.stringify(payload),
        });

        memberDialog.close();
        memberForm.reset();

        membersState.skip = 0;

        await loadMembers();
        await refreshDashboard();

        setMessage(
            membersMessage,
            isEditing
                ? "Member updated successfully."
                : "Member added successfully.",
            "success"
        );
    } catch (error) {
        memberFormError.textContent = error.message;
        console.error("Saving member failed:", error);
    } finally {
        saveMemberButton.disabled = false;
        saveMemberButton.textContent = "Save member";
    }
});

async function toggleMemberStatus(member) {
    const nextStatus = !member.is_active;
    const action = nextStatus ? "activate" : "deactivate";

    if (
        !window.confirm(
            `Are you sure you want to ${action} ${member.full_name}?`
        )
    ) {
        return;
    }

    try {
        await apiRequest(`/members/${member.id}/status`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: nextStatus }),
        });

        await loadMembers();
        await refreshDashboard();

        setMessage(
            membersMessage,
            `Member ${nextStatus ? "activated" : "deactivated"} successfully.`,
            "success"
        );
    } catch (error) {
        setMessage(membersMessage, error.message, "error");
        console.error("Updating member status failed:", error);
    }
}

async function openMemberHistory(member) {
    memberHistoryTitle.textContent = "Borrowing history";
    memberHistorySubtitle.textContent =
        `${member.full_name} · ${member.email}`;

    setMessage(memberHistoryMessage, "Loading borrowing history…");
    makeEmptyRow(memberHistoryTableBody, 5, "Loading history…");

    memberHistoryDialog.showModal();

    try {
        const history = await apiRequest(
            `/members/${member.id}/borrowings?skip=0&limit=100`
        );

        if (!Array.isArray(history)) {
            throw new Error("Unexpected borrowing history response.");
        }

        memberHistoryTableBody.replaceChildren();

        if (history.length === 0) {
            makeEmptyRow(
                memberHistoryTableBody,
                5,
                "No borrowing history found."
            );
        } else {
            history.forEach((loan) => {
                const row = document.createElement("tr");

                row.appendChild(makeCell(loan.id));
                row.appendChild(makeCell(loan.book_copy_id));

                row.appendChild(
                    makeCell(
                        loan.borrowed_at
                            ? new Date(loan.borrowed_at).toLocaleString()
                            : "—"
                    )
                );

                row.appendChild(
                    makeCell(
                        loan.due_at
                            ? new Date(loan.due_at).toLocaleString()
                            : "—"
                    )
                );

                row.appendChild(
                    makeCell(
                        loan.returned_at
                            ? new Date(loan.returned_at).toLocaleString()
                            : "Not returned"
                    )
                );

                memberHistoryTableBody.appendChild(row);
            });
        }

        setMessage(
            memberHistoryMessage,
            `${history.length} borrowing record(s) loaded.`
        );
    } catch (error) {
        makeEmptyRow(
            memberHistoryTableBody,
            5,
            "Could not load borrowing history."
        );

        setMessage(memberHistoryMessage, error.message, "error");
        console.error("Loading borrowing history failed:", error);
    }
}

// Search by member name or numeric ID
memberSearchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    membersState.search = memberSearchInput.value.trim();
    membersState.skip = 0;

    loadMembers();
});

clearMemberSearchButton.addEventListener("click", () => {
    memberSearchInput.value = "";
    membersState.search = "";
    membersState.skip = 0;

    loadMembers();
});

previousMembersPageButton.addEventListener("click", () => {
    if (membersState.skip === 0) return;

    membersState.skip = Math.max(0, membersState.skip - PAGE_SIZE);
    loadMembers();
});

nextMembersPageButton.addEventListener("click", () => {
    if (membersState.currentPageCount < PAGE_SIZE) return;

    membersState.skip += PAGE_SIZE;
    loadMembers();
});
