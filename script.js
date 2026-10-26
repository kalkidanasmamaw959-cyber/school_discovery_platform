const API_BASE =
    window.EDUCONNECT_API_BASE || "http://127.0.0.1:5000";

const state = {
    schools: [],
    loaded: false,
    loading: null,
    currentCity: "",
    recommendations: [],
    compare: new Set()
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function safeUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const withScheme = /^https?:\/\//i.test(raw)
        ? raw
        : "https://" + raw;
    try {
        const parsed = new URL(withScheme);
        if (!["http:", "https:"].includes(parsed.protocol)) return "";
        return parsed.href;
    } catch (error) {
        return "";
    }
}

function stripEmpty(value, fallback) {
    const text = String(value || "").trim();
    return text ? text : fallback;
}

async function apiRequest(path, options = {}) {
    if (window.EDUCONNECT_API_READY) {
        await window.EDUCONNECT_API_READY;
    }
    const apiBase = window.EDUCONNECT_API_BASE || API_BASE;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    let response;
    try {
        response = await fetch(apiBase + path, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            },
            signal: controller.signal
        });
    } catch (error) {
        clearTimeout(timeout);
        throw new Error(
            "Could not reach the backend. Start Flask and serve the " +
            "frontend from a local web server (not file://)."
        );
    }
    clearTimeout(timeout);

    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        payload = null;
    }

    if (!response.ok) {
        const message =
            payload && payload.error
                ? payload.error
                : `Request failed (${response.status}).`;
        throw new Error(message);
    }
    return payload;
}

async function loadSchools(force = false) {
    if (state.loaded && !force) return state.schools;
    if (state.loading && !force) return state.loading;

    state.loading = (async () => {
        const schools = await apiRequest("/api/schools");
        if (!Array.isArray(schools)) {
            throw new Error("The server returned an unexpected response.");
        }
        state.schools = schools;
        state.loaded = true;
        return schools;
    })();

    try {
        return await state.loading;
    } finally {
        state.loading = null;
    }
}

function setListStatus(message, type = "") {
    const element = $("school-list-status");
    if (!element) return;
    element.textContent = message || "";
    element.className =
        "school-status-message" + (type ? ` ${type}` : "");
    element.classList.toggle("hidden", !message);
}

async function showSchools(city) {
    state.currentCity = city;

    $("cities").classList.add("hidden");
    $("school-details").classList.add("hidden");
    $("school-list").classList.remove("hidden");
    $("selected-city-title").textContent = `Schools in ${city}`;
    $("school-search").value = "";
    $("level-filter").value = "all";
    $("verified-filter").checked = false;
    $("school-grid").innerHTML = "";
    $("no-schools").classList.add("hidden");
    setListStatus("Loading schools from the database...", "loading");

    try {
        await loadSchools();
        setListStatus("");
        displaySchools(getCitySchools());
    } catch (error) {
        setListStatus(error.message, "error");
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function getCitySchools() {
    return state.schools.filter(
        (school) =>
            String(school.city || "").toLowerCase() ===
            state.currentCity.toLowerCase()
    );
}

function verificationBadge(school) {
    if (school.verified) {
        return `<span class="school-status verified">Verified by admin</span>`;
    }
    return `<span class="school-status unverified">Unverified profile</span>`;
}

function displaySchools(schoolList) {
    const grid = $("school-grid");
    const noSchools = $("no-schools");
    grid.innerHTML = "";

    if (!schoolList.length) {
        noSchools.classList.remove("hidden");
        return;
    }
    noSchools.classList.add("hidden");

    schoolList.forEach((school) => {
        const firstLetter = stripEmpty(school.name, "?").charAt(0).toUpperCase();
        const programs = (school.programs || []).slice(0, 3);
        const tags = programs.length
            ? programs
                  .map(
                      (program) =>
                          `<span class="school-tag">${escapeHtml(program)}</span>`
                  )
                  .join("")
            : `<span class="school-tag muted">Programs not provided</span>`;

        const rating = school.review_count
            ? `★ ${school.average_rating} (${school.review_count} review${
                  school.review_count === 1 ? "" : "s"
              })`
            : "No family reviews yet";

        grid.insertAdjacentHTML(
            "beforeend",
            `
            <article class="school-card">
                <div class="school-image">
                    ${verificationBadge(school)}
                    <span class="school-image-letter">
                        ${escapeHtml(firstLetter)}
                    </span>
                </div>

                <div class="school-card-content">
                    <h3>${escapeHtml(school.name)}</h3>

                    <div class="school-location">
                        📍 ${escapeHtml(
                            stripEmpty(school.location, "Location not provided")
                        )}
                    </div>

                    <p class="school-description">
                        ${escapeHtml(
                            stripEmpty(
                                school.description,
                                "No description has been provided yet."
                            )
                        )}
                    </p>

                    <div class="school-tags">${tags}</div>

                    <p class="school-rating-line">${escapeHtml(rating)}</p>

                    <button
                        class="view-school-btn"
                        onclick="showSchoolDetails(${Number(school.id)})"
                    >
                        View School
                    </button>
                </div>
            </article>
            `
        );
    });
}

function filterSchools() {
    if (!state.currentCity) return;

    const searchText = $("school-search").value.toLowerCase().trim();
    const selectedLevel = $("level-filter").value;
    const verifiedOnly = $("verified-filter").checked;

    const filtered = getCitySchools().filter((school) => {
        const haystack = [
            school.name,
            school.city,
            school.location,
            school.description,
            ...(school.programs || []),
            ...(school.facilities || [])
        ]
            .join(" ")
            .toLowerCase();

        const matchesSearch = haystack.includes(searchText);
        const matchesLevel =
            selectedLevel === "all" ||
            String(school.level || "")
                .toLowerCase()
                .includes(selectedLevel.toLowerCase());
        const matchesVerification = !verifiedOnly || Boolean(school.verified);

        return matchesSearch && matchesLevel && matchesVerification;
    });

    displaySchools(filtered);
}

async function showSchoolDetails(id) {
    if (!state.loaded) {
        try {
            await loadSchools();
        } catch (error) {
            // The detail request below reports the error if the API is down.
        }
    }

    let school = state.schools.find(
        (item) => Number(item.id) === Number(id)
    );

    $("cities").classList.add("hidden");
    $("school-list").classList.add("hidden");
    $("school-details").classList.remove("hidden");
    document
        .querySelectorAll("#school-details > .success-banner")
        .forEach((banner) => banner.remove());
    $("school-detail-container").innerHTML =
        `<div class="empty-content"><p>Loading school profile...</p></div>`;

    try {
        school = await apiRequest(`/api/schools/${Number(id)}`);
        const index = state.schools.findIndex(
            (item) => Number(item.id) === Number(id)
        );
        if (index >= 0) {
            state.schools[index] = school;
        } else {
            state.schools.push(school);
        }
        if (!state.currentCity && school.city) {
            state.currentCity = school.city;
        }
    } catch (error) {
        $("school-detail-container").innerHTML = `
            <div class="empty-content error-content">
                <p>${escapeHtml(error.message)}</p>
                <button class="view-school-btn" onclick="backToSchools()">
                    Back to schools
                </button>
            </div>
        `;
        return;
    }

    renderSchoolDetails(school);
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderSchoolDetails(school) {
    const programs = (school.programs || []).length
        ? school.programs
              .map(
                  (program) =>
                      `<span class="detail-tag">${escapeHtml(program)}</span>`
              )
              .join("")
        : `<span class="detail-tag muted">Not provided</span>`;

    const facilities = (school.facilities || []).length
        ? school.facilities
              .map(
                  (facility) =>
                      `<span class="detail-tag">${escapeHtml(facility)}</span>`
              )
              .join("")
        : `<span class="detail-tag muted">Not provided</span>`;

    const posts = (school.posts || []).length
        ? school.posts
              .map(
                  (post) => `
            <article class="post-card">
                <span class="post-date">${escapeHtml(post.date || "")}</span>
                <h4>${escapeHtml(post.title)}</h4>
                <p>${escapeHtml(post.text || post.content || "")}</p>
            </article>
        `
              )
              .join("")
        : `
            <div class="empty-content">
                <p>School posts and announcements will appear here.</p>
            </div>
        `;

    const reviews = (school.reviews || []).length
        ? school.reviews
              .map(
                  (review) => `
            <div class="review-card">
                <div class="review-stars">
                    ${"★".repeat(Math.max(1, review.rating))}
                    <span class="review-score">${review.rating}/5</span>
                </div>
                <h4>${escapeHtml(review.name)}</h4>
                <p>${escapeHtml(stripEmpty(review.comment, "No comment."))}</p>
            </div>
        `
              )
              .join("")
        : `
            <div class="empty-content">
                <p>No reviews yet. Be the first family to share an experience.</p>
            </div>
        `;

    const contactItems = [];
    if (school.location) {
        const mapUrl =
            "https://www.google.com/maps/search/?api=1&query=" +
            encodeURIComponent(
                `${school.location}, ${school.city}, Ethiopia`
            );
        contactItems.push(`
            <div class="contact-item">
                <strong>📍 Location</strong>
                <a href="${mapUrl}" target="_blank" rel="noopener noreferrer">
                    ${escapeHtml(school.location)} — View Map
                </a>
            </div>
        `);
    }
    if (school.phone) {
        contactItems.push(`
            <div class="contact-item">
                <strong>📞 Phone</strong>
                <a href="tel:${escapeHtml(
                    school.phone.replace(/[^\d+]/g, "")
                )}">${escapeHtml(school.phone)}</a>
            </div>
        `);
    }
    if (school.email) {
        contactItems.push(`
            <div class="contact-item">
                <strong>✉ Email</strong>
                <a href="mailto:${escapeHtml(school.email)}">
                    ${escapeHtml(school.email)}
                </a>
            </div>
        `);
    }
    const website = safeUrl(school.website);
    if (website) {
        contactItems.push(`
            <div class="contact-item">
                <strong>🌐 Website</strong>
                <a href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer">
                    Visit School Website ↗
                </a>
            </div>
        `);
    }
    const telegram = safeUrl(school.telegram);
    if (telegram) {
        contactItems.push(`
            <div class="contact-item">
                <strong>✈ Telegram</strong>
                <a href="${escapeHtml(telegram)}" target="_blank" rel="noopener noreferrer">
                    Open Telegram ↗
                </a>
            </div>
        `);
    }

    const contact = contactItems.length
        ? contactItems.join("")
        : `<div class="empty-content">
             <p>No contact information has been provided yet. Please confirm
             details directly with the school before making a decision.</p>
           </div>`;

    const missing = (school.missing_information || []).filter(Boolean);
    const verificationNote = school.verified
        ? `Certification information was reviewed and approved by an
           EduConnect administrator. This is not a guarantee of school
           quality; confirm details with the school.`
        : `This profile has not been verified by an administrator.
           Information may be incomplete. Confirm details with the school.`;

    $("school-detail-container").innerHTML = `
        <div class="school-details-container">
            <button class="back-button" onclick="backToSchools()">
                ← Back to schools
            </button>

            <div class="school-profile-header">
                <div class="school-profile-image">
                    <span>${escapeHtml(
                        stripEmpty(school.name, "?").charAt(0).toUpperCase()
                    )}</span>
                </div>

                <div class="school-profile-title">
                    ${verificationBadge(school)}
                    <h2>${escapeHtml(school.name)}</h2>
                    <p>📍 ${escapeHtml(
                        stripEmpty(school.location, "Location not provided")
                    )}</p>
                    <p>${escapeHtml(
                        stripEmpty(school.level, "Education level not provided")
                    )}</p>
                    <p class="profile-rating">
                        ${
                            school.review_count
                                ? `★ ${school.average_rating}/5 from ${school.review_count} review(s)`
                                : "No family reviews yet"
                        }
                    </p>
                </div>
            </div>

            <div class="verification-panel ${
                school.verified ? "is-verified" : "is-unverified"
            }">
                <strong>${
                    school.verified
                        ? "Admin-verified profile"
                        : "Unverified profile"
                }</strong>
                <p>${escapeHtml(verificationNote)}</p>
            </div>

            <section class="profile-section">
                <span class="section-label">ABOUT THE SCHOOL</span>
                <h3>About the School</h3>
                <p>${escapeHtml(
                    stripEmpty(
                        school.description,
                        "No description has been provided by this school yet."
                    )
                )}</p>
            </section>

            <section class="profile-section">
                <span class="section-label">PROGRAMS</span>
                <h3>Education Programs</h3>
                <div class="detail-tags">${programs}</div>
            </section>

            <section class="profile-section">
                <span class="section-label">FACILITIES</span>
                <h3>School Facilities</h3>
                <div class="detail-tags">${facilities}</div>
                ${
                    missing.length
                        ? `<p class="data-note">Information not provided:
                           ${escapeHtml(missing.join(", "))}.
                           Nothing is inferred when data is missing.</p>`
                        : ""
                }
            </section>

            <section class="profile-section">
                <span class="section-label">CONTACT</span>
                <h3>Contact Information</h3>
                <div class="contact-grid">${contact}</div>
            </section>

            <section class="profile-section">
                <span class="section-label">SCHOOL NEWS</span>
                <h3>Latest Posts</h3>
                <div class="posts-container">${posts}</div>
            </section>

            <section class="profile-section">
                <span class="section-label">REVIEWS</span>
                <h3>Student &amp; Family Reviews</h3>
                <div class="reviews-container">${reviews}</div>
                <button
                    class="view-school-btn review-open-btn"
                    onclick="showReviewForm(${Number(school.id)})"
                >
                    Write a review
                </button>
            </section>

            <div id="review-form-container"
                 class="review-form-container hidden"></div>
        </div>
    `;
}

function backToSchools() {
    $("school-details").classList.add("hidden");
    $("school-list").classList.remove("hidden");
    filterSchools();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showCities() {
    $("school-list").classList.add("hidden");
    $("school-details").classList.add("hidden");
    $("cities").classList.remove("hidden");
    $("cities").scrollIntoView({ behavior: "smooth" });
}

function goToCities() {
    $("cities").scrollIntoView({ behavior: "smooth" });
}

function showReviewForm(id) {
    const school = state.schools.find(
        (item) => Number(item.id) === Number(id)
    );
    if (!school) return;

    const container = $("review-form-container");
    container.classList.remove("hidden");
    container.innerHTML = `
        <div class="review-form">
            <h3>Write a Review</h3>
            <label for="review-name">Your name</label>
            <input type="text" id="review-name" maxlength="100"
                   placeholder="Your name" required>
            <label for="review-rating">Rating</label>
            <select id="review-rating">
                <option value="5">★★★★★ — Excellent</option>
                <option value="4">★★★★ — Very good</option>
                <option value="3">★★★ — Good</option>
                <option value="2">★★ — Fair</option>
                <option value="1">★ — Poor</option>
            </select>
            <label for="review-comment">Your experience</label>
            <textarea id="review-comment" maxlength="2000"
                      placeholder="Write your experience..."></textarea>
            <p id="review-form-message" class="form-message" role="status"></p>
            <div class="review-form-actions">
                <button class="view-school-btn" id="review-submit-btn"
                        onclick="submitReview(${Number(school.id)})">
                    Submit Review
                </button>
                <button class="profile-cancel-btn" type="button"
                        onclick="hideReviewForm()">Cancel</button>
            </div>
        </div>
    `;
    container.scrollIntoView({ behavior: "smooth" });
}

function hideReviewForm() {
    const container = $("review-form-container");
    if (container) {
        container.classList.add("hidden");
        container.innerHTML = "";
    }
}

async function submitReview(id) {
    const name = $("review-name").value.trim();
    const rating = Number($("review-rating").value);
    const comment = $("review-comment").value.trim();
    const message = $("review-form-message");
    const button = $("review-submit-btn");

    const showError = (text) => {
        message.textContent = text;
        message.style.color = "#b42318";
    };

    if (!name) return showError("Please enter your name.");
    if (!comment) return showError("Please write a review.");
    if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
        return showError("Choose a rating from 1 to 5.");
    }

    button.disabled = true;
    button.textContent = "Submitting...";
    message.textContent = "";
    message.style.color = "";

    try {
        await apiRequest(`/api/schools/${Number(id)}/reviews`, {
            method: "POST",
            body: JSON.stringify({ name, rating, comment })
        });
        await loadSchools(true);
        await showSchoolDetails(id);
        const refreshed = $("school-details");
        if (refreshed) {
            refreshed.insertAdjacentHTML(
                "afterbegin",
                `<div class="success-banner">
                    Thank you. Your review has been published.
                 </div>`
            );
        }
    } catch (error) {
        showError(error.message);
        button.disabled = false;
        button.textContent = "Submit Review";
    }
}

/* =====================================================
   RECOMMENDATIONS
===================================================== */

function setRecommendMessage(text, type = "") {
    const element = $("recommend-message");
    if (!element) return;
    element.textContent = text || "";
    element.className = "form-message" + (type ? ` ${type}` : "");
}

function selectedValues(name) {
    return Array.from(
        document.querySelectorAll(`input[name="${name}"]:checked`)
    ).map((input) => input.value);
}

async function submitRecommendation(event) {
    event.preventDefault();

    const city = $("recommend-city").value;
    const level = $("recommend-level").value;
    const facilities = selectedValues("recommend-facility");
    const programs = selectedValues("recommend-program");
    const verifiedOnly = $("recommend-verified").checked;

    if (
        !city &&
        !level &&
        !facilities.length &&
        !programs.length &&
        !verifiedOnly
    ) {
        setRecommendMessage(
            "Choose at least one preference so we can match schools.",
            "error"
        );
        return;
    }

    setRecommendMessage("Finding suitable schools...", "loading");
    const button = $("recommend-submit-btn");
    button.disabled = true;
    $("recommend-results-initial").classList.add("hidden");
    $("recommend-list").innerHTML = "";
    $("compare-row").classList.add("hidden");
    $("compare-table-container").classList.add("hidden");
    state.compare.clear();

    try {
        const data = await apiRequest("/api/recommendations", {
            method: "POST",
            body: JSON.stringify({
                city,
                level,
                facilities,
                programs,
                verified_only: verifiedOnly,
                limit: 6
            })
        });
        state.recommendations = data.recommendations || [];
        renderRecommendations(data);
        setRecommendMessage("");
    } catch (error) {
        setRecommendMessage(error.message, "error");
        $("recommend-results-initial").classList.remove("hidden");
    } finally {
        button.disabled = false;
    }
}

function reasonClass(status) {
    if (status === "matched") return "reason-matched";
    if (status === "partial") return "reason-partial";
    if (status === "missing") return "reason-missing";
    return "reason-unmatched";
}

function renderRecommendations(data) {
    const list = $("recommend-list");
    const recommendations = data.recommendations || [];

    if (!recommendations.length) {
        list.innerHTML = `
            <div class="empty-content">
                <p>No schools matched those preferences yet.
                Try widening your choices.</p>
            </div>
        `;
        return;
    }

    const aiBlock = data.ai || {};
    const aiSummary = aiBlock.generated_by_ai && aiBlock.summary
        ? `<div class="ai-summary">
             <span class="ai-badge">External AI summary</span>
             <p>${escapeHtml(aiBlock.summary)}</p>
             <small>${escapeHtml(aiBlock.note || "")}</small>
           </div>`
        : `<div class="ai-summary rule-based">
             <span class="ai-badge rule">Explainable match</span>
             <p>${escapeHtml(
                 aiBlock.note ||
                     "Scores use a transparent weighted algorithm."
             )}</p>
           </div>`;

    const cards = recommendations
        .map((item, index) => {
            const school = item.school;
            const reasons = (item.reasons || [])
                .map(
                    (reason) => `
                    <li class="${reasonClass(reason.status)}">
                        <span>${escapeHtml(reason.label)}</span>
                        <strong>${reason.points}/${reason.max_points}</strong>
                        <p>${escapeHtml(reason.detail)}</p>
                    </li>
                `
                )
                .join("");

            const missing = (item.missing_information || []).filter(
                Boolean
            );

            return `
                <article class="recommend-card">
                    <div class="recommend-card-top">
                        <div class="score-ring" style="--score:${Math.max(
                            0,
                            Math.min(100, item.score)
                        )}">
                            <span>${item.score}%</span>
                        </div>
                        <div class="recommend-title">
                            <div class="recommend-meta">
                                ${verificationBadge(school)}
                                <span class="recommend-rank">
                                    Match ${index + 1}
                                </span>
                            </div>
                            <h3>${escapeHtml(school.name)}</h3>
                            <p>${escapeHtml(school.city)} · ${escapeHtml(
                                stripEmpty(
                                    school.level,
                                    "Level not provided"
                                )
                            )}</p>
                        </div>
                    </div>

                    <ul class="reason-list">${reasons}</ul>

                    ${
                        missing.length
                            ? `<p class="data-note">
                                Missing information: ${escapeHtml(
                                    missing.join(", ")
                                )}. Missing data reduced the score; it was
                                not guessed.</p>`
                            : ""
                    }

                    <div class="recommend-actions">
                        <button class="view-school-btn"
                            onclick="openRecommendedSchool(${Number(
                                school.id
                            )})">
                            View profile
                        </button>
                        <label class="compare-check">
                            <input type="checkbox"
                                   class="compare-box"
                                   value="${Number(school.id)}"
                                   onchange="toggleCompare(${Number(
                                       school.id
                                   )}, this)">
                            Compare
                        </label>
                    </div>
                </article>
            `;
        })
        .join("");

    const feesNote = data.fees_note
        ? `<p class="fees-note">${escapeHtml(data.fees_note)}</p>`
        : "";

    list.innerHTML = aiSummary + feesNote + cards;
    $("compare-row").classList.remove("hidden");
    updateCompareCount();
}

function openRecommendedSchool(id) {
    const item = state.recommendations.find(
        (recommendation) => Number(recommendation.school.id) === Number(id)
    );
    if (item && item.school.city) {
        state.currentCity = item.school.city;
    }
    showSchoolDetails(id);
}

function toggleCompare(id, checkbox) {
    if (checkbox.checked) {
        if (state.compare.size >= 4) {
            checkbox.checked = false;
            setRecommendMessage(
                "You can compare up to four schools at a time.",
                "error"
            );
            return;
        }
        state.compare.add(Number(id));
    } else {
        state.compare.delete(Number(id));
    }
    updateCompareCount();
}

function updateCompareCount() {
    const label = $("compare-count");
    if (label) {
        label.textContent = `${state.compare.size} selected`;
    }
    const button = $("compare-btn");
    if (button) button.disabled = state.compare.size < 2;
}

function renderCompare() {
    const selected = state.recommendations.filter((item) =>
        state.compare.has(Number(item.school.id))
    );
    const container = $("compare-table-container");

    if (selected.length < 2) {
        setRecommendMessage(
            "Select at least two recommended schools to compare.",
            "error"
        );
        return;
    }
    setRecommendMessage("");

    const row = (label, render) => `
        <tr>
            <th>${escapeHtml(label)}</th>
            ${selected
                .map((item) => `<td>${render(item)}</td>`)
                .join("")}
        </tr>
    `;

    container.innerHTML = `
        <div class="compare-header">
            <h3>Compare recommendations</h3>
            <button class="profile-cancel-btn" type="button"
                    onclick="clearCompare()">Close comparison</button>
        </div>
        <div class="table-scroll">
            <table class="compare-table">
                <thead>
                    <tr>
                        <th>Factor</th>
                        ${selected
                            .map(
                                (item) =>
                                    `<th>${escapeHtml(
                                        item.school.name
                                    )}</th>`
                            )
                            .join("")}
                    </tr>
                </thead>
                <tbody>
                    ${row(
                        "Match score",
                        (item) => `<strong>${item.score}%</strong>`
                    )}
                    ${row(
                        "Verification",
                        (item) =>
                            item.school.verified
                                ? "Verified by admin"
                                : "Unverified profile"
                    )}
                    ${row(
                        "City",
                        (item) => escapeHtml(item.school.city)
                    )}
                    ${row(
                        "Level",
                        (item) =>
                            escapeHtml(
                                stripEmpty(
                                    item.school.level,
                                    "Not provided"
                                )
                            )
                    )}
                    ${row("Facilities", (item) =>
                        (item.school.facilities || []).length
                            ? escapeHtml(
                                  item.school.facilities.join(", ")
                              )
                            : "Not provided"
                    )}
                    ${row("Programs", (item) =>
                        (item.school.programs || []).length
                            ? escapeHtml(
                                  item.school.programs.join(", ")
                              )
                            : "Not provided"
                    )}
                    ${row(
                        "Family rating",
                        (item) =>
                            item.school.review_count
                                ? `★ ${item.school.average_rating}/5 (${item.school.review_count})`
                                : "No reviews yet"
                    )}
                    ${row(
                        "Contact",
                        (item) => {
                            const fields = [
                                item.school.phone && "Phone",
                                item.school.email && "Email",
                                item.school.website && "Website",
                                item.school.location && "Location"
                            ].filter(Boolean);
                            return fields.length
                                ? escapeHtml(fields.join(", "))
                                : "Not provided";
                        }
                    )}
                    ${row(
                        "Missing data",
                        (item) =>
                            (item.missing_information || []).length
                                ? escapeHtml(
                                      item.missing_information.join(", ")
                                  )
                                : "None recorded"
                    )}
                </tbody>
            </table>
        </div>
        <p class="fees-note">
            Comparison uses only available school data and does not include
            fees, because reliable fee data is not collected.
        </p>
    `;
    container.classList.remove("hidden");
    container.scrollIntoView({ behavior: "smooth" });
}

function clearCompare() {
    $("compare-table-container").classList.add("hidden");
    $("compare-table-container").innerHTML = "";
    state.compare.clear();
    document
        .querySelectorAll(".compare-box")
        .forEach((box) => {
            box.checked = false;
        });
    updateCompareCount();
}

document.addEventListener("DOMContentLoaded", () => {
    const form = $("recommend-form");
    if (form) form.addEventListener("submit", submitRecommendation);

    const compareButton = $("compare-btn");
    if (compareButton) compareButton.addEventListener("click", renderCompare);

    loadSchools().catch(() => {
        setListStatus(
            "Could not load schools. Make sure the backend is running.",
            "error"
        );
    });
});
