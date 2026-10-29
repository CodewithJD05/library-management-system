
"use strict";

import { PAGE_SIZE } from "./config.js";
import { apiRequest } from "./api.js";
import {
    setMessage,
    makeCell,
    makeEmptyRow,
    createStatusBadge,
} from "./helpers.js";

const booksTableBody = document.getElementById("books-table-body");
const booksMessage = document.getElementById("books-message");
const bookSearchForm = document.getElementById("book-search-form");
const bookSearchInput = document.getElementById("book-search");
const clearSearchButton = document.getElementById("clear-search");
const previousPageButton = document.getElementById("previous-page");
const nextPageButton = document.getElementById("next-page");
const paginationInfo = document.getElementById("pagination-info");
const booksCount = document.getElementById("books-count");
const copiesCount = document.getElementById("copies-count");

const addBookDialog = document.getElementById("add-book-dialog");
const addBookForm = document.getElementById("add-book-form");
const addBookError = document.getElementById("add-book-error");
const saveBookButton = document.getElementById("save-book-button");

const copiesDialog = document.getElementById("copies-dialog");
const copiesDialogTitle = document.getElementById("copies-dialog-title");
const copiesDialogSubtitle = document.getElementById("copies-dialog-subtitle");
const copiesTableBody = document.getElementById("copies-table-body");
const copiesMessage = document.getElementById("copies-message");
const addCopyForm = document.getElementById("add-copy-form");
const addCopyError = document.getElementById("add-copy-error");
const addCopyButton = document.getElementById("add-copy-button");

const editBookDialog = document.getElementById("edit-book-dialog");
const editBookForm = document.getElementById("edit-book-form");
const editBookError = document.getElementById("edit-book-error");
const saveEditBookButton = document.getElementById("save-edit-book");
const closeEditBookButton = document.getElementById("close-edit-book");
const cancelEditBookButton = document.getElementById("cancel-edit-book");

let editingBookId = null;

// app.js registers this callback to refresh dashboard metrics.
let refreshDashboard = async () => {};

export function setDashboardRefresh(callback) {
    refreshDashboard = callback;
}

const catalogueState = {
    search: "",
    skip: 0,
    limit: PAGE_SIZE,
    currentPageCount: 0,
    currentBookId: null,
    currentBookTitle: "",
    loading: false,
};

export async function loadBooks() {
    if (
        !sessionStorage.getItem("access_token") ||
        catalogueState.loading
    ) {
        return;
    }

    catalogueState.loading = true;
    setMessage(booksMessage, "Loading catalogue…");
    makeEmptyRow(booksTableBody, 6, "Loading books…");

    const query = new URLSearchParams({
        skip: String(catalogueState.skip),
        limit: String(catalogueState.limit),
    });

    if (catalogueState.search) {
        query.set("search", catalogueState.search);
    }

    try {
        const books = await apiRequest(`/books/?${query.toString()}`);

        if (!Array.isArray(books)) {
            throw new Error("Unexpected catalogue response from the server.");
        }

        renderBooks(books);
        catalogueState.currentPageCount = books.length;

        const pageNumber =
            Math.floor(catalogueState.skip / PAGE_SIZE) + 1;

        paginationInfo.textContent = `Page ${pageNumber}`;
        previousPageButton.disabled = catalogueState.skip === 0;
        nextPageButton.disabled = books.length < PAGE_SIZE;

        booksCount.textContent = books.length.toLocaleString();

        setMessage(
            booksMessage,
            books.length
                ? `${books.length} book(s) loaded on this page.`
                : "No books found. Try a different search or add a book."
        );
    } catch (error) {
        makeEmptyRow(booksTableBody, 6, "Could not load the catalogue.");
        setMessage(booksMessage, error.message, "error");
        console.error("Loading books failed:", error);
    } finally {
        catalogueState.loading = false;
    }
}

function renderBooks(books) {
    booksTableBody.replaceChildren();

    if (books.length === 0) {
        makeEmptyRow(booksTableBody, 6, "No books found.");
        return;
    }

    books.forEach((book) => {
        const row = document.createElement("tr");

        // Book ID
        row.appendChild(makeCell(book.id));

        // Title and description
        const titleCell = document.createElement("td");
        const title = document.createElement("strong");

        title.className = "book-title";
        title.textContent = book.title || "Untitled";
        titleCell.appendChild(title);

        if (book.description) {
            const description = document.createElement("small");
            description.className = "book-description";
            description.textContent = book.description;
            titleCell.appendChild(description);
        }

        row.appendChild(titleCell);

        // ISBN and publication year
        row.appendChild(makeCell(book.isbn));
        row.appendChild(makeCell(book.published_year));

        // Physical copies
        const countCell = makeCell("Open to view");
        countCell.className = "copy-count-cell";
        row.appendChild(countCell);

        // Actions
        const actionsCell = document.createElement("td");

        // Edit button
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "table-button";
        editButton.textContent = "Edit";

        editButton.addEventListener("click", () => {
            openEditBookDialog(book);
        });

        // View copies button
        const copiesButton = document.createElement("button");
        copiesButton.type = "button";
        copiesButton.className = "table-button";
        copiesButton.textContent = "View copies";

        copiesButton.addEventListener("click", () => {
            openCopiesDialog(book);
        });

        // Delete book button
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "table-button";
        deleteButton.textContent = "Delete";

        deleteButton.addEventListener("click", async () => {
            const confirmed = window.confirm(
                `Delete "${book.title}" (ID: ${book.id})?\n\n` +
                "Books with physical copies cannot be deleted."
            );

            if (!confirmed) return;

            deleteButton.disabled = true;
            deleteButton.textContent = "Deleting…";

            try {
                await apiRequest(`/books/${book.id}`, {
                    method: "DELETE",
                });

                setMessage(
                    booksMessage,
                    `Book "${book.title}" deleted successfully.`,
                    "success"
                );

                // If the last item on a page was deleted, move back one page.
                if (
                    catalogueState.skip > 0 &&
                    catalogueState.currentPageCount === 1
                ) {
                    catalogueState.skip = Math.max(
                        0,
                        catalogueState.skip - PAGE_SIZE
                    );
                }

                await loadBooks();
                await refreshDashboard();
            } catch (error) {
                setMessage(booksMessage, error.message, "error");
            } finally {
                deleteButton.disabled = false;
                deleteButton.textContent = "Delete";
            }
        });

        actionsCell.append(
            editButton,
            copiesButton,
            deleteButton
        );

        row.appendChild(actionsCell);
        booksTableBody.appendChild(row);
    });
}

// Search by title or ISBN.
bookSearchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    catalogueState.search = bookSearchInput.value.trim();
    catalogueState.skip = 0;

    loadBooks();
});

clearSearchButton.addEventListener("click", () => {
    bookSearchInput.value = "";
    catalogueState.search = "";
    catalogueState.skip = 0;

    loadBooks();
});

// Pagination
previousPageButton.addEventListener("click", () => {
    if (catalogueState.skip === 0) return;

    catalogueState.skip = Math.max(
        0,
        catalogueState.skip - PAGE_SIZE
    );

    loadBooks();
});

nextPageButton.addEventListener("click", () => {
    if (catalogueState.currentPageCount < PAGE_SIZE) return;

    catalogueState.skip += PAGE_SIZE;
    loadBooks();
});

// Add book dialog
document.getElementById("show-add-book").addEventListener("click", () => {
    addBookForm.reset();
    addBookError.textContent = "";
    addBookDialog.showModal();
});

addBookForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    addBookError.textContent = "";
    saveBookButton.disabled = true;
    saveBookButton.textContent = "Saving…";

    const formData = new FormData(addBookForm);
    const title = String(formData.get("title") || "").trim();
    const isbn = String(formData.get("isbn") || "").trim();
    const yearValue = String(
        formData.get("published_year") || ""
    ).trim();
    const description = String(
        formData.get("description") || ""
    ).trim();

    const payload = {
        title,
        isbn,
        published_year: yearValue ? Number(yearValue) : null,
        description: description || null,
    };

    try {
        await apiRequest("/books/", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        addBookDialog.close();
        addBookForm.reset();

        catalogueState.skip = 0;
        await loadBooks();
        await refreshDashboard();

        setMessage(booksMessage, "Book added successfully.", "success");
    } catch (error) {
        addBookError.textContent = error.message;
        console.error("Creating book failed:", error);
    } finally {
        saveBookButton.disabled = false;
        saveBookButton.textContent = "Save book";
    }
});

// Edit book dialog
async function openEditBookDialog(book) {
    try {
        const details = await apiRequest(`/books/${book.id}`);

        editingBookId = details.id;

        editBookForm.elements.title.value = details.title ?? "";
        editBookForm.elements.isbn.value = details.isbn ?? "";
        editBookForm.elements.published_year.value =
            details.published_year ?? "";
        editBookForm.elements.description.value =
            details.description ?? "";

        editBookError.textContent = "";
        editBookDialog.showModal();
    } catch (error) {
        setMessage(booksMessage, error.message, "error");
    }
}

closeEditBookButton.addEventListener("click", () => {
    editBookDialog.close();
});

cancelEditBookButton.addEventListener("click", () => {
    editBookDialog.close();
});

editBookDialog.addEventListener("close", () => {
    editingBookId = null;
    editBookForm.reset();
    editBookError.textContent = "";
});

editBookForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (editingBookId === null) return;

    editBookError.textContent = "";
    saveEditBookButton.disabled = true;
    saveEditBookButton.textContent = "Saving…";

    const formData = new FormData(editBookForm);
    const year = String(
        formData.get("published_year") || ""
    ).trim();

    const payload = {
        title: String(formData.get("title") || "").trim(),
        isbn: String(formData.get("isbn") || "").trim(),
        published_year: year ? Number(year) : null,
        description:
            String(formData.get("description") || "").trim() || null,
    };

    try {
        await apiRequest(`/books/${editingBookId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });

        editBookDialog.close();

        setMessage(booksMessage, "Book updated successfully.", "success");

        await loadBooks();
        await refreshDashboard();
    } catch (error) {
        editBookError.textContent = error.message;
        console.error("Updating book failed:", error);
    } finally {
        saveEditBookButton.disabled = false;
        saveEditBookButton.textContent = "Save changes";
    }
});

// Physical copies dialog
async function openCopiesDialog(book) {
    catalogueState.currentBookId = book.id;
    catalogueState.currentBookTitle = book.title || "Book";

    copiesDialogTitle.textContent = "Physical copies";
    copiesDialogSubtitle.textContent =
        `${catalogueState.currentBookTitle} · ISBN ${book.isbn || "—"}`;

    addCopyForm.reset();
    addCopyError.textContent = "";
    setMessage(copiesMessage, "");
    makeEmptyRow(copiesTableBody, 4, "Loading copies…");

    copiesDialog.showModal();
    await loadCopies(book.id);
}

async function loadCopies(bookId) {
    try {
        const copies = await apiRequest(`/books/${bookId}/copies`);

        if (!Array.isArray(copies)) {
            throw new Error("Unexpected copies response from the server.");
        }

        copiesTableBody.replaceChildren();

        if (copies.length === 0) {
            makeEmptyRow(
                copiesTableBody,
                4,
                "No physical copies have been added yet."
            );
        } else {
            copies.forEach((copy) => {
                const row = document.createElement("tr");

                row.appendChild(makeCell(copy.id));
                row.appendChild(makeCell(copy.barcode));

                const statusCell = document.createElement("td");
                statusCell.appendChild(createStatusBadge(copy.status));
                row.appendChild(statusCell);

                const actionsCell = document.createElement("td");
                const deleteButton = document.createElement("button");

                deleteButton.type = "button";
                deleteButton.className = "table-button";
                deleteButton.textContent = "Delete";

                deleteButton.addEventListener("click", async () => {
                    const confirmed = window.confirm(
                        `Delete physical copy "${copy.barcode}" (ID: ${copy.id})?\n\n` +
                        "Copies with borrowing history cannot be deleted."
                    );

                    if (!confirmed) return;

                    deleteButton.disabled = true;
                    deleteButton.textContent = "Deleting…";

                    try {
                        await apiRequest(
                            `/books/${bookId}/copies/${copy.id}`,
                            { method: "DELETE" }
                        );

                        await loadCopies(bookId);
                        await loadBooks();
                        await refreshDashboard();

                        setMessage(
                            copiesMessage,
                            `Physical copy "${copy.barcode}" deleted successfully.`,
                            "success"
                        );
                    } catch (error) {
                        setMessage(copiesMessage, error.message, "error");
                        deleteButton.disabled = false;
                        deleteButton.textContent = "Delete";
                    }
                });

                actionsCell.appendChild(deleteButton);
                row.appendChild(actionsCell);
                copiesTableBody.appendChild(row);
            });
        }

        setMessage(
            copiesMessage,
            `${copies.length} physical copy/copies found.`
        );
    } catch (error) {
        makeEmptyRow(
            copiesTableBody,
            4,
            "Could not load physical copies."
        );
        setMessage(copiesMessage, error.message, "error");
        console.error("Loading copies failed:", error);
    }
}

// Add physical copy
addCopyForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const bookId = catalogueState.currentBookId;
    if (!bookId) return;

    addCopyError.textContent = "";
    addCopyButton.disabled = true;
    addCopyButton.textContent = "Adding…";

    const barcode = document
        .getElementById("new-copy-barcode")
        .value.trim();

    try {
        await apiRequest(`/books/${bookId}/copies`, {
            method: "POST",
            body: JSON.stringify({ barcode }),
        });

        addCopyForm.reset();

        await loadCopies(bookId);
        await loadBooks();
        await refreshDashboard();

        setMessage(
            copiesMessage,
            "Physical copy added successfully.",
            "success"
        );
    } catch (error) {
        addCopyError.textContent = error.message;
        console.error("Adding physical copy failed:", error);
    } finally {
        addCopyButton.disabled = false;
        addCopyButton.textContent = "Add copy";
    }
});
