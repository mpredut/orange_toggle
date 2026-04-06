#!/usr/bin/env python3
"""
My Orange - Toggle Internet Mobil
Dezactivează la 23:00, reactivează la 05:00

Flow real (din screenshots):
  1. Login → https://www.orange.ro/accounts/login-user
  2. Servicii (meniu stânga)
  3. Click "Detalii" pe cardul Voce (cel cu mesagerie/internet mobil)
  4. Tab "Voce" (dacă nu e deja activ)
  5. Cardul "Internet mobil" → toggle orange
"""

import asyncio
import sys
import logging
import os
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv
from playwright_stealth import stealth_async
import json


load_dotenv()

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orange.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

EMAIL    = os.getenv("ORANGE_EMAIL",    "predut1978@gmail.com")
PASSWORD = os.getenv("ORANGE_PASSWORD", "XXX")
PHONE    = os.getenv("ORANGE_PHONE",    "0774004205")

BASE_URL     = "https://www.orange.ro"
LOGIN_URL    = f"{BASE_URL}/accounts/login-user"
FOLDER       = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(FOLDER, "orange_cookies.json")


async def ss(page, name):
    path = os.path.join(FOLDER, "debug", f"debug_{name}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    await page.screenshot(path=path, full_page=True)
    log.info(f"  📸 {path}")


async def accept_cookies(page):
    for sel in [
        "#onetrust-accept-btn-handler",
        "button:has-text('Acceptă toate')",
        "button:has-text('Accept all')",
        "button:has-text('Sunt de acord')",
    ]:
        try:
            btn = page.locator(sel).first
            await btn.wait_for(state="visible", timeout=4000)
            await btn.click()
            log.info("  🍪 Cookies acceptate.")
            await page.wait_for_timeout(800)
            return
        except PlaywrightTimeout:
            continue


async def save_cookies(context):
    cookies = await context.cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)
    log.info(f"  ✓ Cookies salvate ({len(cookies)} entries) → {COOKIES_FILE}")


async def load_cookies(context):
    if not os.path.exists(COOKIES_FILE):
        log.info("  Niciun fișier cookies găsit.")
        return False
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    await context.add_cookies(cookies)
    log.info(f"  ✓ Cookies încărcate ({len(cookies)} entries)")
    return True


async def login(page):
    log.info("▶ STEP 1: Login")

    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=40000)
    await accept_cookies(page)
    await page.wait_for_timeout(3000)

    log.info("  Aștept câmpul de email (#EmailLogin)...")
    await ss(page, "test_1")
    email_input = page.locator("#EmailLogin")
    await email_input.wait_for(state="visible", timeout=10000)
    await ss(page, "test_2")

    await email_input.click(force=True)
    await email_input.fill("")
    await email_input.type(EMAIL, delay=80)
    await email_input.dispatch_event("input")
    await email_input.dispatch_event("change")
    await email_input.press("Tab")
    await page.wait_for_timeout(500)
    log.info("  ✓ Email completat")
    await ss(page, "test_3")

    log.info("  Aștept câmpul de parolă (#PasswordLogin)...")
    password_input = page.locator("#PasswordLogin")
    await password_input.wait_for(state="visible", timeout=20000)

    await password_input.click()
    await password_input.fill("")
    await password_input.type(PASSWORD, delay=80)
    await password_input.dispatch_event("input")
    await password_input.dispatch_event("change")
    await password_input.press("Tab")
    await page.wait_for_timeout(800)
    log.info("  ✓ Parola completată")
    await ss(page, "01_pass_filled")

    values = await page.evaluate("""
        () => {
            const e = document.querySelector('#EmailLogin');
            const p = document.querySelector('#PasswordLogin');
            const b = document.querySelector('#loginBtn');
            return {
                email: e?.value || null,
                pass: p?.value ? 'OK' : null,
                btnText: b?.textContent?.trim() || null,
                btnDisabled: b?.disabled ?? null,
                btnHasDisabledClass: b?.classList.contains('disabled') ?? null
            };
        }
    """)
    log.info(
        f"  DOM after fill: "
        f"email={'OK' if values['email'] else 'MISSING'}, "
        f"pass={values['pass']}, "
        f"btn='{values['btnText']}' "
        f"disabled={values['btnDisabled']} "
        f"disabled-class={values['btnHasDisabledClass']}"
    )

    log.info("  Click login...")
    login_btn = page.locator("#loginBtn")
    await login_btn.wait_for(state="visible", timeout=20000)

    btn_enabled = await login_btn.is_enabled()
    log.info(f"  Buton enabled înainte de click: {btn_enabled}")

    if not btn_enabled:
        log.warning("  ⚠️ Buton dezactivat — încerc force click oricum...")

    await ss(page, "01_before_click")
    await login_btn.click(force=True)
    log.info("  ✓ Click trimis (force=True)")
    await ss(page, "01_login_clicked")
    await page.wait_for_timeout(5000)

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=20000)
    except Exception:
        pass

    log.info("  Aștept 10 secunde pentru redirecționare...")
    await page.wait_for_timeout(10000)

    if "login" in page.url.lower():
        try:
            await page.wait_for_selector(
                "#abonament, #servicii, [href*='contul-meu']",
                timeout=30000
            )
        except Exception:
            log.warning("  ⚠️ Nu s-a detectat un element specific paginii după login")
            await page.wait_for_timeout(30000)

    log.info(f"  URL după login: {page.url}")
    await ss(page, "01_after_login")

    if "login" in page.url.lower():
        log.warning("⚠️ Încă pe pagina de login — posibil captcha sau credențiale greșite")
    else:
        log.info("✅ Login reușit")


async def select_phone_number(page, phone_number: str):
    log.info(f"▶ STEP 2: Select phone number: {phone_number}")

    try:
        await page.wait_for_selector("text=abonament", state="visible", timeout=10000)
        log.info("  ✓ Panel 'abonament' detectat")
    except PlaywrightTimeout:
        log.warning("  ⚠️ Panel 'abonament' nu a apărut")

    await ss(page, "02_phone_selector_panel")

    try:
        phone_loc = page.locator(f"text={phone_number}").first
        await phone_loc.wait_for(state="visible", timeout=5000)
        await phone_loc.click()
        log.info(f"  ✓ Click direct pe număr: {phone_number}")
        await page.wait_for_timeout(1500)
        await ss(page, "02_after_phone_select")
        return True
    except PlaywrightTimeout:
        log.warning(f"  ⚠️ Nu am găsit text='{phone_number}' direct")

    try:
        card = page.locator(f"div:has(p:text('{phone_number}'), span:text('{phone_number}'))").first
        await card.wait_for(state="visible", timeout=5000)
        await card.click()
        log.info(f"  ✓ Click pe card cu numărul: {phone_number}")
        await page.wait_for_timeout(1500)
        await ss(page, "02_after_phone_select")
        return True
    except PlaywrightTimeout:
        log.warning("  ⚠️ Nu am găsit cardul cu numărul")

    try:
        clicked = await page.evaluate(f"""
            () => {{
                const all = document.querySelectorAll('*');
                for (const el of all) {{
                    if (el.children.length === 0 && el.textContent.trim() === '{phone_number}') {{
                        let parent = el.parentElement;
                        for (let i = 0; i < 5; i++) {{
                            if (parent) {{
                                parent.click();
                                parent = parent.parentElement;
                            }}
                        }}
                        return true;
                    }}
                }}
                return false;
            }}
        """)
        if clicked:
            log.info(f"  ✓ Click via JS evaluate pe: {phone_number}")
            await page.wait_for_timeout(1500)
            await ss(page, "02_after_phone_select")
            return True
    except Exception as e:
        log.warning(f"  ⚠️ JS evaluate failed: {e}")

    await ss(page, "02_ERROR_selection_phone_not_found")
    log.error(f"  ✗ Nu am putut selecta numărul {phone_number}")
    return False


async def go_to_servicii(page):
    log.info("▶ STEP 3: Navighez la Servicii")
    url = f"{BASE_URL}/myaccount/reshape/services/summary"
    log.info(f"  Direct URL: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_timeout(15000)
    await ss(page, "03_servicii")


async def click_detalii_voce(page):
    log.info("▶ STEP 4: Click 'Detalii' pe cardul Voce")

    for url in [
        f"{BASE_URL}/myaccount/reshape/services/voice",
        f"{BASE_URL}/my-orange/services/voice",
    ]:
        log.info(f"  URL direct: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        if "voice" in page.url:
            break

    await page.wait_for_load_state("domcontentloaded", timeout=15000)
    await page.wait_for_timeout(2500)
    await ss(page, "04_voce_page")
    log.info(f"  URL: {page.url}")


async def select_voce_tab(page):
    log.info("▶ STEP 5: Selectez tab 'Voce'")
    try:
        tab = page.locator("a:has-text('Voce'), button:has-text('Voce'), [role='tab']:has-text('Voce')").first
        await tab.wait_for(state="visible", timeout=6000)
        await tab.click()
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        log.info("  ✓ Tab Voce selectat")
    except PlaywrightTimeout:
        log.info("  Tab Voce nu găsit — probabil deja pe pagina corectă.")
    await page.wait_for_timeout(200)
    await ss(page, "05_voce_tab")


async def confirm_modal(page, action: str):
    log.info("  ▶ Aștept modal confirmare...")

    if action == "enable":
        texts = ["Activeaza", "Activează", "Confirmă", "Confirm", "Da", "OK"]
    else:
        texts = ["Dezactiveaza", "Dezactivează", "Confirmă", "Confirm", "Da", "OK"]

    try:
        dialog = page.locator("modal-container").first
        await dialog.wait_for(state="visible", timeout=8000)
        log.info("  ✓ Modal detectat (modal-container)")
    except PlaywrightTimeout:
        await ss(page, "05_ERROR_no_modal")
        log.error("  ✗ Modalul nu a apărut!")
        return False

    for text in texts:
        try:
            btn = dialog.locator(f"button:has-text('{text}'), a:has-text('{text}')").first
            await btn.wait_for(state="visible", timeout=2000)
            await btn.click()
            log.info(f"  ✓ Confirmat cu: '{text}'")
            return True
        except PlaywrightTimeout:
            continue

    try:
        btn = dialog.locator("button[type='submit']").first
        await btn.wait_for(state="visible", timeout=3000)
        txt = await btn.text_content()
        log.info(f"  ✓ Fallback submit: '{txt}'")
        await btn.click()
        return True
    except PlaywrightTimeout:
        pass

    try:
        btn = dialog.locator("button").first
        await btn.wait_for(state="visible", timeout=3000)
        txt = await btn.text_content()
        log.warning(f"  ⚠️ Fallback generic button: '{txt}'")
        await btn.click()
        return True
    except PlaywrightTimeout:
        pass

    await ss(page, "05_ERROR_modal_not_confirmed")
    log.error("  ✗ Nu am putut confirma modalul!")
    return False


async def toggle_internet(page, action: str):
    log.info(f"▶ STEP 6: Toggle Internet Mobil → {action.upper()}")
    await page.wait_for_timeout(2500)

    card = None
    for sel in [
        "div:has(> *:has-text('Internet mobil'))",
        "*:has-text('Este serviciul care iti permite sa navighezi')",
        ".card:first-child",
        "article:first-child",
    ]:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=5000)
            card = loc
            log.info(f"  ✓ Card găsit ({sel})")
            break
        except PlaywrightTimeout:
            continue

    toggle = None
    search_in = card if card else page

    for sel in ["button.switch", "#oro-service-modify"]:
        try:
            loc = search_in.locator(sel).first
            await loc.wait_for(state="attached", timeout=4000)
            toggle = loc
            log.info(f"  ✓ Toggle găsit ({sel})")
            break
        except PlaywrightTimeout:
            continue

    if toggle is None:
        await ss(page, "06_ERROR_no_toggle")
        raise RuntimeError("Nu am găsit toggle-ul Internet mobil!")

    try:
        cls = await toggle.get_attribute("class") or ""
        is_active = "on" in cls
    except Exception:
        aria = await toggle.get_attribute("aria-checked") or "false"
        is_active = aria == "true"

    log.info(f"  Stare curentă: {'ACTIV ✅' if is_active else 'INACTIV ⭕'}")

    want_active = (action == "enable")
    if is_active == want_active:
        log.info("  ℹ️  Deja în starea corectă. Nu e nevoie de acțiune.")
        return

    log.info("  Click toggle...")
    await toggle.scroll_into_view_if_needed()
    await toggle.click()
    await page.wait_for_timeout(2000)
    await ss(page, "06_after_toggle_click")

    confirm_ok = await confirm_modal(page, action)
    if not confirm_ok:
        log.warning("  ⚠️ Nu am reușit să confirm modificarea.")

    await page.wait_for_timeout(2000)
    try:
        processing = page.locator(
            "span:has-text('in procesare'), div:has-text('in procesare')"
        ).first
        await processing.wait_for(state="visible", timeout=10000)
        log.info("  🔄 Procesare detectată")
    except PlaywrightTimeout:
        log.warning("  ⚠️ Nu am detectat procesarea")

    await ss(page, f"06_{action}_done")

    try:
        cls = await toggle.get_attribute("class") or ""
        final_active = "on" in cls
        ok = (final_active == want_active)
        log.info(f"  {'✅ SUCCES' if ok else '⚠️ ATENȚIE'}: stare finală {'ACTIV' if final_active else 'INACTIV'}")
    except Exception:
        log.info("  (Nu am putut verifica starea finală)")


async def init_session():
    """
    Deschide browserul vizibil pe Windows, așteaptă login manual,
    apoi salvează cookies pentru rulările automate.
    """
    log.info("▶ INIT SESSION — Loginează-te manual în browser")
    log.info("  După login apasă Enter în terminal pentru a salva sesiunea.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=0,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ro-RO",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await page.goto(LOGIN_URL)

        log.info("  ⌛ Browserul e deschis. Loginează-te manual, apoi apasă Enter aici...")
        await asyncio.get_event_loop().run_in_executor(None, input)

        if "login" in page.url.lower():
            log.error("  ✗ Încă pe pagina de login — sesiunea nu a fost salvată")
        else:
            await save_cookies(context)
            log.info(f"  ✅ Sesiune salvată în {COOKIES_FILE}")
            log.info("  Poți rula acum: python orange_internet.py enable/disable")

        await browser.close()


async def run(action: str):
    log.info(f"\n{'='*55}")
    log.info(f"  Orange Internet Toggle — {action.upper()}")
    log.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*55}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,   # headless=True după ce ai sesiunea salvată
            slow_mo=100,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="ro-RO",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await stealth_async(page)

        try:
            session_ok = await load_cookies(context)

            if session_ok:
                log.info("  Verific validitatea sesiunii...")
                await page.goto(
                    f"{BASE_URL}/myaccount/reshape/services/summary",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                await page.wait_for_timeout(3000)
                if "login" in page.url.lower():
                    log.warning("  Cookies expirate — re-login necesar")
                    session_ok = False

            if not session_ok:
                await login(page)
                if "login" not in page.url.lower():
                    await save_cookies(context)
                else:
                    raise RuntimeError("Login eșuat — cookies nu au fost salvate")

            await select_phone_number(page, PHONE)
            await go_to_servicii(page)
            await click_detalii_voce(page)
            await select_voce_tab(page)
            await toggle_internet(page, action)

            log.info(f"\n✅ FINALIZAT: {action.upper()}")

        except Exception as e:
            log.error(f"\n❌ EROARE: {e}")
            await ss(page, "FATAL_ERROR")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("enable", "disable", "init"):
        print("Utilizare: python orange_internet.py [enable|disable|init]")
        sys.exit(1)

    if sys.argv[1] == "init":
        asyncio.run(init_session())
    else:
        asyncio.run(run(sys.argv[1]))