const LOGIN_API_BASE =
    window.EDUCONNECT_API_BASE || "http://127.0.0.1:5000";

const loginForm = document.getElementById("login-form");

async function loginApiBase() {
    if (window.EDUCONNECT_API_READY) {
        await window.EDUCONNECT_API_READY;
    }
    return window.EDUCONNECT_API_BASE || LOGIN_API_BASE;
}

function loginMessage(text, type = "") {
    const message = document.getElementById("login-message");
    message.textContent = text;
    message.style.color =
        type === "success" ? "#067647" : type === "error" ? "#b42318" : "";
}

function persistSession(payload, remember) {
    const storage = remember ? localStorage : sessionStorage;
    const other = remember ? sessionStorage : localStorage;

    other.removeItem("educonnect_token");
    other.removeItem("educonnect_user");
    other.removeItem("educonnect_school");

    storage.setItem("educonnect_token", payload.token);
    storage.setItem("educonnect_user", JSON.stringify(payload.user));
    if (payload.school) {
        storage.setItem(
            "educonnect_school",
            JSON.stringify(payload.school)
        );
    } else {
        storage.removeItem("educonnect_school");
    }
}

async function submitLogin(event) {
    event.preventDefault();

    const identifier = document
        .getElementById("login-username")
        .value.trim();
    const password = document.getElementById("login-password").value;
    const remember = document.getElementById("remember-me").checked;

    if (!identifier) {
        return loginMessage("Please enter your username or email.", "error");
    }
    if (!password) {
        return loginMessage("Please enter your password.", "error");
    }

    const button = loginForm.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = "Signing in...";
    loginMessage("");

    const apiBase = await loginApiBase();

    let response;
    try {
        response = await fetch(apiBase + "/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                identifier,
                password,
                remember
            })
        });
    } catch (error) {
        loginMessage(
            `Could not reach the backend at ${apiBase}. ` +
                "Start Flask, then open the app through " +
                "http://127.0.0.1:5000/app/.",
            "error"
        );
        button.disabled = false;
        button.textContent = "Sign In";
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
            "Sign in failed. Please try again.";
        if (response.status === 404) {
            message =
                `The sign-in endpoint was not found at ${apiBase}. ` +
                "Another program may be using that port. Start Flask and " +
                "open the app through http://127.0.0.1:5000/app/.";
        }
        loginMessage(message, "error");
        button.disabled = false;
        button.textContent = "Sign In";
        return;
    }

    if (!payload || !payload.token || !payload.user) {
        loginMessage(
            "The backend returned an incomplete sign-in response. " +
                "Restart Flask and try again.",
            "error"
        );
        button.disabled = false;
        button.textContent = "Sign In";
        return;
    }

    persistSession(payload, remember);
    loginMessage("Signed in successfully. Redirecting...", "success");
    button.textContent = "Signed in";

    setTimeout(() => {
        window.location.href =
            payload.redirect === "admin.html"
                ? "admin.html"
                : "dashboard.html";
    }, 500);
}

if (loginForm) {
    loginForm.addEventListener("submit", submitLogin);
}
window.EDUCONNECT_LOGIN_READY = true;
