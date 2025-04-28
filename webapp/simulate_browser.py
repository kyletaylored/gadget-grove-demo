import asyncio
import random
import os
import logging
from ddtrace import tracer, patch_all
from playwright.async_api import async_playwright

# Datadog APM patch
patch_all()

# Logging setup
FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
          '- %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://webapp:8000")


@tracer.wrap(name="simulate.user.session")
async def simulate_user_session():
    session_id = random.randint(1000, 9999)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        log.info(f"[Session {session_id}] Starting browser session")

        # Go to home page
        await page.goto(WEBAPP_URL)
        await page.wait_for_timeout(random.randint(500, 1500))
        log.info(f"[Session {session_id}] Visited home page")

        # Get categories
        categories = await page.query_selector_all('a[data-route^="/category/"]:not([data-route*="/product/"])')
        if not categories:
            log.error(f"[Session {session_id}] No categories found! Exiting")
            await browser.close()
            return

        # Visit 2–5 categories randomly
        for _ in range(random.randint(2, 5)):
            category = random.choice(categories)
            category_href = await category.get_attribute('data-route')
            if not category_href:
                continue

            category_slug = category_href.replace("/category/", "")
            log.info(
                f"[Session {session_id}] Navigating to category {category_slug}")

            # Click category
            await page.click(f'a[data-route="{category_href}"]')
            await page.wait_for_selector(f'#category-{category_slug}-view', state='visible', timeout=5000)
            await page.wait_for_selector(f'#category-{category_slug}-view .product-link', state='visible', timeout=5000)
            await page.wait_for_timeout(random.randint(500, 1500))

            # Get products inside this category
            product_links = await page.query_selector_all(f'#category-{category_slug}-view .product-link')
            if not product_links:
                log.warning(
                    f"[Session {session_id}] No products found in category {category_slug}")
                continue

            # Click 1–3 random products
            for _ in range(random.randint(1, 3)):
                product = random.choice(product_links)
                product_href = await product.get_attribute('data-route')
                if not product_href:
                    continue

                product_id = product_href.split("/")[-1]
                log.info(
                    f"[Session {session_id}] Clicking product {product_id}")

                await page.click(f'a[data-route="{product_href}"]')
                await page.wait_for_selector(f'#product-{product_id}-view', state='visible', timeout=5000)
                await page.wait_for_timeout(random.randint(1000, 2000))

                # Maybe add to cart
                if random.random() > 0.4:
                    add_to_cart = await page.query_selector('.add-to-cart')
                    if add_to_cart:
                        await add_to_cart.wait_for_element_state('visible', timeout=5000)
                        await add_to_cart.click()
                        log.info(
                            f"[Session {session_id}] Added product {product_id} to cart")
                        await page.wait_for_timeout(random.randint(500, 1500))
                    else:
                        log.warning(
                            f"[Session {session_id}] Add to cart button not found for product {product_id}")

                # Go back to category page
                await page.go_back()
                await page.wait_for_timeout(random.randint(500, 1500))

            # Maybe return to home
            if random.random() > 0.7:
                await page.click('a[data-route="/"]')
                await page.wait_for_timeout(random.randint(1000, 2000))
                log.info(f"[Session {session_id}] Returned to home page")

        # Open cart
        cart_btn = await page.query_selector('button[data-bs-target="#cartCanvas"]')
        if cart_btn:
            await cart_btn.click()
            await page.wait_for_timeout(random.randint(1000, 2000))
            log.info(f"[Session {session_id}] Opened cart")

            # Randomly checkout
            if random.random() > 0.5:
                submit_btn = await page.query_selector('#checkout-form button[type="submit"]')
                if submit_btn:
                    await submit_btn.wait_for_element_state('visible', timeout=5000)
                    await submit_btn.click()
                    log.info(f"[Session {session_id}] Submitted checkout")
                    await page.wait_for_timeout(random.randint(2000, 4000))
                else:
                    log.warning(
                        f"[Session {session_id}] Checkout button not found")
        else:
            log.warning(f"[Session {session_id}] Cart button not found")

        await browser.close()
        log.info(f"[Session {session_id}] Simulation complete")

if __name__ == "__main__":
    try:
        asyncio.run(simulate_user_session())
    except Exception as e:
        log.error(f"Simulation failed with error: {e}")
