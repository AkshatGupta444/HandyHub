
let selectedProvider = null;

async function api(url, options = {}) {

    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.error || "Something went wrong"
        );
    }

    return data;
}


async function loadServices() {

    const data = await api("/api/services");

    const serviceSelect =
        document.getElementById("service");

    if (serviceSelect) {

        data.forEach(service => {

            serviceSelect.insertAdjacentHTML(
                "beforeend",
                `<option value="${service.id}">
                    ${service.name}
                </option>`
            );

        });
    }

    const registerService =
        document.getElementById("registerService");

    if (registerService) {

        registerService.innerHTML =
            '<option value="">Select Service</option>' +
            data.map(service =>
                `<option value="${service.id}">
                    ${service.name}
                </option>`
            ).join("");

    }
}


async function loadProviders() {

    const grid =
        document.getElementById("providerGrid");

    if (!grid) {
        return;
    }

    grid.innerHTML = "Loading providers...";

    const q =
        encodeURIComponent(
            document.getElementById("search")?.value || ""
        );

    const city =
        encodeURIComponent(
            document.getElementById("city")?.value || ""
        );

    const service =
        document.getElementById("service")?.value || "";

    try {

        const data = await api(
            `/api/providers?q=${q}&city=${city}&service=${service}`
        );

        if (!data.length) {

            grid.innerHTML =
                "<p>No matching providers found.</p>";

            return;
        }

        grid.innerHTML = data.map(provider => `

            <article class="card">

                <div class="avatar">
                    ${provider.name.charAt(0).toUpperCase()}
                </div>

                <h3>
                    ${escapeHtml(provider.name)}
                </h3>

                <div class="meta">
                    ${escapeHtml(provider.service)}
                    •
                    ${escapeHtml(provider.city || "")}
                </div>

                <div class="meta">
                    ${provider.experience}
                    years experience
                </div>

                <div class="price">
                    ₹${Number(provider.price)
                        .toLocaleString("en-IN")}
                    starting
                </div>

                <button
                    class="btn"
                    onclick='openRequest(${JSON.stringify(provider)})'
                >
                    Request Service
                </button>

            </article>

        `).join("");

    } catch (error) {

        grid.innerHTML =
            `<p>${escapeHtml(error.message)}</p>`;

    }
}


function openRequest(provider) {

    selectedProvider = provider;

    document.getElementById(
        "modalInfo"
    ).innerHTML = `
        <p>
            <strong>
                ${escapeHtml(provider.name)}
            </strong>
            —
            ${escapeHtml(provider.service)}
            in
            ${escapeHtml(provider.city || "")}
        </p>
    `;

    document.getElementById(
        "description"
    ).value = "";

    document.getElementById(
        "modal"
    ).classList.remove("hidden");
}


function closeModal() {

    document.getElementById(
        "modal"
    ).classList.add("hidden");

}


async function submitRequest() {

    if (!selectedProvider) {
        return;
    }

    const description =
        document.getElementById(
            "description"
        ).value.trim();

    if (!description) {

        alert(
            "Please describe the service you need."
        );

        return;
    }

    try {

        const result = await api(
            "/api/requests",
            {
                method: "POST",

                body: JSON.stringify({
                    provider_id:
                        selectedProvider.id,

                    service_id:
                        selectedProvider.service_id,

                    description:
                        description
                })
            }
        );

        alert(
            result.message +
            " (#" +
            result.request_id +
            ")"
        );

        closeModal();

    } catch (error) {

        if (
            error.message.includes(
                "Authentication"
            )
        ) {

            window.location.href =
                "/login";

        } else {

            alert(error.message);

        }
    }
}


async function logout() {

    await api(
        "/api/logout",
        {
            method: "POST"
        }
    );

    window.location.href = "/";
}


function escapeHtml(value) {

    return String(value ?? "").replace(
        /[&<>"']/g,

        character => ({

            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"

        }[character])
    );
}


async function loadRequests() {

    const box =
        document.getElementById("requests");

    if (!box) {
        return;
    }

    try {

        const data =
            await api("/api/requests");

        if (!data.length) {

            box.innerHTML =
                "<p>No service requests yet.</p>";

            return;
        }

        box.innerHTML = data.map(request => {

            const person =
                request.provider_name ||
                request.customer_name ||
                "User";

            return `

                <div class="request">

                    <strong>
                        ${escapeHtml(request.service)}
                    </strong>

                    <span class="status">
                        ${escapeHtml(request.status)}
                    </span>

                    <p>
                        ${escapeHtml(
                            request.description
                        )}
                    </p>

                    <small>
                        With:
                        ${escapeHtml(person)}
                    </small>

                    <br><br>

                    ${
                        request.status === "Pending"
                        ?
                        `<button
                            class="btn small"
                            onclick="changeStatus(
                                ${request.id},
                                'Cancelled'
                            )"
                        >
                            Cancel
                        </button>`
                        :
                        ""
                    }

                    ${
                        request.customer_name
                        ?
                        `<button
                            class="btn small"
                            onclick="changeStatus(
                                ${request.id},
                                'Accepted'
                            )"
                        >
                            Accept
                        </button>

                        <button
                            class="btn small"
                            onclick="changeStatus(
                                ${request.id},
                                'Rejected'
                            )"
                        >
                            Reject
                        </button>`
                        :
                        ""
                    }

                    ${
                        request.status === "Accepted"
                        ?
                        `<button
                            class="btn small"
                            onclick="changeStatus(
                                ${request.id},
                                'Completed'
                            )"
                        >
                            Complete
                        </button>`
                        :
                        ""
                    }

                </div>
            `;

        }).join("");

    } catch (error) {

        box.innerHTML =
            `<p>${escapeHtml(error.message)}</p>`;

    }
}


async function changeStatus(id, status) {

    try {

        await api(
            `/api/requests/${id}`,
            {
                method: "PATCH",

                body: JSON.stringify({
                    status: status
                })
            }
        );

        loadRequests();

    } catch (error) {

        alert(error.message);

    }
}


document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadServices().catch(console.error);

        loadProviders().catch(console.error);

        loadRequests();

        const role =
            document.getElementById("role");

        if (role) {

            role.addEventListener(
                "change",
                () => {

                    document
                        .getElementById(
                            "providerFields"
                        )
                        .classList.toggle(
                            "hidden",
                            role.value !== "provider"
                        );

                }
            );

        }


        const loginForm =
            document.getElementById(
                "loginForm"
            );

        if (loginForm) {

            loginForm.addEventListener(
                "submit",
                async event => {

                    event.preventDefault();

                    const formData =
                        new FormData(loginForm);

                    try {

                        await api(
                            "/api/login",
                            {
                                method: "POST",

                                body: JSON.stringify(
                                    Object.fromEntries(
                                        formData
                                    )
                                )
                            }
                        );

                        window.location.href =
                            "/dashboard";

                    } catch (error) {

                        document
                            .getElementById(
                                "message"
                            )
                            .textContent =
                            error.message;

                    }

                }
            );

        }


        const registerForm =
            document.getElementById(
                "registerForm"
            );

        if (registerForm) {

            registerForm.addEventListener(
                "submit",
                async event => {

                    event.preventDefault();

                    const formData =
                        new FormData(
                            registerForm
                        );

                    try {

                        await api(
                            "/api/register",
                            {
                                method: "POST",

                                body: JSON.stringify(
                                    Object.fromEntries(
                                        formData
                                    )
                                )
                            }
                        );

                        window.location.href =
                            "/dashboard";

                    } catch (error) {

                        document
                            .getElementById(
                                "message"
                            )
                            .textContent =
                            error.message;

                    }

                }
            );

        }

    }
);

    
document.getElementById("modal")?.addEventListener("click", function(event) {
    if (event.target === this) {
        this.classList.add("hidden");
    }
});



// ===== FORCE MODAL CLOSE =====
document.addEventListener("DOMContentLoaded", function () {

    const modal = document.getElementById("modal");

    const closeButton = document.querySelector(".close");

    if (closeButton && modal) {

        closeButton.addEventListener("click", function (event) {

            event.preventDefault();
            event.stopPropagation();

            modal.classList.add("hidden");
            modal.style.display = "none";

        });

    }

    // Close when clicking outside the white popup
    if (modal) {

        modal.addEventListener("click", function (event) {

            if (event.target === modal) {

                modal.classList.add("hidden");
                modal.style.display = "none";

            }

        });

    }

});
