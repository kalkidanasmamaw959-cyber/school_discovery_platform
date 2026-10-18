// ==========================================
// EDUCONNECT ETHIOPIA - SCHOOL DASHBOARD
// ==========================================
// PROFILE ELEMENTS
const editButton = document.getElementById("edit-profile-btn");
const quickEditButton = document.getElementById("quick-edit-profile-btn");
const profileDisplay = document.getElementById("profile-display");
const profileForm = document.getElementById("profile-form");
const cancelButton = document.getElementById("cancel-profile-btn");
const message = document.getElementById("profile-message");

// PROFILE FORM FIELDS
const fields = {
    name: document.getElementById("edit-school-name"),
    city: document.getElementById("edit-city"),
    level: document.getElementById("edit-level"),
    email: document.getElementById("edit-email"),
    phone: document.getElementById("edit-phone"),
    address: document.getElementById("edit-address"),
    website: document.getElementById("edit-website"),
    telegram: document.getElementById("edit-telegram")
};
// DEFAULT DEMONSTRATION PROFILE
const defaultProfile = {
    name: "SOS School",
    city: "Bahir Dar",
    level: "Primary & Secondary",
    email: "school@example.com",
    phone: "+251 900 000 000",
    address: "Bahir Dar, Ethiopia",
    website: "",
    telegram: ""
};
let schoolProfile = { ...defaultProfile };
// LOAD SAVED PROFILE
try {
    const savedProfile = localStorage.getItem("eduConnectSchoolProfile");

    if (savedProfile) {
        schoolProfile = {
            ...defaultProfile,
            ...JSON.parse(savedProfile)
        };
    }
} catch (error) {
    console.error("Could not load the saved profile:", error);
}

// DISPLAY PROFILE INFORMATION
function displayProfile() {
    document.getElementById("display-school-name").textContent =
        schoolProfile.name;

    document.getElementById("display-city").textContent =
        schoolProfile.city;

    document.getElementById("display-level").textContent =
        schoolProfile.level;

    document.getElementById("display-email").textContent =
        schoolProfile.email;

    document.getElementById("display-phone").textContent =
        schoolProfile.phone;

    document.getElementById("display-address").textContent =
        schoolProfile.address;

    document.getElementById("display-website").textContent =
        schoolProfile.website || "Not provided";

    document.getElementById("display-telegram").textContent =
        schoolProfile.telegram || "Not provided";

    document.querySelectorAll(".dashboard-school-name").forEach(element => {
        element.textContent = schoolProfile.name;
    });
}
// FILL EDIT FORM
function fillProfileForm() {
    fields.name.value = schoolProfile.name;
    fields.city.value = schoolProfile.city;
    fields.level.value = schoolProfile.level;
    fields.email.value = schoolProfile.email;
    fields.phone.value = schoolProfile.phone;
    fields.address.value = schoolProfile.address;
    fields.website.value = schoolProfile.website;
    fields.telegram.value = schoolProfile.telegram;
}
// OPEN PROFILE FORM
function openProfileForm() {
    fillProfileForm();
    profileDisplay.hidden = true;
    profileForm.hidden = false;
    message.textContent = "";
    fields.name.focus();
}
editButton.addEventListener("click", openProfileForm);
quickEditButton.addEventListener("click", openProfileForm);

// CANCEL PROFILE EDITING
cancelButton.addEventListener("click", function () {
    profileForm.hidden = true;
    profileDisplay.hidden = false;
    message.textContent = "";
});

// SAVE PROFILE CHANGES
profileForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const updatedProfile = {
        name: fields.name.value.trim(),
        city: fields.city.value,
        level: fields.level.value,
        email: fields.email.value.trim(),
        phone: fields.phone.value.trim(),
        address: fields.address.value.trim(),
        website: fields.website.value.trim(),
        telegram: fields.telegram.value.trim()
    };

    try {
        localStorage.setItem(
            "eduConnectSchoolProfile",
            JSON.stringify(updatedProfile)
        );

        schoolProfile = updatedProfile;
        displayProfile();

        profileForm.hidden = true;
        profileDisplay.hidden = false;
        message.textContent = "";

        alert("School profile updated successfully!");
    } catch (error) {
        message.textContent =
            "Could not save changes in this browser.";
        message.style.color = "red";
    }
});
// ==========================================
// PHOTO UPLOAD PREVIEW
// ==========================================
const addPhotosButton = document.getElementById("add-photos-btn");
const photoInput = document.getElementById("school-photo-input");
const photoPreview = document.getElementById("school-photo-preview");
const photoCount = document.getElementById("photo-count");

let selectedPhotos = [];

addPhotosButton.addEventListener("click", function () {
    photoInput.click();
});

function displayPhotos() {
    photoPreview.replaceChildren();

    selectedPhotos.forEach(function (photo) {
        const image = document.createElement("img");

        image.src = photo.url;
        image.alt = photo.name;
        image.className = "school-photo";

        photoPreview.appendChild(image);
    });

    photoCount.textContent = selectedPhotos.length;
}

photoInput.addEventListener("change", function () {
    const files = Array.from(photoInput.files);

    files.forEach(function (file) {
        if (!file.type.startsWith("image/")) {
            return;
        }

        const photoURL = URL.createObjectURL(file);

        selectedPhotos.push({
            name: file.name,
            url: photoURL
        });
    });

    displayPhotos();

    // Allow selecting the same file again
    photoInput.value = "";
});

// ==========================================
// CREATE SCHOOL POSTS
// ==========================================

const createPostButton = document.getElementById("create-post-btn");
const schoolPosts = document.getElementById("school-posts");
const postCount = document.getElementById("post-count");
const noPostsMessage = document.getElementById("no-posts-message");

let posts = [];

function displayPosts() {
    // Remove previously displayed posts
    schoolPosts.querySelectorAll(".school-post").forEach(function (post) {
        post.remove();
    });

    posts.forEach(function (postData) {
        const post = document.createElement("article");
        post.className = "school-post";

        const content = document.createElement("p");
        content.textContent = postData.text;

        const date = document.createElement("small");
        date.textContent = postData.date;

        post.appendChild(content);
        post.appendChild(date);
        schoolPosts.appendChild(post);
    });

    postCount.textContent = posts.length;
    noPostsMessage.hidden = posts.length > 0;
}

createPostButton.addEventListener("click", function () {
    const postText = prompt("Write a post or announcement about your school:");

    if (postText === null || postText.trim() === "") {
        return;
    }

    posts.unshift({
        text: postText.trim(),
        date: new Date().toLocaleString()
    });

    displayPosts();
});
// ==========================================
// INITIALIZE DASHBOARD
// ==========================================
displayProfile();
displayPosts();
displayPhotos();


