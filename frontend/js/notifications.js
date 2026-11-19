"use strict";
import { apiRequest } from "./api.js";
const body=document.getElementById("notifications-body");
const message=document.getElementById("notifications-message");
export async function loadNotifications() {
    if (!body) return;
    body.replaceChildren();
    try {
        const [summary, list] = await Promise.all([
            apiRequest("/notifications/summary"), apiRequest("/notifications/?limit=100")
        ]);
        message.textContent = `Queued: ${summary.pending} · Sent: ${summary.sent} · Failed: ${summary.failed} · SMTP: ${summary.smtp_configured ? "Configured" : "Not configured"}`;
        for (const item of list) {
            const tr=document.createElement("tr");
            for (const value of [item.event_key,item.recipient,item.subject,item.status,item.attempts]) {
                const td=document.createElement("td");td.textContent=value;tr.appendChild(td);
            }
            body.appendChild(tr);
        }
    } catch(e) { message.textContent=e.message; }
}
document.getElementById("refresh-notifications")?.addEventListener("click", () => void loadNotifications());
document.getElementById("send-notifications")?.addEventListener("click", async () => {
    try { await apiRequest("/notifications/dispatch",{method:"POST"});message.textContent="Dispatch requested.";await loadNotifications(); }
    catch(e) { message.textContent=e.message; }
});
