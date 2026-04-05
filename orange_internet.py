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

BASE_URL  = "https://www.orange.ro"
LOGIN_URL = f"{BASE_URL}/accounts/login-user"
FOLDER    = os.path.dirname(os.path.abspath(__file__))


async def ss(page, name):
    path = os.path.join(FOLDER, "debug", f"debug_{name}.png")
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


async def login(page):
    log.info("▶ STEP 1: Login")

    # 1. Deschide pagina
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=40000)

    # 2. Accept cookies (dacă apar)
    await accept_cookies(page)

    await page.wait_for_timeout(3000)

    # 3. Așteaptă INPUT-UL REAL (cheia problemei)
    log.info("  Aștept câmpul de email (#EmailLogin)...")
    await ss(page, "test_1")
    email_input = page.locator("#EmailLogin")
    await email_input.wait_for(state="visible", timeout=30000)
    await ss(page, "test_2")
    # 4. Completează email
    await email_input.click(force=True)
    await email_input.fill(EMAIL)
    log.info("  ✓ Email completat")
    await ss(page, "test_3")

    # 5. Completează parola (direct, există deja în DOM)
    log.info("  Aștept câmpul de parolă (#PasswordLogin)...")
    password_input = page.locator("#PasswordLogin")
    await password_input.wait_for(state="visible", timeout=20000)

    await password_input.click()
    await password_input.fill(PASSWORD)
    log.info("  ✓ Parola completată")

    await ss(page, "01_pass_filled")

    # 6. Click login (ID direct = 100% sigur)
    log.info("  Click login...")
    login_btn = page.locator("#loginBtn")
    await login_btn.wait_for(state="visible", timeout=20000)

    await login_btn.click()
    await ss(page, "01_login_clicked")
    #print(await page.content())

    # 7. Așteaptă navigare după login
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=20000)
    except:
        pass

    await page.wait_for_timeout(10000)

    log.info(f"  URL după login: {page.url}")
    await ss(page, "01_after_login")

    # 8. Verificare simplă (foarte important)
    if "login" in page.url.lower():
        log.warning("⚠️ Încă pe pagina de login — posibil captcha sau eroare login")
    else:
        log.info("✅ Login probabil reușit")

async def select_phone_number(page, phone_number: str):
    """
    Selectează numărul de telefon din panelul 'Tip abonament'.
    phone_number: ex. "0774004205"
    """
    log.info(f"▶ STEP 2: Select phone number: {phone_number}")
    
    # Așteptăm panelul să apară (Angular îl randează async)
    # Din screenshot, panelul are "Tip abonament" ca titlu
    try:
        await page.wait_for_selector(
            "text=abonament",
            state="visible",
            timeout=10000
        )
        log.info("  ✓ Panel 'abonament' detectat")
    except PlaywrightTimeout:
        log.warning("  ⚠️ Panel 'abonament' nu a apărut")

    await ss(page, "02_phone_selector_panel")

    # Strategia 1: caută direct după textul numărului de telefon
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

    # Strategia 2: caută în cardurile de abonament
    # Din screenshot, fiecare card are structura: avatar + nume + număr
    try:
        # Găsim elementul părinte al numărului și dăm click pe card
        card = page.locator(f"div:has(p:text('{phone_number}'), span:text('{phone_number}'))").first
        await card.wait_for(state="visible", timeout=5000)
        await card.click()
        log.info(f"  ✓ Click pe card cu numărul: {phone_number}")
        await page.wait_for_timeout(1500)
        await ss(page, "02_after_phone_select")
        return True
    except PlaywrightTimeout:
        log.warning("  ⚠️ Nu am găsit cardul cu numărul")

    # Strategia 3: evaluate JS - caută elementul care conține textul și dă click
    try:
        clicked = await page.evaluate(f"""
            () => {{
                const all = document.querySelectorAll('*');
                for (const el of all) {{
                    if (el.children.length === 0 && el.textContent.trim() === '{phone_number}') {{
                        // click pe părintele clickabil
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

    await ss(page, "02_ERROR_phone_not_found")
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
            clicked = True
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
    """Confirmă modalul după click pe toggle (variantă stabilă Angular)."""
    log.info("  ▶ Aștept modal confirmare...")

    # Texte posibile în funcție de acțiune
    if action == "enable":
        texts = ["Activeaza", "Activează", "Confirmă", "Confirm", "Da", "OK"]
    else:
        texts = ["Dezactiveaza", "Dezactivează", "Confirmă", "Confirm", "Da", "OK"]

    # 1️⃣ Așteaptă modalul REAL
    try:
        dialog = page.locator("modal-container").first
        await dialog.wait_for(state="visible", timeout=8000)
        log.info("  ✓ Modal detectat (modal-container)")
    except PlaywrightTimeout:
        await ss(page, "05_ERROR_no_modal")
        log.error("  ✗ Modalul nu a apărut!")
        return False

    # 2️⃣ Caută buton DOAR în modal (IMPORTANT)
    for text in texts:
        try:
            btn = dialog.locator(f"button:has-text('{text}'), a:has-text('{text}')").first
            await btn.wait_for(state="visible", timeout=2000)
            await btn.click()
            log.info(f"  ✓ Confirmat cu: '{text}'")
            return True
        except PlaywrightTimeout:
            continue

    # 3️⃣ Fallback inteligent (buton submit din modal)
    try:
        btn = dialog.locator("button[type='submit']").first
        await btn.wait_for(state="visible", timeout=3000)

        txt = await btn.text_content()
        log.info(f"  ✓ Fallback submit: '{txt}'")

        await btn.click()
        return True
    except PlaywrightTimeout:
        pass

    # 4️⃣ Ultim fallback (primul buton vizibil din modal)
    try:
        btn = dialog.locator("button").filter(has_text="").first
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
    """
    Din screenshot 2: cardul 'Internet mobil' (primul din grid) are:
      - text verde 'activ' + toggle portocaliu (checked)
    Trebuie să găsim toggle-ul din primul card.
    """
    log.info(f"▶ STEP 5: Toggle Internet Mobil → {action.upper()}")
    await page.wait_for_timeout(2500)

    # Găsim cardul "Internet mobil" — din screenshot titlul e h2/h3/div bold
    card = None
    for sel in [
        "div:has(> *:has-text('Internet mobil'))",
        "*:has-text('Este serviciul care iti permite sa navighezi')",
        # fallback: primul card din grid-ul de servicii voce
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

    # Găsim toggle-ul
    toggle = None
    search_in = card if card else page

    for sel in [
        "button.switch",
        "#oro-service-modify",
    ]:
        try:
            loc = search_in.locator(sel).first
            await loc.wait_for(state="attached", timeout=4000)
            toggle = loc
            log.info(f"  ✓ Toggle găsit ({sel})")
            break
        except PlaywrightTimeout:
            continue

    if toggle is None:
        await ss(page, "05_ERROR_no_toggle")
        raise RuntimeError("Nu am găsit toggle-ul Internet mobil! Vezi debug_ERROR_no_toggle.png")

    # Stare curentă
    try:
        cls = await toggle.get_attribute("class") or ""
        is_active = "on" in cls
    except Exception:
        aria = await toggle.get_attribute("aria-checked") or "false"
        is_active = aria == "true"

    log.info(f"  Stare curentă: {'ACTIV ✅' if is_active else 'INACTIV ⭕'}")

    want_active = (action == "enable")
    if is_active == want_active:
        log.info(f"  ℹ️  Deja în starea corectă. Nu e nevoie de acțiune.")
        return

    # Acționăm toggle-ul
    log.info(f"  Click toggle...")
    await toggle.scroll_into_view_if_needed()
    await toggle.click()
    await page.wait_for_timeout(2000)
    await ss(page, "05_after_click_on_toggle")

    await ss(page, "05_DEBUG_before_confirm_toggle")

    # Dump toate butoanele vizibile
    #buttons = page.locator("button:visible")
    #count = await buttons.count()
    #for i in range(count):
    #    txt = await buttons.nth(i).text_content()
    #     log.info(f"  Button[{i}]: '{txt}'")
        
    confirm_modal_result = await confirm_modal(page, action)
    if not confirm_modal_result:
        log.warning("  ⚠️ Nu am reușit să confirm modificarea. Verifică debug_ERROR_modal_not_confirmed.png")
        #return
    
    # Așteptăm procesarea să se termine
    await page.wait_for_timeout(2000)
    try:
        # Wait for "in procesare" to appear, then disappear
        processing_locator = page.locator("span:has-text('in procesare'), div:has-text('in procesare'), *:has-text('in procesare')").first
        await processing_locator.wait_for(state="visible", timeout=10000)  # wait up to 10s for it to appear
        log.info("  🔄 Procesare detectată")
    except PlaywrightTimeout:
        log.warning("  ⚠️ Nu am detectat sau așteptat sfârșitul procesării")

    await ss(page, f"05_{action}_done")

    # Verificare finală
    try:
        cls = await toggle.get_attribute("class") or ""
        final_active = "on" in cls
        ok = (final_active == want_active)
        log.info(f"  {'✅ SUCCES' if ok else '⚠️ ATENȚIE'}: stare finală {'ACTIV' if final_active else 'INACTIV'}")
    except Exception:
        log.info("  (Nu am putut verifica starea finală)")


async def run(action: str):
    log.info(f"\n{'='*55}")
    log.info(f"  Orange Internet Toggle — {action.upper()}")
    log.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*55}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="ro-RO",
        )
        page = await context.new_page()
        await stealth_async(page)
        try:
            await login(page)
            await select_phone_number(page, PHONE)  # Exemplu de număr de telefon
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
    if len(sys.argv) != 2 or sys.argv[1] not in ("enable", "disable"):
        print("Utilizare: python orange_internet.py [enable|disable]")
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))
