const DASH_API_BASE =
    window.EDUCONNECT_API_BASE || "http://127.0.0.1:5000";

async function dashboardApiBase() {
    if (window.EDUCONNECT_API_READY) {
        await window.EDUCONNECT_API_READY;
    }
    return window.EDUCONNECT_API_BASE || DASH_API_BASE;
}

const state = {
    user: null,
    school: null,
    posts: [],
    reviews: [],
    photos: []
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

function redirectToLogin() {
    window.location.replace("school-login.html");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function setText(id, value, fallback = "—") {
    const element = $(id);
    if (!element) return;
    const text = String(value || "").trim();
    element.textContent = text || fallback;
}

function showMessage(text, type = "") {
    const message = $("dashboard-message");
    if (!message) return;
    message.textContent = text || "";
    message.className = "form-message" + (type ? ` ${type}` : "");
}

async function apiRequest(path, options = {}) {
    const token = getToken();
    if (!token) {
        redirectToLogin();
        throw new Error("Not signed in.");
    }

    const apiBase = await dashboardApiBase();
    const headers = {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`
    };
    if (options.body) {
        headers["Content-Type"] = "application/json";
    }

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
        redirectToLogin();
        throw new Error("Your session expired. Sign in again.");
    }
    if (!response.ok) {
        throw new Error(
            (payload && payload.error) ||
                `Request failed (${response.status}).`
        );
    }
    return payload;
}

function verificationClass(status) {
    if (status === "verified") return "verified";
    if (status === "rejected") return "rejected";
    return "pending";
}

function verificationText(status) {
    if (status === "verified") return "Admin Verified";
    if (status === "rejected") return "Verification Rejected";
    return "Pending Verification";
}

function computeCompletion(school) {
    const fields = [
        school.name,
        school.city,
        school.level,
        school.location,
        school.phone,
        school.email,
        school.website,
        school.description,
        (school.programs || []).length,
        (school.facilities || []).length
    ];
    const complete = fields.filter((value) => Boolean(value)).length;
    return Math.round((complete / fields.length) * 100);
}

function renderSchool() {
    const school = state.school;
    const user = state.user;
    if (!school) return;

    setText("header-school-name", school.name, "School");
    setText("welcome-title", `Welcome, ${school.name}!`);
    setText(
        "welcome-description",
        `${school.city} · ${school.level || "Education level not provided"}`
    );

    const badge = $("verification-badge");
    badge.textContent = verificationText(school.verification_status);
    badge.className =
        "verification-badge " +
        verificationClass(school.verification_status);

    const detailBadge = $("verification-detail-badge");
    detailBadge.textContent = verificationText(school.verification_status);
    detailBadge.className =
        "verification-badge " +
        verificationClass(school.verification_status);

    $("completion-count").textContent = `${computeCompletion(school)}%`;

    setText("display-school-name", school.name);
    setText("display-city", school.city);
    setText("display-level", school.level, "Not provided");
    setText("display-email", school.email, "Not provided");
    setText("display-phone", school.phone, "Not provided");
    setText("display-address", school.location, "Not provided");
    setText("display-website", school.website, "Not provided");
    setText("display-telegram", school.telegram, "Not provided");
    setText(
        "display-programs",
        (school.programs || []).join(", "),
        "Not provided"
    );
    setText(
        "display-facilities",
        (school.facilities || []).join(", "),
        "Not provided"
    );

    setText("account-username", user.username);
    setText("account-email", user.email);
    setText("account-role", user.role);

    fillProfileForm();
    renderVerification();
}

function fillProfileForm() {
    const school = state.school;
    const fields = {
        "edit-school-name": school.name,
        "edit-city": school.city,
        "edit-level": school.level,
        "edit-email": school.email,
        "edit-phone": school.phone,
        "edit-address": school.location,
        "edit-website": school.website,
        "edit-telegram": school.telegram,
        "edit-programs": (school.programs || []).join(", "),
        "edit-facilities": (school.facilities || []).join(", "),
        "edit-description": school.description
    };
    Object.entries(fields).forEach(([id, value]) => {
        const element = $(id);
        if (element) element.value = value || "";
    });
}

function renderVerification() {
    const school = state.school;
    const summary = $("verification-summary");
    const records = school.verification_records || [];

    const recordRows = records.length
        ? records
              .map(
                  (record) => `
                <li>
                    <strong>${escapeHtml(record.status)}</strong>
                    <span>${escapeHtml(
                        formatDate(record.submitted_at)
                    )}</span>
                    ${
                        record.reviewed_by
                            ? `<p>Reviewed by ${escapeHtml(
                                  record.reviewed_by
                              )} on ${escapeHtml(
                                  formatDate(record.reviewed_at)
                              )}</p>`
                            : "<p>Awaiting review</p>"
                    }
                    ${record.notes ? `<p>${escapeHtml(record.notes)}</p>` : ""}
                </li>
            `
              )
              .join("")
        : "<li><p>No verification submissions recorded yet.</p></li>";

    const safeCertUrl = /^https?:\/\//i.test(
        school.certification_url || ""
    )
        ? school.certification_url
        : "";

    summary.innerHTML = `
        <div class="verification-summary-grid">
            <div>
                <strong>Status</strong>
                <p>${escapeHtml(
                    verificationText(school.verification_status)
                )}</p>
            </div>
            <div>
                <strong>Registration number</strong>
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
                    safeCertUrl
                        ? `<a href="${escapeHtml(
                              safeCertUrl
                          )}" target="_blank" rel="noopener noreferrer">
                              Open reference ↗
                           </a>`
                        : "Not provided"
                }</p>
            </div>
        </div>
        <p class="data-note">
            ${escapeHtml(
                school.verification_notes ||
                    "Verification is only marked complete after an administrator reviews the submitted certification."
            )}
        </p>
        <h3 class="verification-subtitle">Verification history</h3>
        <ul class="verification-history">${recordRows}</ul>
    `;

    $("verify-cert-number").value = school.certification_number || "";
    $("verify-cert-issuer").value =
        school.certification_issuer || "Ministry of Education";
    $("verify-cert-url").value = school.certification_url || "";
}

function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric"
    });
}

async function loadPosts() {
    state.posts = await apiRequest("/api/school/posts");
    renderPosts();
    updateCounts();
}

function renderPosts() {
    const container = $("school-posts");
    if (!state.posts.length) {
        container.innerHTML = `
            <p class="field-help">
                You haven't created any posts yet. Use "Create Post" to
                publish an update.
            </p>
        `;
        return;
    }

    container.innerHTML = state.posts
        .map(
            (post) => `
            <article class="school-post">
                <div class="school-post-header">
                    <strong>${escapeHtml(post.title)}</strong>
                    ${
                        post.is_hidden
                            ? '<span class="moderation-badge">Hidden by admin</span>'
                            : ""
                    }
                </div>
                <p>${escapeHtml(post.text || post.content || "")}</p>
                <small>${escapeHtml(formatDate(post.created_at || post.date))}</small>
                <button type="button" class="post-delete-btn"
                        data-post-id="${Number(post.id)}">
                    Delete
                </button>
            </article>
        `
        )
        .join("");
}

async function loadReviews() {
    state.reviews = await apiRequest("/api/school/reviews");
    renderReviews();
    updateCounts();
}

function renderReviews() {
    const container = $("dashboard-reviews");
    if (!state.reviews.length) {
        container.innerHTML = `
            <div class="empty-activity">
                <div class="empty-icon">+</div>
                <h3>No reviews yet</h3>
                <p>Family reviews will appear here.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.reviews
        .map(
            (review) => `
            <article class="dashboard-review">
                <div class="dashboard-review-top">
                    <strong>${escapeHtml(review.name)}</strong>
                    <span>${"★".repeat(review.rating)} ${review.rating}/5</span>
                    ${
                        review.is_hidden
                            ? '<span class="moderation-badge">Hidden by admin</span>'
                            : ""
                    }
                </div>
                <p>${escapeHtml(review.comment || "No comment.")}</p>
                <small>${escapeHtml(
                    formatDate(review.created_at || review.date)
                )}</small>
            </article>
        `
        )
        .join("");
}

function updateCounts() {
    $("post-count").textContent = state.posts.length;
    $("review-count").textContent = state.reviews.length;
}

function renderPhotos() {
    const container = $("school-photo-preview");
    container.replaceChildren();

    state.photos.forEach((photo) => {
        const image = document.createElement("img");
        image.src = photo.url;
        image.alt = photo.name;
        image.className = "school-photo";
        container.appendChild(image);
    });

    $("photo-count").textContent = state.photos.length;
}

function openProfileForm() {
    $("profile-display").hidden = true;
    $("profile-form").hidden = false;
    $("profile-message").textContent = "";
    $("edit-school-name").focus();
}

function closeProfileForm() {
    $("profile-form").hidden = true;
    $("profile-display").hidden = false;
    $("profile-message").textContent = "";
}

async function saveProfile(event) {
    event.preventDefault();
    const message = $("profile-message");
    const button = $("profile-form").querySelector(
        'button[type="submit"]'
    );

    const parseList = (value) =>
        String(value || "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);

    const data = {
        name: $("edit-school-name").value.trim(),
        city: $("edit-city").value,
        level: $("edit-level").value,
        email: $("edit-email").value.trim(),
        phone: $("edit-phone").value.trim(),
        location: $("edit-address").value.trim(),
        website: $("edit-website").value.trim(),
        telegram: $("edit-telegram").value.trim(),
        programs: parseList($("edit-programs").value),
        facilities: parseList($("edit-facilities").value),
        description: $("edit-description").value.trim()
    };

    if (!data.name || !data.city || !data.level || !data.email) {
        message.textContent = "Complete the required profile fields.";
        message.style.color = "#b42318";
        return;
    }

    button.disabled = true;
    message.textContent = "Saving...";
    message.style.color = "";

    try {
        const payload = await apiRequest("/api/school/me", {
            method: "PUT",
            body: JSON.stringify(data)
        });
        state.school = payload.school;
        localStorage.setItem(
            "educonnect_school",
            JSON.stringify(payload.school)
        );
        renderSchool();
        closeProfileForm();
        showMessage(payload.message || "School profile updated.", "success");
    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#b42318";
    } finally {
        button.disabled = false;
    }
}

async function createPost(event) {
    event.preventDefault();
    const message = $("post-message");
    const title = $("post-title").value.trim();
    const content = $("post-content").value.trim();

    if (!title || !content) {
        message.textContent = "Enter both a title and content.";
        message.style.color = "#b42318";
        return;
    }

    const button = $("post-form").querySelector(
        'button[type="submit"]'
    );
    button.disabled = true;
    message.textContent = "Publishing...";
    message.style.color = "";

    try {
        await apiRequest(
            `/api/schools/${Number(state.school.id)}/posts`,
            {
                method: "POST",
                body: JSON.stringify({ title, content })
            }
        );
        $("post-title").value = "";
        $("post-content").value = "";
        $("post-form").hidden = true;
        await loadPosts();
        showMessage("Post published.", "success");
    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#b42318";
    } finally {
        button.disabled = false;
    }
}

async function deletePost(postId) {
    if (!window.confirm("Delete this post permanently?")) return;
    try {
        await apiRequest(`/api/posts/${Number(postId)}`, {
            method: "DELETE"
        });
        await loadPosts();
        showMessage("Post deleted.", "success");
    } catch (error) {
        showMessage(error.message, "error");
    }
}

async function submitVerification(event) {
    event.preventDefault();
    const message = $("verification-message");
    const data = {
        certification_number: $("verify-cert-number").value.trim(),
        certification_issuer: $("verify-cert-issuer").value.trim(),
        certification_url: $("verify-cert-url").value.trim(),
        notes: $("verify-notes").value.trim()
    };

    const button = $("verification-form").querySelector(
        'button[type="submit"]'
    );
    button.disabled = true;
    message.textContent = "Submitting...";
    message.style.color = "";

    try {
        const payload = await apiRequest("/api/school/verification", {
            method: "POST",
            body: JSON.stringify(data)
        });
        state.school = payload.school;
        renderSchool();
        $("verify-notes").value = "";
        message.textContent =
            "Certification submitted. An administrator will review it.";
        message.style.color = "#067647";
        showMessage("Verification submitted for review.", "success");
    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#b42318";
    } finally {
        button.disabled = false;
    }
}

async function logout() {
    const token = getToken();
    if (token) {
        try {
            const apiBase = await dashboardApiBase();
            await fetch(apiBase + "/api/auth/logout", {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` }
            });
        } catch (error) {
            // Clear the local token even if the server is unreachable.
        }
    }
    clearSession();
    redirectToLogin();
}

function bindEvents() {
    $("logout-btn").addEventListener("click", logout);
    $("logout-btn-secondary").addEventListener("click", logout);

    $("edit-profile-btn").addEventListener("click", openProfileForm);
    $("quick-edit-profile-btn").addEventListener("click", openProfileForm);
    $("cancel-profile-btn").addEventListener("click", closeProfileForm);
    $("profile-form").addEventListener("submit", saveProfile);

    $("create-post-btn").addEventListener("click", () => {
        $("post-form").hidden = false;
        $("post-title").focus();
    });
    $("cancel-post-btn").addEventListener("click", () => {
        $("post-form").hidden = true;
        $("post-message").textContent = "";
    });
    $("post-form").addEventListener("submit", createPost);

    $("school-posts").addEventListener("click", (event) => {
        const button = event.target.closest(".post-delete-btn");
        if (button) deletePost(button.dataset.postId);
    });

    $("verification-form").addEventListener("submit", submitVerification);

    $("add-photos-btn").addEventListener("click", () => {
        $("school-photo-input").click();
    });

    $("school-photo-input").addEventListener("change", (event) => {
        const files = Array.from(event.target.files || []);
        files.forEach((file) => {
            if (!file.type.startsWith("image/")) return;
            state.photos.push({
                name: file.name,
                url: URL.createObjectURL(file)
            });
        });
        renderPhotos();
        event.target.value = "";
    });

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
        redirectToLogin();
        return;
    }

    bindEvents();

    try {
        const payload = await apiRequest("/api/auth/me");
        if (payload.user.role === "admin") {
            window.location.replace("admin.html");
            return;
        }
        state.user = payload.user;
        state.school = payload.school;

        if (!state.school) {
            showMessage(
                "No school is linked to this account. Contact an administrator.",
                "error"
            );
            return;
        }

        sessionStorage.setItem(
            "educonnect_user",
            JSON.stringify(state.user)
        );
        sessionStorage.setItem(
            "educonnect_school",
            JSON.stringify(state.school)
        );

        renderSchool();
        await Promise.all([loadPosts(), loadReviews()]);
    } catch (error) {
        if (getToken()) {
            showMessage(error.message, "error");
        }
    }
}

document.addEventListener("DOMContentLoaded", init);
