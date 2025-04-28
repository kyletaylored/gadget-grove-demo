// SPA Router for GadgetGrove Shop
document.addEventListener('DOMContentLoaded', function () {
    // Initialize router
    const router = {
        currentPath: '/',
        routes: {
            '/': showHomePage,
            '/category': showCategoryPage,
            '/product': showProductPage
        },

        // Navigate to a path
        navigate: function (path) {
            // Update URL without page refresh
            window.history.pushState(null, null, path);

            // Handle the route
            this.handleRoute(path);

            // Track page view with analytics
            trackPageView(path);
        },

        // Handle current route
        handleRoute: function (path) {
            if (path !== '/' && path.endsWith('/')) {
                path = path.slice(0, -1);
            }

            this.currentPath = path;

            // Hide all page views
            document.querySelectorAll('.page-view').forEach(view => {
                view.style.display = 'none';
            });

            // Reset active classes
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });

            // Routing rules
            if (path === '/') {
                this.routes['/'](path);
            } else if (path.startsWith('/category/') && path.includes('/product/')) {
                this.routes['/product'](path);
            } else if (path.startsWith('/category/')) {
                this.routes['/category'](path);
            } else {
                this.routes['/'](path);
            }
        }

    };

    // Route handlers
    function showHomePage(path) {
        // Show home view
        document.getElementById('home-view').style.display = 'block';

        // Set active nav item
        document.querySelector('[data-route="/"]').classList.add('active');

        // Update document title
        document.title = 'GadgetGrove Shop';
    }

    function showCategoryPage(path) {
        const categorySlug = path.replace('/category/', '');

        const categoryView = document.getElementById(`category-${categorySlug}-view`);
        if (categoryView) {
            categoryView.style.display = 'block';

            document.querySelector(`[data-route="${path}"]`)?.classList.add('active');

            const categoryTitle = categorySlug.split('-').map(word =>
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ');

            document.title = `${categoryTitle} - GadgetGrove Shop`;

            if (window.analytics) {
                window.analytics.track('view_category', {
                    category: categoryTitle
                });
            }

            // Re-initialize Add to Cart buttons
            window.initializeAddToCartButtons && window.initializeAddToCartButtons();
        } else {
            router.navigate('/');
        }
    }


    function showProductPage(path) {
        const match = path.match(/^\/category\/([^\/]+)\/product\/(.+)$/);

        if (match) {
            const categorySlug = match[1];
            const productId = match[2];

            const productView = document.getElementById(`product-${productId}-view`);
            if (productView) {
                productView.style.display = 'block';

                const product = window.PRODUCT_DATA[productId];
                if (product) {
                    document.title = `${product.name} - GadgetGrove Shop`;

                    // Highlight correct category
                    document.querySelector(`[data-route="/category/${categorySlug}"]`)?.classList.add('active');
                }
                // Re-initialize Add to Cart buttons
                window.initializeAddToCartButtons && window.initializeAddToCartButtons();
            } else {
                router.navigate('/');
            }
        } else {
            router.navigate('/');
        }
    }

    // Track page views with analytics
    function trackPageView(path) {
        if (window.analytics) {
            window.analytics.page({
                path: path,
                title: document.title,
                url: window.location.href,
                referrer: document.referrer || undefined
            });

            console.log(`[Analytics] Page view tracked: ${path}`);
        } else {
            console.warn('[Analytics] Analytics library not loaded yet.');
        }
    }


    // Attach click handlers to navigation links
    document.querySelectorAll('[data-route]').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const route = this.getAttribute('data-route');
            router.navigate(route);
        });
    });

    // Handle product links
    document.querySelectorAll('.product-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const route = this.getAttribute('data-route');
            router.navigate(route);
        });
    });

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function () {
        const path = window.location.pathname;
        router.handleRoute(path);
        trackPageView(path);
    });

    // Initialize router with current path or default to home
    let initialPath = window.location.pathname;
    if (initialPath === '/shop' || initialPath === '/shop/') {
        initialPath = '/';
    }
    router.handleRoute(initialPath);
});