/**
 * GadgetGrove Shop - Cart and Checkout Functionality
 */
document.addEventListener('DOMContentLoaded', function () {
    // Clean up any modal mess that might exist on page load
    cleanupModals();

    // Initialize or load cart from localStorage
    let cart = JSON.parse(localStorage.getItem("cart") || "[]");

    // Constants for calculations
    const TAX_RATE = 0.0725;
    const SHIPPING_THRESHOLD = 75;
    const SHIPPING_COST = 9.99;

    // Elements
    const cartCountElement = document.getElementById('cart-count');
    const cartItemsElement = document.getElementById('cart-items');
    const cartSubtotalElement = document.getElementById('cart-subtotal');
    const cartShippingElement = document.getElementById('cart-shipping');
    const cartTaxElement = document.getElementById('cart-tax');
    const cartTotalElement = document.getElementById('cart-total');
    const emptyCartMessage = document.getElementById('empty-cart-message');
    const cartItemsContainer = document.getElementById('cart-items-container');
    const checkoutForm = document.getElementById('checkout-form');

    // Initialize modals if they exist
    const orderSuccessModal = document.getElementById('orderSuccessModal') ?
        new bootstrap.Modal(document.getElementById('orderSuccessModal')) : null;
    const orderErrorModal = document.getElementById('orderErrorModal') ?
        new bootstrap.Modal(document.getElementById('orderErrorModal')) : null;

    // Event Listeners

    // Add to cart buttons
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function () {
            try {
                const productId = this.getAttribute('data-product-id');
                const productData = window.PRODUCT_DATA[productId];
                if (productData) {
                    addToCart(productData);
                }
            } catch (error) {
                console.error('Error adding product to cart:', error);
            }
        });
    });

    /**
     * Clean up Bootstrap modal mess
     * This helps fix issues with stuck modals and backdrops
     */
    function cleanupModals() {
        // Remove any stuck backdrops
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());

        // Fix body classes
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';

        // Reset any open modals
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            modal.classList.remove('show');
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
            modal.removeAttribute('aria-modal');
            modal.removeAttribute('role');
        });
    }

    // Handle the "Try Again" button in error modal
    document.getElementById('try-again-btn')?.addEventListener('click', function () {
        // Hide error modal properly
        if (orderErrorModal) {
            orderErrorModal.hide();

            // Clean up any modal mess
            setTimeout(cleanupModals, 300);

            // After cleanup, try again
            setTimeout(submitOrder, 500);
        } else {
            submitOrder();
        }
    });

    // Checkout form
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function (e) {
            e.preventDefault();
            submitOrder();
        });
    }

    // Cart Functions

    /**
     * Add a product to the cart
     */
    function addToCart(product) {
        // Check if product is already in cart
        const existingItemIndex = cart.findIndex(item =>
            item.id === product.id
        );

        // Track product view for Datadog RUM
        window.DD_RUM && window.DD_RUM.addAction('add_to_cart', product);


        if (existingItemIndex >= 0) {
            // Update quantity if product already exists
            cart[existingItemIndex].quantity = (cart[existingItemIndex].quantity || 1) + 1;
        } else {
            // Add new product with quantity 1
            product.quantity = 1;
            cart.push(product);
        }

        // Save cart to localStorage and update UI
        saveCart();
        renderCart();
    }

    /**
     * Remove an item from the cart
     */
    function removeItem(item, index) {
        cart.splice(index, 1);
        saveCart();
        renderCart();

        // Track product view for Datadog RUM
        window.DD_RUM && window.DD_RUM.addAction('remove_from_cart', item);
    }

    /**
     * Update the quantity of an item
     */
    function updateQuantity(item, index, newQuantity) {
        if (index >= 0 && index < cart.length) {
            newQuantity = parseInt(newQuantity);

            if (newQuantity < 1) {
                removeItem(item, index);
            } else {
                cart[index].quantity = newQuantity;
                saveCart();
                renderCart();

                // Track product view for Datadog RUM
                window.DD_RUM && window.DD_RUM.addAction('update_quantity', { ...item, quantity: newQuantity });
            }
        }
    }

    /**
     * Calculate cart totals
     */
    function calculateTotals() {
        const subtotal = cart.reduce((sum, item) => {
            const price = parseFloat(item.price);
            const quantity = item.quantity || 1;
            return sum + (price * quantity);
        }, 0);

        const shipping = subtotal >= SHIPPING_THRESHOLD ? 0 : SHIPPING_COST;
        const tax = subtotal * TAX_RATE;
        const total = subtotal + shipping + tax;

        return {
            subtotal: subtotal.toFixed(2),
            shipping: shipping.toFixed(2),
            tax: tax.toFixed(2),
            total: total.toFixed(2)
        };
    }

    /**
     * Save cart to localStorage
     */
    function saveCart() {
        localStorage.setItem("cart", JSON.stringify(cart));
    }

    /**
     * Render the cart UI
     */
    function renderCart() {
        // Update cart count
        const totalItems = cart.reduce((count, item) => count + (item.quantity || 1), 0);
        if (cartCountElement) {
            cartCountElement.textContent = totalItems;
        }

        // Show/hide empty cart message
        if (emptyCartMessage && cartItemsContainer) {
            if (cart.length === 0) {
                emptyCartMessage.classList.remove('d-none');
                cartItemsContainer.classList.add('d-none');
                if (checkoutForm) checkoutForm.classList.add('d-none');
            } else {
                emptyCartMessage.classList.add('d-none');
                cartItemsContainer.classList.remove('d-none');
                if (checkoutForm) checkoutForm.classList.remove('d-none');
            }
        }

        // Clear and repopulate cart items
        if (cartItemsElement) {
            cartItemsElement.innerHTML = '';

            cart.forEach((item, index) => {
                const quantity = item.quantity || 1;
                const price = parseFloat(item.price);
                const itemTotal = price * quantity;

                const li = document.createElement('li');
                li.className = 'cart-item';

                // Item details
                const itemContent = document.createElement('div');
                itemContent.className = 'flex-grow-1';
                itemContent.innerHTML = `
            <div class="fw-bold">${item.name}</div>
            <div class="text-muted small">
              ${item.brand || ''} 
              ${item.color ? '- ' + item.color : ''}
              ${item.size ? '/ ' + item.size : ''}
            </div>
            <div class="product-price">$${itemTotal.toFixed(2)}</div>
          `;

                // Quantity controls
                const controls = document.createElement('div');
                controls.className = 'cart-controls';

                // Minus button
                const minusBtn = document.createElement('button');
                minusBtn.className = 'btn btn-sm btn-outline-secondary';
                minusBtn.innerHTML = '-';
                minusBtn.addEventListener('click', () => updateQuantity(item, index, quantity - 1));

                // Quantity input
                const quantityInput = document.createElement('input');
                quantityInput.type = 'number';
                quantityInput.className = 'quantity-control';
                quantityInput.min = 1;
                quantityInput.value = quantity;
                quantityInput.addEventListener('change', e => updateQuantity(item, index, e.target.value));

                // Plus button
                const plusBtn = document.createElement('button');
                plusBtn.className = 'btn btn-sm btn-outline-secondary';
                plusBtn.innerHTML = '+';
                plusBtn.addEventListener('click', () => updateQuantity(item, index, quantity + 1));

                // Remove button
                const removeBtn = document.createElement('button');
                removeBtn.className = 'btn btn-sm btn-outline-danger ms-2';
                removeBtn.innerHTML = '×';
                removeBtn.addEventListener('click', () => removeItem(item, index));

                // Add all controls
                controls.appendChild(minusBtn);
                controls.appendChild(quantityInput);
                controls.appendChild(plusBtn);
                controls.appendChild(removeBtn);

                // Combine content and controls
                li.appendChild(itemContent);
                li.appendChild(controls);

                // Add to cart items list
                cartItemsElement.appendChild(li);
            });
        }

        // Update totals
        const totals = calculateTotals();
        if (cartSubtotalElement) cartSubtotalElement.textContent = totals.subtotal;
        if (cartShippingElement) cartShippingElement.textContent = totals.shipping;
        if (cartTaxElement) cartTaxElement.textContent = totals.tax;
        if (cartTotalElement) cartTotalElement.textContent = totals.total;
    }

    /**
     * Get session information
     */
    function getSessionInfo() {
        return fetch('/api/session')
            .then(response => response.json())
            .catch(error => {
                console.error('Error fetching session:', error);
                return null;
            });
    }

    /**
     * End current session
     */
    function endSession() {
        // Track end session for Datadog RUM
        window.DD_RUM && window.DD_RUM.addAction('end_session');
        window.DD_RUM && window.DD_RUM.stopSession();

        return fetch('/api/session/end', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('You have been logged out', 'info');
                    // Reload page after short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showToast('Failed to end session', 'danger');
                }
                return data;
            })
            .catch(error => {
                console.error('Error ending session:', error);
                showToast('Network error', 'danger');
                return { status: 'failed', message: 'Network error' };
            });
    }

    /**
     * Submit order to server
     */
    function submitOrder() {
        if (cart.length === 0) {
            showToast('Your cart is empty', 'warning');
            return;
        }

        // Get form data
        const name = document.getElementById('checkout-name')?.value || '';
        const email = document.getElementById('checkout-email')?.value || '';
        const totals = calculateTotals();

        // Track checkout for Datadog RUM
        window.DD_RUM && window.DD_RUM.addAction('checkout', {
            name: name,
            email: email,
            totals: totals
        });
        // Check if user wants to end session after checkout
        const endSessionAfterCheckout = document.getElementById('end-session-checkbox')?.checked || false;

        // Prepare order data
        const orderData = {
            name: name,
            email: email,
            items: cart.map(item => ({
                product_id: item.id,
                quantity: item.quantity || 1
            })),
            total: parseFloat(totals.total),
            end_session: endSessionAfterCheckout
        };

        // Submit order
        fetch('/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success modal or toast
                    if (orderSuccessModal) {
                        orderSuccessModal.show();
                    } else {
                        showToast('Order successful!', 'success');
                    }

                    // Clear cart
                    cart = [];
                    saveCart();
                    renderCart();
                } else {
                    // Show error modal or toast
                    if (orderErrorModal) {
                        const errorElement = document.getElementById('order-error-reason');
                        if (errorElement) errorElement.textContent = data.reason || 'Unknown error';
                        orderErrorModal.show();
                    } else {
                        showToast(`Order failed: ${data.reason || 'Unknown error'}`, 'danger');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);

                // Show error modal or toast
                if (orderErrorModal) {
                    const errorElement = document.getElementById('order-error-reason');
                    if (errorElement) errorElement.textContent = 'Network error. Please try again.';
                    orderErrorModal.show();
                } else {
                    showToast('Network error. Please try again.', 'danger');
                }
            });
    }

    /**
     * Show a toast notification
     */
    function showToast(message, type = 'primary') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="toast-header bg-${type} text-white">
            <strong class="me-auto">GadgetGrove</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
          <div class="toast-body">
            ${message}
          </div>
        </div>
      `;

        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);

        // Initialize and show toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 3000
        });
        toast.show();

        // Remove toast from DOM after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function () {
            toastElement.remove();
        });
    }

    // Add logout button event listener
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            endSession();
        });
    }

    // Initialize cart on page load
    renderCart();

    /**
     * Refresh current session
     */
    function refreshSession() {
        return fetch('/api/session/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('Session refreshed', 'success');
                    updateSessionUI(data);
                } else {
                    showToast('Failed to refresh session', 'danger');
                }
                return data;
            })
            .catch(error => {
                console.error('Error refreshing session:', error);
                showToast('Network error', 'danger');
                return { status: 'failed', message: 'Network error' };
            });
    }

    /**
     * Update all session UI elements
     */
    function updateSessionUI(sessionInfo) {
        if (!sessionInfo) return;

        // Format expiry time
        const expiryDate = new Date(sessionInfo.expires_at);
        const now = new Date();
        const minutesRemaining = Math.round((expiryDate - now) / 60000);
        const expiryText = minutesRemaining > 0
            ? `Session expires in ${minutesRemaining} minutes`
            : 'Session expired';

        // Update main UI session expiry
        const sessionExpiry = document.getElementById('session-expiry');
        if (sessionExpiry) {
            sessionExpiry.textContent = expiryText;
        }

        // Update modal session expiry
        const modalSessionExpiry = document.getElementById('modal-session-expiry');
        if (modalSessionExpiry) {
            modalSessionExpiry.textContent = expiryText;

            // Update badge color based on time remaining
            modalSessionExpiry.className = 'badge';
            if (minutesRemaining < 5) {
                modalSessionExpiry.classList.add('bg-danger', 'text-white');
            } else if (minutesRemaining < 10) {
                modalSessionExpiry.classList.add('bg-warning', 'text-dark');
            } else {
                modalSessionExpiry.classList.add('bg-info', 'text-white');
            }
        }
    }

    // Session modal management
    let sessionModalInstance = null;
    const sessionModal = document.getElementById('sessionModal');
    if (sessionModal) {
        // Set up event listeners for the session modal
        sessionModal.addEventListener('hidden.bs.modal', function () {
            // Remove backdrop manually if it's stuck
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
            // Fix body classes
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        });

        // Initialize modal
        sessionModalInstance = new bootstrap.Modal(sessionModal, {
            backdrop: true,
            keyboard: true,
            focus: true
        });

        // Refresh button
        const refreshBtn = document.getElementById('modal-refresh-session');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function () {
                refreshSession();
            });
        }

        // End session button
        const endSessionBtn = document.getElementById('modal-end-session');
        if (endSessionBtn) {
            endSessionBtn.addEventListener('click', function () {
                // Hide modal
                if (sessionModalInstance) sessionModalInstance.hide();

                // Make sure backdrop is removed
                setTimeout(() => {
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }

                    // End session
                    endSession();
                }, 300);
            });
        }
    }

    // Add session info to page
    getSessionInfo().then(sessionInfo => {
        if (sessionInfo) {
            updateSessionUI(sessionInfo);

            // Track user session for Datadog RUM
            window.DD_RUM && window.DD_RUM.setUser({
                id: sessionInfo.session_id,
                name: sessionInfo.user.name,
                email: sessionInfo.user.email
            });

            // Set up a timer to refresh session UI every minute
            setInterval(() => {
                getSessionInfo().then(updateSessionUI);
            }, 60000);
        }
    });
});