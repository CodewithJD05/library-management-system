
"use strict";

import { PAGE_SIZE } from "./config.js";
import { apiRequest } from "./api.js";
import { makeCell, makeEmptyRow, setMessage } from "./helpers.js";

const tableBody = document.getElementById("fines-table-body");
const message = document.getElementById("fines-message");
const filterSelect = document.getElementById("fine-filter");
const countElement = document.getElementById("fines-count");
const paginationInfo = document.getElementById("fines-pagination-info");
const previousButton = document.getElementById("previous-fines-page");
const nextButton = document.getElementById("next-fines-page");

let currentPage = 0;
let currentRecords = [];
let refreshDashboard = async () => {};

export function setFinesDashboardRefresh(callback) {
    refreshDashboard = callback;
}

function formatAmount(value) {
    return Number(value ?? 0).toLocaleString("en-IN", {
        style: "currency",
        currency: "INR",
    });
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function getMemberId(fine) {
    return fine.member_id ?? fine.borrowing?.member_id ?? "—";
}

function getBorrowingId(fine) {
    return fine.borrowing_id ?? fine.borrowing?.id ?? "—";
}

function isFinePaid(fine) {
    return fine.is_paid === true || fine.status === "paid" ||
        fine.paid_at != null;
}

function createActionButton(label, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button";
    button.textContent = label;
    button.addEventListener("click", handler);
    return button;
}

function updateSummary(summary) {
    const totalElement = document.getElementById("total-fines-amount");
    const unpaidElement = document.getElementById("unpaid-fines-amount");
    const paidElement = document.getElementById("paid-fines-amount");

    if (totalElement) totalElement.textContent = formatAmount(summary.total_amount);
    if (unpaidElement) unpaidElement.textContent = formatAmount(summary.unpaid_amount);
    if (paidElement) paidElement.textContent = formatAmount(summary.paid_amount);
}

function renderFines(records) {
    currentRecords = records;
    countElement.textContent = records.length.toLocaleString();

    if (!records.length) {
        makeEmptyRow(tableBody, 7, "No fine records found.");
        return;
    }

    tableBody.replaceChildren();

    for (const fine of records) {
        const row = document.createElement("tr");
        const paid = isFinePaid(fine);

        row.appendChild(makeCell(fine.id));
        row.appendChild(makeCell(getBorrowingId(fine)));
        row.appendChild(makeCell(getMemberId(fine)));
        row.appendChild(makeCell(formatAmount(fine.amount)));

        const statusCell = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `status-badge status-${paid ? "paid" : "unpaid"}`;
        badge.textContent = paid ? "Paid" : "Unpaid";
        statusCell.appendChild(badge);
        row.appendChild(statusCell);

        row.appendChild(makeCell(formatDate(fine.created_at)));

        const actionsCell = document.createElement("td");

        if (!paid) {
            actionsCell.appendChild(
                createActionButton("Mark paid", () => markFinePaid(fine.id))
            );
        } else {
            actionsCell.textContent = "—";
        }

        row.appendChild(actionsCell);
        tableBody.appendChild(row);
    }
}

function updatePagination(total) {
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    paginationInfo.textContent = `Page ${currentPage + 1} of ${totalPages}`;
    previousButton.disabled = currentPage === 0;
    nextButton.disabled = currentPage + 1 >= totalPages;
}

export async function loadFines() {
    setMessage(message, "Loading fine records…");
    tableBody.setAttribute("aria-busy", "true");

    try {
        const params = new URLSearchParams({
            skip: String(currentPage * PAGE_SIZE),
            limit: String(PAGE_SIZE),
        });

        if (filterSelect.value === "unpaid") {
            params.set("unpaid_only", "true");
        }

        const [records, summary] = await Promise.all([
            apiRequest(`/fines/?${params.toString()}`),
            apiRequest("/fines/summary"),
        ]);

        renderFines(records);
        updateSummary(summary);

        // This count is the number of records loaded on the current page.
        // Pagination is updated based on the API page size.
        const hasNextPage = records.length === PAGE_SIZE;
        const estimatedTotal = currentPage * PAGE_SIZE +
            records.length + (hasNextPage ? 1 : 0);

        updatePagination(estimatedTotal);
        setMessage(message, "");
    } catch (error) {
        setMessage(message, error.message, "error");
        makeEmptyRow(tableBody, 7, "Could not load fine records.");
        console.error("Failed to load fines:", error);
    } finally {
        tableBody.removeAttribute("aria-busy");
    }
}

async function markFinePaid(fineId) {
    if (!window.confirm(`Mark fine #${fineId} as paid?`)) return;

    try {
        await apiRequest(`/fines/${fineId}/pay`, {
            method: "PUT",
        });

        setMessage(message, `Fine #${fineId} marked as paid.`, "success");
        await loadFines();
        await refreshDashboard();
    } catch (error) {
        setMessage(message, error.message, "error");
    }
}

filterSelect.addEventListener("change", () => {
    currentPage = 0;
    loadFines();
});

document.getElementById("refresh-fines").addEventListener("click", loadFines);

previousButton.addEventListener("click", () => {
    if (currentPage > 0) {
        currentPage -= 1;
        loadFines();
    }
});

nextButton.addEventListener("click", () => {
    if (currentRecords.length === PAGE_SIZE) {
        currentPage += 1;
        loadFines();
    }
});
