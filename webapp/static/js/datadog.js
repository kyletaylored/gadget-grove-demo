window.DD_RUM &&
    window.DD_RUM.init({
        clientToken: dd_rum_config.clientToken,
        applicationId: dd_rum_config.applicationId,
        site: dd_rum_config.site,
        service: "gadget-grove-web-ui",
        env: "podman",
        version: "1.0.1",
        sessionSampleRate: 100,
        sessionReplaySampleRate: 100,
        defaultPrivacyLevel: "mask-user-input",
        allowedTracingUrls: [
            "localhost",
            "127.0.0.1",
            (url) => url.length > 0,
        ],
    });