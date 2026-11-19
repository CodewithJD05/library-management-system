"use strict";
import { apiRequest, clearToken } from "./api.js";
const body=document.getElementById("sessions-body");
const message=document.getElementById("sessions-message");
export async function loadSessions() {
    if (!body) return;
    body.replaceChildren();
    try {
        const sessions=await apiRequest("/auth/sessions");
        for (const session of sessions) {
            const tr=document.createElement("tr");
            for (const value of [session.id.slice(0,8),new Date(session.created_at).toLocaleString(),
                                  new Date(session.expires_at).toLocaleString(), session.revoked_at ? "Yes" : "No"]) {
                const td=document.createElement("td");td.textContent=value;tr.appendChild(td);
            }
            const td=document.createElement("td");
            if (!session.revoked_at) {
                const button=document.createElement("button");button.className="secondary-button";button.textContent="Revoke";
                button.addEventListener("click", async () => {
                    if (!window.confirm("Revoke this session?")) return;
                    try { await apiRequest(`/auth/sessions/${session.id}`, { method: "DELETE" });await loadSessions(); }
                    catch (error) { message.textContent=error.message; }
                });td.appendChild(button);
            }
            tr.appendChild(td);body.appendChild(tr);
        }
    } catch (e) { message.textContent=e.message; }
}
document.getElementById("refresh-sessions")?.addEventListener("click", () => void loadSessions());
document.getElementById("logout-all-sessions")?.addEventListener("click", async () => {
    if (!window.confirm("Sign out from every device, including this one?")) return;
    try { await apiRequest("/auth/logout-all", { method: "POST" }); }
    catch (e) { console.warn("Remote sign-out request failed",e); }
    clearToken();window.dispatchEvent(new Event("auth-required"));
});
