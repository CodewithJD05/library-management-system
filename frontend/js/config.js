"use strict";
// Local VS Code Live Server (5500) -> local FastAPI. Hosted frontend -> hosted FastAPI.
const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost"]);
export const API_BASE_URL = LOCAL_HOSTS.has(window.location.hostname)
    ? "http://127.0.0.1:8000"
    : "https://library-management-system-gq50.onrender.com";
export const PAGE_SIZE = 10;
