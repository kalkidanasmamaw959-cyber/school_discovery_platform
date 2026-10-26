const REG_API_BASE =
    window.EDUCONNECT_API_BASE || "http://127.0.0.1:5000";

const registrationForm = document.getElementById("registration-form");

async function registrationApiBase() {
    if (window.EDUCONNECT_API_READY) {
        await window.EDUCONNECT_API_READY;
    }
    return window.EDUCONNECT_API_BASE || REG_API_BASE;
}

function registrationMessage(text, type = "") {
    const message = document.getElementById("registration-message");
    message.textContent = text;
    message.style.color =
        type === "success" ? "#067647" : type === "error" ? "#b42318" : "";
}

async function submitRegistration(event) {
    event.preventDefault();

    const schoolName = document.getElementById("school-name").value.trim();
    const city = document.getElementById("school-city").value;
    const level = document.getElementById("school-level").value;
    const address = document.getElementById("school-address").value.trim();
    const email = document.getElementById("school-email").value.trim();
    const phone = document.getElementById("school-phone").value.trim();
    const website = document.getElementById("school-website").value.trim();
    const telegram = document.getElementById("school-telegram").value.trim();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword =
        document.getElementById("confirm-password").value;
    const certificationNumber = document
        .getElementById("certification-number")
        .value.trim();
    const certificationIssuer = document
        .getElementById("certification-issuer")
        .value.trim();
    const certificationUrl = document
        .getElementById("certification-url")
        .value.trim();

    if (!schoolName || !city || !level || !address) {
        return registrationMessage(
            "Please complete all required school information.",
            "error"
        );
    }
    if (!email || !phone) {
        return registrationMessage(
            "Please provide a school email and phone number.",
            "error"
        );
    }
    if (!username) {
        return registrationMessage("Please choose a username.", "error");
    }
    if (password !== confirmPassword) {
        return registrationMessage("Passwords do not match.", "error");
    }
    if (password.length < 8) {
        return registrationMessage(
            "Password must contain at least 8 characters.",
            "error"
        );
    }
    if (!certificationNumber) {
        return registrationMessage(
            "Enter the Ministry of Education registration number.",
            "error"
        );
    }

    const button = registrationForm.querySelector(
        'button[type="submit"]'
    );
    button.disabled = true;
    button.textContent = "Creating account...";
    registrationMessage("Submitting registration...");
    const apiBase = await registrationApiBase();

    let response;
    try {
        response = await fetch(apiBase + "/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                school_name: schoolName,
                city,
                level,
                location: address,
                description: "",
                school_email: email,
                phone,
                website,
                telegram,
                username,
                password,
                confirm_password: confirmPassword,
                certification_number: certificationNumber,
                certification_issuer:
                    certificationIssuer || "Ministry of Education",
                certification_url: certificationUrl
            })
        });
    } catch (error) {
        registrationMessage(
            `Could not reach the backend at ${apiBase}. ` +
                "Start Flask and open the app through " +
                "http://127.0.0.1:5000/app/.",
            "error"
        );
        button.disabled = false;
        button.textContent = "Create School Account";
        return;
    }

    let payload = null;
    if (
        (response.headers.get("content-type") || "").includes(
            "application/json"
        )
    ) {
        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }
    }

    if (!response.ok) {
        let message =
            (payload && payload.error) ||
            `Registration failed (HTTP ${response.status}).`;
        if (response.status === 404) {
            message =
                `The registration endpoint was not found at ${apiBase}. ` +
                "Another program may be using that port. Start Flask and " +
                "open the app through http://127.0.0.1:5000/app/.";
        }
        registrationMessage(message, "error");
        button.disabled = false;
        button.textContent = "Create School Account";
        return;
    }

    if (!payload || !payload.token || !payload.user) {
        registrationMessage(
            "The backend returned an incomplete registration response. " +
                "Restart Flask and try again.",
            "error"
        );
        button.disabled = false;
        button.textContent = "Create School Account";
        return;
    }

    [sessionStorage, localStorage].forEach((storage) => {
        storage.removeItem("educonnect_token");
        storage.removeItem("educonnect_user");
        storage.removeItem("educonnect_school");
    });
    sessionStorage.setItem("educonnect_token", payload.token);
    sessionStorage.setItem("educonnect_user", JSON.stringify(payload.user));
    sessionStorage.setItem(
        "educonnect_school",
        JSON.stringify(payload.school)
    );

    registrationMessage(
        "School account created. Your certification is pending " +
            "administrator review. Redirecting to your dashboard...",
        "success"
    );
    button.textContent = "Account created";

    setTimeout(() => {
        window.location.href = "dashboard.html";
    }, 1200);
}

if (registrationForm) {
    registrationForm.addEventListener("submit", submitRegistration);
}
