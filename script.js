const $ = id => document.getElementById(id);
const schools = [

    /* =========================
       BAHIR DAR
    ========================= */

    {
        id: 1,
        name: "SOS School",
        city: "Bahir Dar",
        level: "Primary & Secondary",
        location: "Bahir Dar, Ethiopia",

        description:
            "School information will be added after the school data collection phase.",

        programs: [
            "Primary Education",
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab",
            "Science Lab",
            "Playground"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    {
        id: 2,
        name: "Bahir Dar Academy",
        city: "Bahir Dar",
        level: "Primary & Secondary",
        location: "Bahir Dar, Ethiopia",

        description:
            "School information will be added after the school data collection phase.",

        programs: [
            "Primary Education",
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab",
            "Playground"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    {
        id: 3,
        name: "Catholic School",
        city: "Bahir Dar",
        level: "Primary & Secondary",
        location: "Bahir Dar, Ethiopia",

        description:
            "School information will be added after the school data collection phase.",

        programs: [
            "Primary Education",
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    {
        id: 4,
        name: "Eshet School",
        city: "Bahir Dar",
        level: "Primary & Secondary",
        location: "Bahir Dar, Ethiopia",

        description:
            "School information will be added after the school data collection phase.",

        programs: [
            "Primary Education",
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab",
            "Playground"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    {
        id: 5,
        name: "Abune Gorgorios School",
        city: "Bahir Dar",
        level: "Primary & Secondary",
        location: "Bahir Dar, Ethiopia",

        description:
            "School information will be added after the school data collection phase.",

        programs: [
            "Primary Education",
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab",
            "Science Lab"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    /* =========================
       ADDIS ABABA
    ========================= */

    {
        id: 6,
        name: "School Profile Coming Soon",
        city: "Addis Ababa",
        level: "Primary",
        location: "Addis Ababa, Ethiopia",

        description:
            "Real school information will be added after the data collection phase.",

        programs: [
            "Primary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    /* =========================
       HAWASSA
    ========================= */

    {
        id: 7,
        name: "School Profile Coming Soon",
        city: "Hawassa",
        level: "Secondary",
        location: "Hawassa, Ethiopia",

        description:
            "Real school information will be added after the data collection phase.",

        programs: [
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    },


    /* =========================
       ADAMA
    ========================= */

    {
        id: 8,
        name: "School Profile Coming Soon",
        city: "Adama",
        level: "Primary & Secondary",
        location: "Adama, Ethiopia",

        description:
            "Real school information will be added after the data collection phase.",

        programs: [
            "Primary Education",
            "Secondary Education"
        ],

        facilities: [
            "Library",
            "Computer Lab"
        ],

        website: "",
        email: "",
        phone: "",
        telegram: "",

        posts: [],

        reviews: []
    }

];



/* =====================================================
   2. CURRENT CITY
===================================================== */

let currentCity = "";



/* =====================================================
   3. SHOW SCHOOLS IN A CITY
===================================================== */

function showSchools(city) {

    // Remember which city the user selected
    currentCity = city;


    // Hide the city section
    document
        .getElementById("cities")
        .classList.add("hidden");


    // Hide school details if they were open
    document
        .getElementById("school-details")
        .classList.add("hidden");


    // Show school list
    document
        .getElementById("school-list")
        .classList.remove("hidden");


    // Change heading
    document
        .getElementById("selected-city-title")
        .textContent = `Schools in ${city}`;


    // Clear search box
    document
        .getElementById("school-search")
        .value = "";


    // Reset level filter
    document
        .getElementById("level-filter")
        .value = "all";


    // Get schools from selected city
    const citySchools = schools.filter(
        school => school.city === city
    );


    // Display them
    displaySchools(citySchools);


    // Go to top of page
    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}



/* =====================================================
   4. DISPLAY SCHOOL CARDS
===================================================== */

function displaySchools(schoolList) {

    const grid =
        document.getElementById("school-grid");

    const noSchools =
        document.getElementById("no-schools");


    // Clear previous cards
    grid.innerHTML = "";


    /* -----------------------------------------
       If there are no schools
    ----------------------------------------- */

    if (schoolList.length === 0) {

        noSchools.classList.remove("hidden");

        return;
    }


    // Hide "No schools found"
    noSchools.classList.add("hidden");


    /* -----------------------------------------
       Create a card for every school
    ----------------------------------------- */

    schoolList.forEach(school => {

        // Get first letter of school name
        const firstLetter =
            school.name.charAt(0).toUpperCase();


        // Create program tags
        const tags = school.programs
            .slice(0, 2)
            .map(program => {

                return `
                    <span class="school-tag">
                        ${program}
                    </span>
                `;

            })
            .join("");


        // Add school card
        grid.innerHTML += `

            <article class="school-card">

                <div class="school-image">

                    <span class="school-status">
                        Profile Listed
                    </span>

                    <span class="school-image-letter">
                        ${firstLetter}
                    </span>

                </div>


                <div class="school-card-content">

                    <h3>
                        ${school.name}
                    </h3>


                    <div class="school-location">
                        📍 ${school.location}
                    </div>


                    <p class="school-description">
                        ${school.description}
                    </p>


                    <div class="school-tags">

                        ${tags}

                    </div>


                    <button
                        class="view-school-btn"
                        onclick="showSchoolDetails(${school.id})"
                    >
                        View School
                    </button>

                </div>

            </article>

        `;

    });
}



/* =====================================================
   5. SEARCH + FILTER
===================================================== */

function filterSchools() {

    // Get search text
    const searchText =
        document
            .getElementById("school-search")
            .value
            .toLowerCase()
            .trim();


    // Get selected level
    const selectedLevel =
        document
            .getElementById("level-filter")
            .value;


    /*
       Find schools that satisfy ALL conditions.
    */

    const filteredSchools = schools.filter(school => {

        // School must belong to current city
        const belongsToCity =
            school.city === currentCity;


        // School name must match search
        const matchesSearch =
            school.name
                .toLowerCase()
                .includes(searchText);


        // School level must match filter
        const matchesLevel =
            selectedLevel === "all" ||
            school.level === selectedLevel;


        return (
            belongsToCity &&
            matchesSearch &&
            matchesLevel
        );

    });


    // Display filtered results
    displaySchools(filteredSchools);
}



/* =====================================================
   6. SHOW SCHOOL DETAILS
===================================================== */

function showSchoolDetails(id) {

    const school = schools.find(s => s.id === id);
    if (!school) return;

    $("school-list").classList.add("hidden");

    const details = $("school-details");
    details.classList.remove("hidden");

    const programs = school.programs
        .map(p => `<span class="detail-tag">${p}</span>`)
        .join("");

    const facilities = school.facilities
        .map(f => `<span class="detail-tag">${f}</span>`)
        .join("");

    const posts = school.posts.length
        ? school.posts.map(post => `
            <article class="post-card">
                <span class="post-date">${post.date}</span>
                <h4>${post.title}</h4>
                <p>${post.text}</p>
            </article>
        `).join("")
        : `
            <div class="empty-content">
                <p>School posts and announcements will appear here.</p>
            </div>
        `;

    const reviews = school.reviews.length
        ? school.reviews.map(review => `
            <div class="review-card">
                <div class="review-stars">
                    ${"⭐".repeat(review.rating)}
                </div>
                <h4>${review.name}</h4>
                <p>${review.comment}</p>
            </div>
        `).join("")
        : `
            <div class="empty-content">
                <p>No reviews yet.</p>
                <button
                    class="view-school-btn"
                    onclick="showReviewForm(${school.id})">
                    Be the first to review
                </button>
            </div>
        `;

    const contact = [
        school.location && `
            <div class="contact-item">
                <strong>📍 Location</strong>
                <span>${school.location}</span>
            </div>
        `,

        school.phone && `
            <div class="contact-item">
                <strong>📞 Phone</strong>
                <span>${school.phone}</span>
            </div>
        `,

        school.email && `
            <div class="contact-item">
                <strong>✉ Email</strong>
                <span>${school.email}</span>
            </div>
        `,

        school.website && `
            <div class="contact-item">
                <strong>🌐 Website</strong>
                <span>${school.website}</span>
            </div>
        `,

        school.telegram && `
            <div class="contact-item">
                <strong>✈ Telegram</strong>
                <span>${school.telegram}</span>
            </div>
        `
    ].filter(Boolean).join("");

    details.innerHTML = `

        <div class="school-details-container">

            <button
                class="back-button"
                onclick="backToSchools()">
                ← Back to schools
            </button>


            <div class="school-profile-header">

                <div class="school-profile-image">
                    <span>
                        ${school.name.charAt(0)}
                    </span>
                </div>

                <div class="school-profile-title">

                    <span class="school-status">
                        Profile Listed
                    </span>

                    <h2>${school.name}</h2>

                    <p>📍 ${school.location}</p>

                    <p>${school.level}</p>

                </div>

            </div>


            <section class="profile-section">

                <span class="section-label">
                    ABOUT THE SCHOOL
                </span>

                <h3>About the School</h3>

                <p>
                    ${school.description}
                </p>

            </section>


            <section class="profile-section">

                <span class="section-label">
                    PROGRAMS
                </span>

                <h3>Education Programs</h3>

                <div class="detail-tags">
                    ${programs}
                </div>

            </section>


            <section class="profile-section">

                <span class="section-label">
                    FACILITIES
                </span>

                <h3>School Facilities</h3>

                <div class="detail-tags">
                    ${facilities}
                </div>

            </section>


            <section class="profile-section">

                <span class="section-label">
                    CONTACT
                </span>

                <h3>Contact Information</h3>

                <div class="contact-grid">
                    ${contact}
                </div>

            </section>


            <section class="profile-section">

                <span class="section-label">
                    SCHOOL NEWS
                </span>

                <h3>Latest Posts</h3>

                <div class="posts-container">
                    ${posts}
                </div>

            </section>


            <section class="profile-section">

                <span class="section-label">
                    REVIEWS
                </span>

                <h3>Student & Family Reviews</h3>

                <div class="reviews-container">
                    ${reviews}
                </div>

            </section>


            <div
                id="review-form-container"
                class="review-form-container hidden">
            </div>

        </div>
    `;

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}





/* =====================================================
   7. BACK TO SCHOOL LIST
===================================================== */

function backToSchools() {

    document
        .getElementById("school-details")
        .classList.add("hidden");


    document
        .getElementById("school-list")
        .classList.remove("hidden");


    // Display schools from current city again
    const citySchools = schools.filter(
        school => school.city === currentCity
    );


    displaySchools(citySchools);


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}



/* =====================================================
   8. BACK TO CITIES
===================================================== */

function showCities() {

    // Hide school list
    document
        .getElementById("school-list")
        .classList.add("hidden");


    // Hide school details
    document
        .getElementById("school-details")
        .classList.add("hidden");


    // Show cities
    document
        .getElementById("cities")
        .classList.remove("hidden");


    // Go to cities section
    document
        .getElementById("cities")
        .scrollIntoView({
            behavior: "smooth"
        });
}



/* =====================================================
   9. REVIEW FORM
===================================================== */

function showReviewForm(id) {

    const school = schools.find(
        school => school.id === id
    );


    if (!school) {
        return;
    }


    const container =
        document.getElementById(
            "review-form-container"
        );


    container.classList.remove("hidden");


    container.innerHTML = `

        <div class="review-form">

            <h3>
                Write a Review
            </h3>


            <input
                type="text"
                id="review-name"
                placeholder="Your name"
            >


            <select id="review-rating">

                <option value="5">
                    ⭐⭐⭐⭐⭐ — Excellent
                </option>

                <option value="4">
                    ⭐⭐⭐⭐ — Very Good
                </option>

                <option value="3">
                    ⭐⭐⭐ — Good
                </option>

                <option value="2">
                    ⭐⭐ — Fair
                </option>

                <option value="1">
                    ⭐ — Poor
                </option>

            </select>


            <textarea
                id="review-comment"
                placeholder="Write your experience..."
            ></textarea>


            <button
                class="view-school-btn"
                onclick="submitReview(${school.id})"
            >
                Submit Review
            </button>

        </div>

    `;


    container.scrollIntoView({
        behavior: "smooth"
    });
}



/* =====================================================
   10. SUBMIT REVIEW
===================================================== */

function submitReview(id) {

    const school = schools.find(
        school => school.id === id
    );


    if (!school) {
        return;
    }


    const name =
        document
            .getElementById("review-name")
            .value
            .trim();


    const rating =
        Number(
            document
                .getElementById("review-rating")
                .value
        );


    const comment =
        document
            .getElementById("review-comment")
            .value
            .trim();


    /* -----------------------------------------
       Validate
    ----------------------------------------- */

    if (!name) {

        alert("Please enter your name.");

        return;
    }


    if (!comment) {

        alert("Please write a review.");

        return;
    }


    /* -----------------------------------------
       Add review
    ----------------------------------------- */

    school.reviews.push({

        name: name,

        rating: rating,

        comment: comment

    });


    alert("Thank you! Your review has been submitted.");


    // Show school details again
    showSchoolDetails(id);
}

