const form = document.getElementById("registration-form");

form.addEventListener("submit", function (event) {

    event.preventDefault();

    const schoolName = document.getElementById("school-name").value.trim();
    const city = document.getElementById("school-city").value;
    const level = document.getElementById("school-level").value;
    const address = document.getElementById("school-address").value.trim();

    const email = document.getElementById("school-email").value.trim();
    const phone = document.getElementById("school-phone").value.trim();

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword =
        document.getElementById("confirm-password").value;

    const message =
        document.getElementById("registration-message");


    // Check password
    if (password !== confirmPassword) {

        message.textContent = "Passwords do not match.";
        message.style.color = "red";

        return;
    }


    // Check password length
    if (password.length < 6) {

        message.textContent =
            "Password must contain at least 6 characters.";

        message.style.color = "red";

        return;
    }


    // Temporary success
    message.textContent =
        "Registration submitted successfully! Your school is now pending verification.";

    message.style.color = "green";


    console.log("School Registration:");

    console.log({
        schoolName,
        city,
        level,
        address,
        email,
        phone,
        username
    });

});