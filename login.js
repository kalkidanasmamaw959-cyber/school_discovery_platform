const loginForm = document.getElementById("login-form");

loginForm.addEventListener("submit", function (event) {

    event.preventDefault();

    const username =
        document.getElementById("login-username").value.trim();

    const password =
        document.getElementById("login-password").value;

    const message =
        document.getElementById("login-message");

    if (username === "") {
        message.textContent =
            "Please enter your username or email.";
        message.style.color = "red";
        return;
    }

    if (password === "") {
        message.textContent =
            "Please enter your password.";
        message.style.color = "red";
        return;
    }

    // Frontend demo only
    message.textContent = "Login successful! Redirecting...";
    message.style.color = "green";

    setTimeout(function () {
        window.location.href = "dashboard.html";
    }, 1000);
});