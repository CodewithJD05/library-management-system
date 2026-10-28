
"use strict";

import { PAGE_SIZE } from "./config.js";
import { apiRequest } from "./api.js";
import { makeCell, makeEmptyRow, setMessage } from "./helpers.js";

const tableBody = document.getElementById("borrowings-table-body");
const message = document.getElementById("borrowings-message");
const countElement = document.getElementById("borrowings-count");
const overdueCountElement = document.getElementById("overdue-borrowings-count");
const filterSelect = document.getElementById("borrowing-filter");
const paginationInfo = document.getElementById("borrowings-pagination-info");
const previousButton = document.getElementById("previous-borrowings-page");
const nextButton = document.getElementById("next-borrowings-page");
const refreshButton = document.getElementById("refresh-borrowings");

// Issue book dialog
const issueBookButton = document.getElementById("show-issue-book");
const issueBookDialog = document.getElementById("issue-book-dialog");
const issueBookForm = document.getElementById("issue-book-form");
const issueMemberSelect = document.getElementById("issue-member");
const issueCopySelect = document.getElementById("issue-book-copy");
const issueBookError = document.getElementById("issue-book-error");
const saveIssueBookButton = document.getElementById("save-issue-book");
const cancelIssueBookButton = document.getElementById("cancel-issue-book");

// Extend due-date dialog
const dueDateDialog = document.getElementById("due-date-dialog");
const dueDateForm = document.getElementById("due-date-form");
const dueDateInput = document.getElementById("new-due-date");
const dueDateCurrent = document.getElementById("due-date-current");
const dueDateError = document.getElementById("due-date-error");
const saveDueDateButton = document.getElementById("save-due-date");

let currentPage = 0;
let currentRecords = [];
let selectedBorrowing = null;
let refreshDashboard = async () => {};
let loadingBorrowings = false;
let loadingIssueOptions = false;

export function setBorrowingsDashboardRefresh(callback) {
    refreshDashboard = callback;
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Invalid date";
    }

    return date.toLocaleString();
}

function getBorrowingStatus(borrowing) {
    if (borrowing.returned_at) {
        return "Returned";
    }

    if (borrowing.due_at && new Date(borrowing.due_at).getTime() < Date.now()) {
        return "Overdue";
    }

    return "Active";
}

function createStatusBadge(status) {
    const badge = document.createElement("span");
    badge.className = `status-badge status-${status.toLowerCase()}`;
    badge.textContent = status;
    return badge;
}

function createActionButton(label, className, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", handler);
    return button;
}

function updatePagination() {
    paginationInfo.textContent = `Page ${currentPage + 1}`;

    previousButton.disabled = currentPage === 0;
    nextButton.disabled = currentRecords.length < PAGE_SIZE;
}

function renderBorrowings(records) {
    currentRecords = records;
    countElement.textContent = records.length.toLocaleString();

    tableBody.replaceChildren();

    if (!records.length) {
        makeEmptyRow(tableBody, 7, "No borrowing records found.");
        updatePagination();
        return;
    }

    for (const borrowing of records) {
        const row = document.createElement("tr");

        row.appendChild(makeCell(borrowing.id));
        row.appendChild(makeCell(borrowing.member_id));
        row.appendChild(makeCell(borrowing.book_copy_id));
        row.appendChild(makeCell(formatDate(borrowing.borrowed_at)));
        row.appendChild(makeCell(formatDate(borrowing.due_at)));

        const statusCell = document.createElement("td");
        statusCell.appendChild(
            createStatusBadge(getBorrowingStatus(borrowing))
        );
        row.appendChild(statusCell);

        const actionsCell = document.createElement("td");
        actionsCell.className = "table-actions";

        if (!borrowing.returned_at) {
            actionsCell.appendChild(
                createActionButton("Return", "secondary-button", () =>
                    returnBorrowing(borrowing.id)
                )
            );

            actionsCell.appendChild(
                createActionButton("Extend", "secondary-button", () =>
                    openDueDateDialog(borrowing)
                )
            );
        } else {
            actionsCell.textContent = "—";
        }

        row.appendChild(actionsCell);
        tableBody.appendChild(row);
    }

    updatePagination();
}

export async function loadBorrowings() {
    if (!sessionStorage.getItem("access_token") || loadingBorrowings) {
        return;
    }

    loadingBorrowings = true;
    setMessage(message, "Loading borrowing records…");
    tableBody.setAttribute("aria-busy", "true");

    try {
        const params = new URLSearchParams({
            skip: String(currentPage * PAGE_SIZE),
            limit: String(PAGE_SIZE),
        });

        const filter = filterSelect.value;

        if (filter === "active") {
            params.set("active_only", "true");
        }

        if (filter === "overdue") {
            params.set("overdue_only", "true");
        }

        const [records, overdueCount] = await Promise.all([
            apiRequest(`/borrowings/?${params.toString()}`),
            apiRequest("/borrowings/overdue/count"),
        ]);

        if (!Array.isArray(records)) {
            throw new Error("Unexpected borrowing records response.");
        }

        renderBorrowings(records);

        const overdueTotal =
            typeof overdueCount === "number"
                ? overdueCount
                : Number(overdueCount.count ?? 0);

        overdueCountElement.textContent =
            overdueTotal.toLocaleString();

        setMessage(
            message,
            records.length
                ? `${records.length} borrowing record(s) loaded on this page.`
                : "No borrowing records found."
        );
    } catch (error) {
        setMessage(message, error.message, "error");
        makeEmptyRow(tableBody, 7, "Could not load borrowing records.");
        console.error("Failed to load borrowings:", error);
    } finally {
        loadingBorrowings = false;
        tableBody.removeAttribute("aria-busy");
    }
}

// -------------------- Issue a book --------------------

function setSelectPlaceholder(select, placeholder) {
    select.replaceChildren();

    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    option.disabled = true;
    option.selected = true;

    select.appendChild(option);
}

async function loadIssueOptions() {
    if (loadingIssueOptions) {
        return;
    }

    loadingIssueOptions = true;
    issueBookError.textContent = "";

    issueMemberSelect.disabled = true;
    issueCopySelect.disabled = true;

    setSelectPlaceholder(issueMemberSelect, "Loading members…");
    setSelectPlaceholder(issueCopySelect, "Loading available copies…");

    try {
        const [members, books] = await Promise.all([
            apiRequest("/members/?skip=0&limit=100"),
            apiRequest("/books/?skip=0&limit=100"),
        ]);

        if (!Array.isArray(members) || !Array.isArray(books)) {
            throw new Error("Unexpected members or books response.");
        }

        setSelectPlaceholder(issueMemberSelect, "Select a member");

        const activeMembers = members.filter((member) => member.is_active);

        for (const member of activeMembers) {
            const option = document.createElement("option");
            option.value = String(member.id);
            option.textContent = `${member.full_name} (ID: ${member.id})`;
            issueMemberSelect.appendChild(option);
        }

        if (activeMembers.length === 0) {
            setSelectPlaceholder(
                issueMemberSelect,
                "No active members available"
            );
        }

        setSelectPlaceholder(issueCopySelect, "Loading available copies…");

        // Load physical copies for each book, then keep only available copies.
        const copyResults = await Promise.all(
            books.map(async (book) => {
                try {
                    const copies = await apiRequest(
                        `/books/${book.id}/copies`
                    );

                    if (!Array.isArray(copies)) {
                        return [];
                    }

                    return copies
                        .filter(
                            (copy) =>
                                String(copy.status).toLowerCase() === "available"
                        )
                        .map((copy) => ({
                            ...copy,
                            bookTitle: book.title,
                        }));
                } catch (error) {
                    console.error(
                        `Could not load copies for book ${book.id}:`,
                        error
                    );
                    throw error;
                }
            })
        );

        const availableCopies = copyResults.flat();

        setSelectPlaceholder(issueCopySelect, "Select an available copy");

        for (const copy of availableCopies) {
            const option = document.createElement("option");
            option.value = String(copy.id);
            option.textContent =
                `${copy.bookTitle} — Barcode: ${copy.barcode} (Copy ID: ${copy.id})`;
            issueCopySelect.appendChild(option);
        }

        if (availableCopies.length === 0) {
            setSelectPlaceholder(
                issueCopySelect,
                "No available copies found"
            );
        }

        issueMemberSelect.disabled = activeMembers.length === 0;
        issueCopySelect.disabled = availableCopies.length === 0;

        if (activeMembers.length === 0 || availableCopies.length === 0) {
            issueBookError.textContent =
                activeMembers.length === 0
                    ? "Add or activate a member before issuing a book."
                    : "There are no available book copies to issue.";
        }
    } catch (error) {
        issueBookError.textContent =
            `Could not load issue options: ${error.message}`;
        console.error("Loading issue-book options failed:", error);
    } finally {
        loadingIssueOptions = false;
    }
}

function openIssueBookDialog() {
    issueBookForm.reset();
    issueBookError.textContent = "";
    saveIssueBookButton.disabled = false;
    saveIssueBookButton.textContent = "Issue book";

    issueBookDialog.showModal();
    loadIssueOptions();
}

issueBookButton.addEventListener("click", openIssueBookDialog);

cancelIssueBookButton.addEventListener("click", () => {
    issueBookDialog.close();
});

issueBookForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    issueBookError.textContent = "";

    const memberId = Number(issueMemberSelect.value);
    const bookCopyId = Number(issueCopySelect.value);

    if (!Number.isInteger(memberId) || memberId <= 0) {
        issueBookError.textContent = "Please select a member.";
        return;
    }

    if (!Number.isInteger(bookCopyId) || bookCopyId <= 0) {
        issueBookError.textContent = "Please select an available book copy.";
        return;
    }

    saveIssueBookButton.disabled = true;
    saveIssueBookButton.textContent = "Issuing…";

    try {
        await apiRequest("/borrowings/", {
            method: "POST",
            body: JSON.stringify({
                member_id: memberId,
                book_copy_id: bookCopyId,
            }),
        });

        issueBookDialog.close();
        issueBookForm.reset();

        currentPage = 0;
        filterSelect.value = "all";

        await loadBorrowings();
        await refreshDashboard();

        setMessage(
            message,
            `Book copy #${bookCopyId} issued to member #${memberId} successfully.`,
            "success"
        );
    } catch (error) {
        issueBookError.textContent = error.message;
        console.error("Issuing book failed:", error);
    } finally {
        saveIssueBookButton.disabled = false;
        saveIssueBookButton.textContent = "Issue book";
    }
});

// -------------------- Return a book --------------------

async function returnBorrowing(borrowingId) {
    if (!window.confirm(`Return borrowing #${borrowingId}?`)) {
        return;
    }

    try {
        await apiRequest(`/borrowings/${borrowingId}/return`, {
            method: "PUT",
        });

        currentPage = 0;

        await loadBorrowings();
        await refreshDashboard();

        setMessage(
            message,
            `Borrowing #${borrowingId} returned successfully.`,
            "success"
        );
    } catch (error) {
        setMessage(message, error.message, "error");
        console.error("Returning borrowing failed:", error);
    }
}

// -------------------- Extend due date --------------------

function toLocalDateTimeInput(value) {
    const date = new Date(value);
    const offset = date.getTimezoneOffset() * 60_000;

    return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function openDueDateDialog(borrowing) {
    selectedBorrowing = borrowing;
    dueDateError.textContent = "";

    dueDateCurrent.textContent =
        `Borrowing #${borrowing.id} — current due date: ${formatDate(borrowing.due_at)}`;

    dueDateInput.value = toLocalDateTimeInput(borrowing.due_at);
    dueDateInput.min = toLocalDateTimeInput(borrowing.due_at);

    dueDateDialog.showModal();
}

dueDateForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!selectedBorrowing) {
        return;
    }

    const newDate = new Date(dueDateInput.value);

    if (Number.isNaN(newDate.getTime())) {
        dueDateError.textContent = "Please enter a valid due date.";
        return;
    }

    if (
        newDate.getTime() <=
        new Date(selectedBorrowing.due_at).getTime()
    ) {
        dueDateError.textContent =
            "The new due date must be later than the current due date.";
        return;
    }

    saveDueDateButton.disabled = true;
    dueDateError.textContent = "";

    try {
        await apiRequest(
            `/borrowings/${selectedBorrowing.id}/due-date`,
            {
                method: "PATCH",
                body: JSON.stringify({
                    due_at: newDate.toISOString(),
                }),
            }
        );

        dueDateDialog.close();
        currentPage = 0;

        await loadBorrowings();
        await refreshDashboard();

        setMessage(message, "Due date updated successfully.", "success");
    } catch (error) {
        dueDateError.textContent = error.message;
    } finally {
        saveDueDateButton.disabled = false;
    }
});

// -------------------- Page controls --------------------

filterSelect.addEventListener("change", () => {
    currentPage = 0;
    loadBorrowings();
});

refreshButton.addEventListener("click", () => {
    loadBorrowings();
});

previousButton.addEventListener("click", () => {
    if (currentPage > 0) {
        currentPage -= 1;
        loadBorrowings();
    }
});

nextButton.addEventListener("click", () => {
    if (currentRecords.length === PAGE_SIZE) {
        currentPage += 1;
        loadBorrowings();
    }
});
