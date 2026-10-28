
"use strict";

export function setMessage(element, message, type = "") {
    if (!element) return;

    element.textContent = message;
    element.className = `page-message ${type}`.trim();
}

export function makeCell(value) {
    const cell = document.createElement("td");

    cell.textContent =
        value === null || value === undefined || value === ""
            ? "—"
            : String(value);

    return cell;
}

export function makeEmptyRow(tableBody, columnCount, message) {
    if (!tableBody) return;

    const row = document.createElement("tr");
    const cell = document.createElement("td");

    cell.colSpan = columnCount;
    cell.className = "empty-state";
    cell.textContent = message;

    row.appendChild(cell);
    tableBody.replaceChildren(row);
}

export function formatStatus(status) {
    return String(status || "unknown")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function createStatusBadge(status) {
    const badge = document.createElement("span");
    const normalizedStatus = String(status || "unknown").toLowerCase();

    badge.className = `status-badge status-${normalizedStatus}`;
    badge.textContent = formatStatus(status);

    return badge;
}
