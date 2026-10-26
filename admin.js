const ADMIN_API_BASE =
    window.EDUCONNECT_API_BASE || "http://127.0.0.1:5000";

async function adminApiBase() {
    if (window.EDUCONNECT_API_READY) {
        await window.EDUCONNECT_API_READY;
    }
    return window.EDUCONNECT_API_BASE || ADMIN_API_BASE;
}

const adminState = {
    user: null,
    schools: [],
    users: [],
    reviews: [],
    posts: [],
    activeSchoolId: null
};

const $ = (id) => document.getElementById(id);

function getToken() {
    return (
        sessionStorage.getItem("educonnect_token") ||
        localStorage.getItem("educonnect_token")
    );
}

function clearSession() {
    [sessionStorage, localStorage].forEach((storage) => {
        storage.removeItem("educonnect_token");
        storage.removeItem("educonnect_user");
        storage.removeItem("educonnect_school");
    });
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function safeUrl(value) {
    const url = String(value || "").trim();
    if (!/^https?:\/\//i.test(url)) return "";
    return url;
}

function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function adminMessage(text, type = "") {
    const element = $("admin-message");
    element.textContent = text || "";
    element.className = "form-message" + (type ? ` ${type}` : "");
}

async function apiRequest(path, options = {}) {
    const token = getToken();
    if (!token) {
        window.location.replace("school-login.html");
        throw new Error("Not signed in.");
    }

    const apiBase = await adminApiBase();
    const headers = {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`
    };
    if (options.body) headers["Content-Type"] = "application/json";

    let response;
    try {
        response = await fetch(apiBase + path, {
            ...options,
            headers
        });
    } catch (error) {
        throw new Error(
            `Could not reach the backend at ${apiBase}. ` +
                "Start Flask and open the app through " +
                "http://127.0.0.1:5000/app/."
        );
    }

    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        payload = null;
    }

    if (response.status === 401) {
        clearSession();
        window.location.replace("school-login.html");
        throw new Error("Session expired.");
    }
    if (response.status === 403) {
        throw new Error(
            "Administrator permission is required for this action."
        );
    }
    if (!response.ok) {
        throw new Error(
            (payload && payload.error) ||
                `Request failed (${response.status}).`
        );
    }
    return payload;
}

function statusClass(status) {
    if (status === "verified") return "verified";
    if (status === "rejected") return "rejected";
    return "pending";
}

function statusText(status) {
    if (status === "verified") return "Verified";
    if (status === "rejected") return "Rejected";
    return "Pending";
}

async function loadStats() {
    const stats = await apiRequest("/api/admin/stats");
    $("stat-schools").textContent = stats.schools;
    $("stat-pending").textContent = stats.pending_schools;
    $("stat-verified").textContent = stats.verified_schools;
    $("stat-users").textContent = stats.users;
    $("stat-hidden-reviews").textContent = stats.hidden_reviews;
    $("stat-hidden-posts").textContent = stats.hidden_posts;
}

async function loadSchools() {
    const status = $("school-status-filter").value;
    const path = status
        ? `/api/admin/schools?status=${encodeURIComponent(status)}`
        : "/api/admin/schools";
    adminState.schools = await apiRequest(path);
    renderSchools();
}

function renderSchools() {
    const container = $("admin-school-list");
    if (!adminState.schools.length) {
        container.innerHTML = `
            <div class="empty-content">
                <p>No schools match this filter.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = adminState.schools
        .map((school) => {
            const certUrl = safeUrl(school.certification_url);
            return `
            <article class="admin-card">
                <div class="admin-card-top">
                    <div>
                        <h3>${escapeHtml(school.name)}</h3>
                        <p>${escapeHtml(school.city)} · ${escapeHtml(
                            school.level || "Level not provided"
                        )}</p>
                    </div>
                    <span class="verification-badge ${statusClass(
                        school.verification_status
                    )}">
                        ${statusText(school.verification_status)}
                    </span>
                </div>

                <div class="admin-info-grid">
                    <div>
                        <strong>MoE registration number</strong>
                        <p>${escapeHtml(
                            school.certification_number || "Not provided"
                        )}</p>
                    </div>
                    <div>
                        <strong>Issuing authority</strong>
                        <p>${escapeHtml(
                            school.certification_issuer || "Not provided"
                        )}</p>
                    </div>
                    <div>
                        <strong>Certificate reference</strong>
                        <p>${
                            certUrl
                                ? `<a href="${escapeHtml(
                                      certUrl
                                  )}" target="_blank" rel="noopener noreferrer">
                                      Open reference ↗
                                   </a>`
                                : "Not provided"
                        }</p>
                    </div>
                    <div>
                        <strong>Contact</strong>
                        <p>${escapeHtml(
                            school.phone || "No phone"
                        )} · ${escapeHtml(school.email || "No email")}</p>
                    </div>
                    <div>
                        <strong>Submitted</strong>
                        <p>${escapeHtml(formatDate(school.created_at))}</p>
                    </div>
                    <div>
                        <strong>Registered accounts</strong>
                        <p>${(school.users || []).length}</p>
                    </div>
                </div>

                <p class="data-note">
                    ${escapeHtml(
                        school.verification_notes ||
                            "No reviewer notes recorded."
                    )}
                </p>

                <div class="admin-actions">
                    <button type="button" class="dashboard-action"
                            data-action="review-school"
                            data-id="${Number(school.id)}">
                        Review certification
                    </button>
                </div>
            </article>
        `;
        })
        .join("");
}

async function loadUsers() {
    adminState.users = await apiRequest("/api/admin/users");
    renderUsers();
}

function renderUsers() {
    const container = $("admin-user-list");
    if (!adminState.users.length) {
        container.innerHTML = `<div class="empty-content"><p>No users.</p></div>`;
        return;
    }

    container.innerHTML = adminState.users
        .map((user) => {
            const isSelf = user.id === adminState.user.id;
            return `
            <article class="admin-row">
                <div class="admin-row-main">
                    <strong>${escapeHtml(user.username)}</strong>
                    <span>${escapeHtml(user.email)}</span>
                    <span>${escapeHtml(user.role)} · ${
                        user.school_name
                            ? escapeHtml(user.school_name)
                            : "No school"
                    }</span>
                </div>
                <div class="admin-row-actions">
                    <span class="verification-badge ${
                        user.is_active ? "verified" : "rejected"
                    }">
                        ${user.is_active ? "Active" : "Disabled"}
                    </span>
                    ${
                        isSelf
                            ? '<span class="admin-self">Current account</span>'
                            : `<button type="button" class="dashboard-action"
                                   data-action="toggle-user"
                                   data-id="${Number(user.id)}"
                                   data-active="${user.is_active ? "1" : "0"}">
                                   ${user.is_active ? "Disable" : "Enable"}
                               </button>
                               <button type="button" class="reject-btn"
                                   data-action="delete-user"
                                   data-id="${Number(user.id)}">
                                   Delete
                               </button>`
                    }
                </div>
            </article>
        `;
        })
        .join("");
}

async function loadReviews() {
    adminState.reviews = await apiRequest("/api/admin/reviews");
    renderReviews();
}

function renderReviews() {
    const container = $("admin-review-list");
    if (!adminState.reviews.length) {
        container.innerHTML = `<div class="empty-content"><p>No reviews.</p></div>`;
        return;
    }

    container.innerHTML = adminState.reviews
        .map(
            (review) => `
            <article class="admin-card">
                <div class="admin-card-top">
                    <div>
                        <h3>${escapeHtml(review.name)} · ${"★".repeat(
                            review.rating
                        )}</h3>
                        <p>${escapeHtml(review.school_name)} · ${escapeHtml(
                            formatDate(review.created_at)
                        )}</p>
                    </div>
                    ${
                        review.is_hidden
                            ? '<span class="moderation-badge">Hidden</span>'
                            : ""
                    }
                </div>
                <p class="admin-content">${escapeHtml(
                    review.comment || "No comment."
                )}</p>
                <div class="admin-actions">
                    <button type="button" class="dashboard-action"
                            data-action="toggle-review"
                            data-id="${Number(review.id)}"
                            data-hidden="${review.is_hidden ? "1" : "0"}">
                        ${review.is_hidden ? "Restore" : "Hide"}
                    </button>
                    <button type="button" class="reject-btn"
                            data-action="delete-review"
                            data-id="${Number(review.id)}">
                        Delete
                    </button>
                </div>
            </article>
        `
        )
        .join("");
}

async function loadPosts() {
    adminState.posts = await apiRequest("/api/admin/posts");
    renderPosts();
}

function renderPosts() {
    const container = $("admin-post-list");
    if (!adminState.posts.length) {
        container.innerHTML = `<div class="empty-content"><p>No posts.</p></div>`;
        return;
    }

    container.innerHTML = adminState.posts
        .map(
            (post) => `
            <article class="admin-card">
                <div class="admin-card-top">
                    <div>
                        <h3>${escapeHtml(post.title)}</h3>
                        <p>${escapeHtml(post.school_name)} · ${escapeHtml(
                            formatDate(post.created_at)
                        )}</p>
                    </div>
                    ${
                        post.is_hidden
                            ? '<span class="moderation-badge">Hidden</span>'
                            : ""
                    }
                </div>
                <p class="admin-content">${escapeHtml(
                    post.text || post.content || ""
                )}</p>
                <div class="admin-actions">
                    <button type="button" class="dashboard-action"
                            data-action="toggle-post"
                            data-id="${Number(post.id)}"
                            data-hidden="${post.is_hidden ? "1" : "0"}">
                        ${post.is_hidden ? "Restore" : "Hide"}
                    </button>
                    <button type="button" class="reject-btn"
                            data-action="delete-post"
                            data-id="${Number(post.id)}">
                        Delete
                    </button>
                </div>
            </article>
        `
        )
        .join("");
}

function openSchoolModal(schoolId) {
    const school = adminState.schools.find(
        (item) => Number(item.id) === Number(schoolId)
    );
    if (!school) return;

    adminState.activeSchoolId = Number(school.id);
    const certUrl = safeUrl(school.certification_url);
    const records = school.verification_records || [];

    $("review-modal-title").textContent = `Review: ${school.name}`;
    $("school-review-content").innerHTML = `
        <div class="admin-info-grid">
            <div>
                <strong>Status</strong>
                <p>${statusText(school.verification_status)}</p>
            </div>
            <div>
                <strong>City</strong>
                <p>${escapeHtml(school.city)}</p>
            </div>
            <div>
                <strong>MoE registration number</strong>
                <p>${escapeHtml(
                    school.certification_number || "Not provided"
                )}</p>
            </div>
            <div>
                <strong>Issuing authority</strong>
                <p>${escapeHtml(
                    school.certification_issuer || "Not provided"
                )}</p>
            </div>
            <div>
                <strong>Certificate reference</strong>
                <p>${
                    certUrl
                        ? `<a href="${escapeHtml(
                              certUrl
                          )}" target="_blank" rel="noopener noreferrer">
                              Open reference ↗
                           </a>`
                        : "Not provided"
                }</p>
            </div>
            <div>
                <strong>Address</strong>
                <p>${escapeHtml(school.location || "Not provided")}</p>
            </div>
            <div>
                <strong>Email</strong>
                <p>${escapeHtml(school.email || "Not provided")}</p>
            </div>
            <div>
                <strong>Phone</strong>
                <p>${escapeHtml(school.phone || "Not provided")}</p>
            </div>
        </div>

        <h3 class="verification-subtitle">Submitted accounts</h3>
        <ul class="verification-history">
            ${(school.users || [])
                .map(
                    (user) =>
                        `<li><strong>${escapeHtml(
                            user.username
                        )}</strong><p>${escapeHtml(user.email)}</p></li>`
                )
                .join("") || "<li><p>No linked accounts.</p></li>"}
        </ul>

        <h3 class="verification-subtitle">Verification history</h3>
        <ul class="verification-history">
            ${
                records
                    .map(
                        (record) => `
                <li>
                    <strong>${escapeHtml(record.status)}</strong>
                    <span>${escapeHtml(formatDate(record.submitted_at))}</span>
                    <p>${escapeHtml(record.notes || "No submitter notes.")}</p>
                    ${
                        record.admin_notes
                            ? `<p>Admin: ${escapeHtml(
                                  record.admin_notes
                              )}</p>`
                            : ""
                    }
                </li>
            `
                    )
                    .join("") ||
                "<li><p>No verification records.</p></li>"
            }
        </ul>
    `;
    $("review-notes").value = school.verification_notes || "";
    $("review-message").textContent = "";
    $("school-review-modal").classList.remove("hidden");
}

function closeSchoolModal() {
    $("school-review-modal").classList.add("hidden");
    adminState.activeSchoolId = null;
}

async function approveActiveSchool() {
    const id = adminState.activeSchoolId;
    if (!id) return;
    const notes = $("review-notes").value.trim();
    const message = $("review-message");
    try {
        await apiRequest(`/api/admin/schools/${id}/verify`, {
            method: "POST",
            body: JSON.stringify({ notes })
        });
        closeSchoolModal();
        adminMessage("School verified and approved.", "success");
        await Promise.all([loadSchools(), loadStats()]);
    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#b42318";
    }
}

async function rejectActiveSchool() {
    const id = adminState.activeSchoolId;
    if (!id) return;
    const notes = $("review-notes").value.trim();
    const message = $("review-message");
    if (notes.length < 3) {
        message.textContent =
            "Enter a clear rejection reason before rejecting.";
        message.style.color = "#b42318";
        return;
    }
    try {
        await apiRequest(`/api/admin/schools/${id}/reject`, {
            method: "POST",
            body: JSON.stringify({ notes })
        });
        closeSchoolModal();
        adminMessage("School rejected. It is hidden from public listings.");
        await Promise.all([loadSchools(), loadStats()]);
    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#b42318";
    }
}

async function toggleUser(id, active) {
    try {
        await apiRequest(`/api/admin/users/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: !active })
        });
        adminMessage(
            active ? "User disabled." : "User enabled.",
            "success"
        );
        await Promise.all([loadUsers(), loadStats()]);
    } catch (error) {
        adminMessage(error.message, "error");
    }
}

async function deleteUser(id) {
    if (!window.confirm("Delete this user account permanently?")) return;
    try {
        await apiRequest(`/api/admin/users/${id}`, { method: "DELETE" });
        adminMessage("User deleted.", "success");
        await Promise.all([loadUsers(), loadStats()]);
    } catch (error) {
        adminMessage(error.message, "error");
    }
}

async function toggleReview(id, hidden) {
    try {
        await apiRequest(`/api/admin/reviews/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ is_hidden: !hidden })
        });
        adminMessage(
            hidden ? "Review restored." : "Review hidden.",
            "success"
        );
        await Promise.all([loadReviews(), loadStats()]);
    } catch (error) {
        adminMessage(error.message, "error");
    }
}

async function deleteReview(id) {
    if (!window.confirm("Delete this review permanently?")) return;
    try {
        await apiRequest(`/api/admin/reviews/${id}`, { method: "DELETE" });
        adminMessage("Review deleted.", "success");
        await Promise.all([loadReviews(), loadStats()]);
    } catch (error) {
        adminMessage(error.message, "error");
    }
}

async function togglePost(id, hidden) {
    try {
        await apiRequest(`/api/admin/posts/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ is_hidden: !hidden })
        });
        adminMessage(
            hidden ? "Post restored." : "Post hidden.",
            "success"
        );
        await Promise.all([loadPosts(), loadStats()]);
    } catch (error) {
        adminMessage(error.message, "error");
    }
}

async function deletePost(id) {
    if (!window.confirm("Delete this post permanently?")) return;
    try {
        await apiRequest(`/api/posts/${id}`, { method: "DELETE" });
        adminMessage("Post deleted.", "success");
        await Promise.all([loadPosts(), loadStats()]);
    } catch (error) {
        adminMessage(error.message, "error");
    }
}

async function logout() {
    const token = getToken();
    if (token) {
        try {
            const apiBase = await adminApiBase();
            await fetch(apiBase + "/api/auth/logout", {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` }
            });
        } catch (error) {
            // Local session is cleared below regardless.
        }
    }
    clearSession();
    window.location.replace("school-login.html");
}

function bindEvents() {
    $("admin-logout").addEventListener("click", logout);
    $("refresh-schools").addEventListener("click", () => {
        loadSchools().catch((error) => adminMessage(error.message, "error"));
    });
    $("school-status-filter").addEventListener("change", () => {
        loadSchools().catch((error) => adminMessage(error.message, "error"));
    });
    $("refresh-users").addEventListener("click", () => {
        loadUsers().catch((error) => adminMessage(error.message, "error"));
    });
    $("refresh-reviews").addEventListener("click", () => {
        loadReviews().catch((error) => adminMessage(error.message, "error"));
    });
    $("refresh-posts").addEventListener("click", () => {
        loadPosts().catch((error) => adminMessage(error.message, "error"));
    });

    $("admin-school-list").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action='review-school']");
        if (button) openSchoolModal(button.dataset.id);
    });

    $("admin-user-list").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.dataset.action === "toggle-user") {
            toggleUser(id, button.dataset.active === "1");
        } else if (button.dataset.action === "delete-user") {
            deleteUser(id);
        }
    });

    $("admin-review-list").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.dataset.action === "toggle-review") {
            toggleReview(id, button.dataset.hidden === "1");
        } else if (button.dataset.action === "delete-review") {
            deleteReview(id);
        }
    });

    $("admin-post-list").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.dataset.action === "toggle-post") {
            togglePost(id, button.dataset.hidden === "1");
        } else if (button.dataset.action === "delete-post") {
            deletePost(id);
        }
    });

    $("close-school-modal").addEventListener("click", closeSchoolModal);
    $("cancel-school-modal").addEventListener("click", closeSchoolModal);
    $("approve-school-btn").addEventListener("click", approveActiveSchool);
    $("reject-school-btn").addEventListener("click", rejectActiveSchool);

    document.querySelectorAll(".dashboard-nav a").forEach((link) => {
        link.addEventListener("click", () => {
            document
                .querySelectorAll(".dashboard-nav a")
                .forEach((item) => item.classList.remove("active"));
            link.classList.add("active");
        });
    });
}

async function init() {
    if (!getToken()) {
        window.location.replace("school-login.html");
        return;
    }

    bindEvents();

    try {
        const payload = await apiRequest("/api/auth/me");
        if (payload.user.role !== "admin") {
            window.location.replace("dashboard.html");
            return;
        }
        adminState.user = payload.user;
        $("admin-name").textContent = payload.user.username;

        const results = await Promise.allSettled([
            loadStats(),
            loadSchools(),
            loadUsers(),
            loadReviews(),
            loadPosts()
        ]);
        const failed = results.find(
            (result) => result.status === "rejected"
        );
        if (failed) {
            adminMessage(failed.reason.message, "error");
        }
    } catch (error) {
        if (getToken()) adminMessage(error.message, "error");
    }
}

document.addEventListener("DOMContentLoaded", init);
