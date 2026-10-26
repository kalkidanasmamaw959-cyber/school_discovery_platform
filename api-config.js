(function () {
    const defaultPort = "5000";
    const fallbackPorts = ["5000", "5001"];
    const isFile = window.location.protocol === "file:";
    const servedByFlask =
        !isFile &&
        (window.location.pathname.startsWith("/app/") ||
            fallbackPorts.includes(window.location.port));

    if (window.EDUCONNECT_API_BASE) {
        window.EDUCONNECT_API_READY = Promise.resolve(
            window.EDUCONNECT_API_BASE
        );
        return;
    }

    if (servedByFlask) {
        window.EDUCONNECT_API_BASE = window.location.origin;
        window.EDUCONNECT_API_READY = Promise.resolve(
            window.EDUCONNECT_API_BASE
        );
        return;
    }

    window.EDUCONNECT_API_BASE = `http://127.0.0.1:${defaultPort}`;
    window.EDUCONNECT_API_READY = (async () => {
        for (const port of fallbackPorts) {
            const base = `http://127.0.0.1:${port}`;
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 1800);
            try {
                const response = await fetch(base + "/api/health", {
                    cache: "no-store",
                    signal: controller.signal
                });
                clearTimeout(timeout);
                if (!response.ok) continue;
                const payload = await response.json();
                if (payload && payload.status === "healthy") {
                    window.EDUCONNECT_API_BASE = base;
                    return base;
                }
            } catch (error) {
                clearTimeout(timeout);
            }
        }
        return window.EDUCONNECT_API_BASE;
    })();
})();
