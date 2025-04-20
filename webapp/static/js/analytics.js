/**
 * GadgetGrove Analytics
 * Tracks user behavior and sends it to RabbitMQ via the backend
 */
document.addEventListener('DOMContentLoaded', function () {
    // Initialize analytics
    const analytics = window._analytics.Analytics({
        app: 'gadgetgrove',
        version: '1.0.0',
        plugins: [
            rabbitMQPlugin({
                endpoint: '/api/analytics',
                trackPageViews: true,
                trackClicks: true,
                trackFormSubmissions: true,
                debug: false,
                // Enrich each event with user and session data
                enrichEventData: (data) => {
                    // Add session ID if available
                    const sessionId = document.querySelector('meta[name="session-id"]')?.getAttribute('content');
                    if (sessionId) {
                        data.sessionId = sessionId;
                    }

                    // Add user ID if available
                    const userId = document.querySelector('meta[name="user-id"]')?.getAttribute('content');
                    if (userId) {
                        data.userId = userId;
                    }

                    return data;
                }
            })
        ]
    });

    // Track initial page view
    analytics.page();

    // Track product views and add-to-cart events
    initEcommerceTracking(analytics);

    // Track user identification
    initUserTracking(analytics);
});

/**
 * Initialize e-commerce tracking
 */
function initEcommerceTracking(analytics) {
    // Track "Add to Cart" events
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function () {
            try {
                const productId = this.getAttribute('data-product-id');
                const productData = window.PRODUCT_DATA[productId];
                if (productData) {
                    analytics.track('add_to_cart', {
                        product_id: productData.id,
                        name: productData.name,
                        brand: productData.brand,
                        category: productData.category,
                        price: productData.price,
                        quantity: 1
                    });
                }
            } catch (error) {
                console.error('Error tracking add to cart event:', error);
            }
        });
    });

    // Track successful purchase
    const successModal = document.getElementById('orderSuccessModal');
    if (successModal) {
        // Use MutationObserver to detect when modal becomes visible
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.attributeName === 'class' &&
                    successModal.classList.contains('show')) {
                    // Modal is shown - track purchase
                    const orderId = Math.random().toString(36).substring(2, 15);
                    const total = parseFloat(document.getElementById('cart-total')?.textContent || '0');

                    // Track purchase completion
                    analytics.track('purchase', {
                        transaction_id: orderId,
                        value: total
                    });
                }
            });
        });

        observer.observe(successModal, { attributes: true });
    }
}

/**
 * Initialize user tracking
 */
function initUserTracking(analytics) {
    // Track user login/session start
    const userId = document.querySelector('meta[name="user-id"]')?.getAttribute('content');
    const userName = document.querySelector('meta[name="user-name"]')?.getAttribute('content');
    const userEmail = document.querySelector('meta[name="user-email"]')?.getAttribute('content');

    if (userId) {
        // Identify the user
        analytics.identify(userId, {
            name: userName,
            email: userEmail
        });
    }

    // Track logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function () {
            analytics.track('logout');
        });
    }
}