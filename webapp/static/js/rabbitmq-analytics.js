/**
 * RabbitMQ plugin for analytics library
 * This sends analytics events to a RabbitMQ server
 */
function rabbitMQPlugin(userConfig = {}) {
    // Initialize with defaults
    const config = {
        endpoint: '/api/analytics',
        trackPageViews: true,
        trackClicks: false,
        trackFormSubmissions: false,
        queueName: 'analytics_events',
        enrichEventData: (data) => data,
        debug: false,
        ...userConfig
    };

    // Return analytics plugin object
    return {
        name: 'rabbitmq-analytics',
        config,

        // Lifecycle methods
        initialize: ({ payload }) => {
            if (config.debug) {
                console.log('[RabbitMQ Analytics] Initialized with config:', config);
            }
            return { config };
        },

        // Track page views
        page: ({ payload, config }) => {
            if (!config.trackPageViews) return;

            const eventData = {
                type: 'page_view',
                url: window.location.href,
                path: window.location.pathname,
                title: document.title,
                referrer: document.referrer,
                timestamp: new Date().toISOString(),
                ...config.enrichEventData(payload)
            };

            sendToRabbitMQ(eventData, config);

            return eventData;
        },

        // Track events
        track: ({ payload, config }) => {
            const eventData = {
                type: 'custom_event',
                event: payload.event,
                timestamp: new Date().toISOString(),
                properties: payload.properties || {},
                ...config.enrichEventData(payload)
            };

            sendToRabbitMQ(eventData, config);

            return eventData;
        },

        // Track user identification
        identify: ({ payload, config }) => {
            const eventData = {
                type: 'identify',
                userId: payload.userId,
                traits: payload.traits || {},
                timestamp: new Date().toISOString(),
                ...config.enrichEventData(payload)
            };

            sendToRabbitMQ(eventData, config);

            return eventData;
        }
    };
}

// Helper function to send data to the RabbitMQ endpoint
function sendToRabbitMQ(eventData, config) {
    // Add session information if available
    if (localStorage.getItem('analytics_session_id')) {
        eventData.sessionId = localStorage.getItem('analytics_session_id');
    } else {
        const sessionId = generateSessionId();
        localStorage.setItem('analytics_session_id', sessionId);
        eventData.sessionId = sessionId;
    }

    // Add queue name if configured
    if (config.queueName) {
        eventData.queueName = config.queueName;
    }

    // Log in debug mode
    if (config.debug) {
        console.log('[RabbitMQ Analytics] Sending event:', eventData);
    }

    // Send to server endpoint
    fetch(config.endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(eventData),
        // Don't block page load with the request
        keepalive: true
    }).catch(error => {
        if (config.debug) {
            console.error('[RabbitMQ Analytics] Error sending event:', error);
        }
    });
}

// Helper to generate a unique session ID
function generateSessionId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}