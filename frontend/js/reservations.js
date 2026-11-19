"use strict";
import { apiRequest } from "./api.js";
const form = document.getElementById("reservation-form");
const body = document.getElementById("reservations-body");
const message = document.getElementById("reservation-message");

export async function loadReservations() {
    if (!body) return;
    body.replaceChildren();
    try {
        const rows = await apiRequest("/reservations/?limit=100");
        for (const reservation of rows) {
            const tr = document.createElement("tr");
            for (const value of [reservation.id, reservation.book_id, reservation.member_id,
                reservation.book_copy_id ?? "—", reservation.status,
                reservation.expires_at ? new Date(reservation.expires_at).toLocaleString() : "—"]) {
                const td = document.createElement("td");
                td.textContent = String(value);
                tr.appendChild(td);
            }
            const cell = document.createElement("td");
            if (["waiting", "ready"].includes(reservation.status)) {
                const button = document.createElement("button");
                button.type = "button";button.className = "secondary-button";button.textContent = "Cancel";
                button.addEventListener("click", async () => {
                    if (!window.confirm("Cancel this reservation?")) return;
                    try { await apiRequest(`/reservations/${reservation.id}/cancel`, { method: "POST" }); await loadReservations(); }
                    catch (e) { message.textContent = e.message; }
                });
                cell.appendChild(button);
            }
            tr.appendChild(cell);body.appendChild(tr);
        }
        if (!rows.length) { const tr=document.createElement("tr");const td=document.createElement("td");td.colSpan=7;td.textContent="No reservations yet.";tr.appendChild(td);body.appendChild(tr); }
    } catch (error) { message.textContent = error.message; }
}
form?.addEventListener("submit", async event => {
    event.preventDefault();
    const data = new FormData(form);
    try {
        await apiRequest("/reservations/", { method: "POST", body: { book_id: Number(data.get("book_id")), member_id: Number(data.get("member_id")) } });
        message.textContent = "Reservation created.";form.reset();await loadReservations();
    } catch (error) { message.textContent = error.message; }
});
document.getElementById("refresh-reservations")?.addEventListener("click", () => void loadReservations());
