"use strict";
import { apiRequest } from "./api.js";
const form = document.getElementById("holiday-form");
const body = document.getElementById("holidays-body");
const message = document.getElementById("holiday-message");

export async function loadHolidays() {
    if (!body) return;
    body.replaceChildren();
    try {
        const policy = await apiRequest("/holidays/policy");
        const policyElement = document.getElementById("fine-policy-summary");
        if (policyElement) policyElement.textContent = `Daily rates — Student: ₹${policy.student_daily_fine} | Faculty: ₹${policy.faculty_daily_fine} | Time zone: ${policy.library_timezone}`;
        const rows = await apiRequest("/holidays/");
        for (const holiday of rows) {
            const tr = document.createElement("tr");
            for (const value of [holiday.day, holiday.name]) {
                const td=document.createElement("td");td.textContent=value;tr.appendChild(td);
            }
            const td=document.createElement("td");const button=document.createElement("button");
            button.type="button";button.className="secondary-button";button.textContent="Delete";
            button.addEventListener("click", async () => {
                if (!window.confirm(`Remove ${holiday.name} from the fine holiday calendar?`)) return;
                try { await apiRequest(`/holidays/${holiday.id}`, { method: "DELETE" }); await loadHolidays(); }
                catch (e) { message.textContent=e.message; }
            });
            td.appendChild(button);tr.appendChild(td);body.appendChild(tr);
        }
        if (!rows.length) { const tr=document.createElement("tr");const td=document.createElement("td");td.colSpan=3;td.textContent="No configured holidays.";tr.appendChild(td);body.appendChild(tr); }
    } catch (error) { message.textContent=error.message; }
}
form?.addEventListener("submit", async event => {
    event.preventDefault();const data=new FormData(form);
    try { await apiRequest("/holidays/", { method: "POST", body: { day: data.get("day"), name: data.get("name") } });
        form.reset();message.textContent="Holiday added.";await loadHolidays(); }
    catch (error) { message.textContent=error.message; }
});
