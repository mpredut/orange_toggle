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
print({PASSWORD})

BASE_URL  = "https://www.orange.ro"
LOGIN_URL = f"{BASE_URL}/accounts/login-user"
FOLDER    = os.path.dirname(os.path.abspath(__file__))


async def ss(page, name):
    path = os.path.join(FOLDER, f"debug_{name}.png")
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

    # 3. Așteaptă INPUT-UL REAL (cheia problemei)
    log.info("  Aștept câmpul de email (#EmailLogin)...")
    await ss(page, "test_1")
    email_input = page.locator("#EmailLogin")
    await email_input.wait_for(state="visible", timeout=15000)
    await ss(page, "test_2")
    # 4. Completează email
    await email_input.click(force=True)
    await email_input.fill(EMAIL)
    log.info("  ✓ Email completat")
    await ss(page, "test_3")

    # 5. Completează parola (direct, există deja în DOM)
    log.info("  Aștept câmpul de parolă (#PasswordLogin)...")
    password_input = page.locator("#PasswordLogin")
    await password_input.wait_for(state="visible", timeout=10000)

    await password_input.click()
    await password_input.fill(PASSWORD)
    log.info("  ✓ Parola completată")

    await ss(page, "02_filled")

    # 6. Click login (ID direct = 100% sigur)
    log.info("  Click login...")
    login_btn = page.locator("#loginBtn")
    await login_btn.wait_for(state="visible", timeout=10000)

    await login_btn.click()
    await ss(page, "login_clicked")
    #print(await page.content())

    # 7. Așteaptă navigare după login
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass

    await page.wait_for_timeout(5000)

    log.info(f"  URL după login: {page.url}")
    await ss(page, "03_after_login")

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
    log.info(f"▶ Select phone number: {phone_number}")
    
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

    await ss(page, "06_phone_selector_panel")

    # Strategia 1: caută direct după textul numărului de telefon
    try:
        phone_loc = page.locator(f"text={phone_number}").first
        await phone_loc.wait_for(state="visible", timeout=5000)
        await phone_loc.click()
        log.info(f"  ✓ Click direct pe număr: {phone_number}")
        await page.wait_for_timeout(1500)
        await ss(page, "06b_after_phone_select")
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
        await ss(page, "06b_after_phone_select")
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
            await ss(page, "06b_after_phone_select")
            return True
    except Exception as e:
        log.warning(f"  ⚠️ JS evaluate failed: {e}")

    await ss(page, "ERROR_phone_not_found")
    log.error(f"  ✗ Nu am putut selecta numărul {phone_number}")
    return False

async def go_to_servicii(page):
    log.info("▶ STEP 2: Navighez la Servicii")
    # Din screenshot 1: sidebar stânga are "Servicii" cu iconița de chat
    clicked = False
    for sel in [
        # Sidebar stânga — link sau buton cu textul exact
        "a:has-text('Servicii'):visible",
        "li:has-text('Servicii') a:visible",
        "[href*='servicii']:visible",
        # fallback text match
        "text='Servicii'",
    ]:
        try:
            #loc = page.locator(sel).first
            #loc = page.locator("a").filter(has_text="Servicii").filter(has_not_text="SIM").first
            loc = page.locator("//a[normalize-space()='Servicii']").first
            await loc.wait_for(state="visible", timeout=5000)
            await loc.click()
            await page.wait_for_load_state("networkidle", timeout=5000)
            log.info(f"  ✓ Click Servicii ({sel}) → {page.url}")
            clicked = True
            break
        except PlaywrightTimeout:
            continue

    if not clicked:
        url = f"{BASE_URL}/myaccount/reshape/services/summary"
        log.info(f"  Direct URL: {url}")
        await page.goto(url, wait_until="networkidle", timeout=5000)

    await page.wait_for_timeout(1500)
    await ss(page, "04_servicii")


async def click_detalii_voce(page):
    """
    Din screenshot 1: primul card (Voce) are textul
    'Poti activa sau dezactiva mesageria vocala, internetul mobil...'
    și un link 'Detalii' la bază.
    """
    log.info("▶ STEP 3: Click 'Detalii' pe cardul Voce")
    clicked = False

    # Strategie 1: cardul care conține "Internetul mobil" → Detalii din el
    for card_text in ["Internetul mobil", "mesageria vocala", "dezactiva"]:
        try:
            card = page.locator(f"div:has-text('{card_text}')").first
            await card.wait_for(state="visible", timeout=5000)
            detalii = card.locator("text=Detalii").first
            await detalii.wait_for(state="visible", timeout=4000)
            await detalii.click()
            log.info(f"  ✓ Click Detalii (card cu '{card_text}')")
            clicked = True
            break
        except PlaywrightTimeout:
            continue

    # Strategie 2: primul "Detalii" din pagină
    if not clicked:
        try:
            detalii = page.locator("a:has-text('Detalii'), button:has-text('Detalii')").first
            await detalii.wait_for(state="visible", timeout=6000)
            await detalii.click()
            log.info("  ✓ Click primul Detalii din pagină")
            clicked = True
        except PlaywrightTimeout:
            pass

    # Strategie 3: URL direct
    if not clicked:
        for url in [
            f"{BASE_URL}/myaccount/reshape/services/voice",
            f"{BASE_URL}/my-orange/services/voice",
        ]:
            log.info(f"  URL direct: {url}")
            await page.goto(url, wait_until="networkidle", timeout=20000)
            if "voice" in page.url:
                clicked = True
                break

    await page.wait_for_load_state("networkidle", timeout=15000)
    await page.wait_for_timeout(1500)
    await ss(page, "05_voce_page")
    log.info(f"  URL: {page.url}")


async def select_voce_tab(page):
    """Din screenshot 2: tab-uri sus → Sumar | Voce | Telefoane | Orange care
    <div _ngcontent-fkr-c199="" class="d-flex align-items-center justify-content-between"><oro-switch _ngcontent-fkr-c199="" _nghost-fkr-c198=""><button _ngcontent-fkr-c198="" id="oro-service-modify" triggers="click" placement="bottom" containerclass="popover-dark" class="switch switch-btn on"><span _ngcontent-fkr-c198="" class="tooltip-icon"></span></button><!----></oro-switch></div>
    """
    log.info("▶ STEP 4: Selectez tab 'Voce'")
    try:
        tab = page.locator("a:has-text('Voce'), button:has-text('Voce'), [role='tab']:has-text('Voce')").first
        await tab.wait_for(state="visible", timeout=6000)
        await tab.click()
        await page.wait_for_load_state("networkidle", timeout=10000)
        log.info("  ✓ Tab Voce selectat")
    except PlaywrightTimeout:
        log.info("  Tab Voce nu găsit — probabil deja pe pagina corectă.")
    await page.wait_for_timeout(1500)
    await ss(page, "06_voce_tab")


async def confirm_modal(page, action: str):
    """Confirmă modalul după click pe toggle."""
    log.info("  ▶ Aștept modal confirmare...")
    
    # Textul exact din buton depinde de acțiune
    if action == "enable":
        btn_texts = ["Activeaza", "Activează", "Confirmă", "Confirm", "Da", "OK"]
    else:
        btn_texts = ["Dezactiveaza", "Dezactivează", "Confirmă", "Confirm", "Da", "OK"]
    
    # Așteptăm să apară modalul (Angular modal)
    modal_sel = "modal-container, [role='dialog'], .modal, .modal-dialog"
    try:
        await page.wait_for_selector(modal_sel, state="visible", timeout=8000)
        log.info("  ✓ Modal detectat")
    except PlaywrightTimeout:
        log.warning("  ⚠️ Modal nu a apărut în 8s")
    
    # Încercăm fiecare text de buton
    for text in btn_texts:
        try:
            # Folosim get_by_role pentru precizie maximă
            btn = page.get_by_role("button", name=text, exact=True)
            await btn.wait_for(state="visible", timeout=3000)
            await btn.click()
            log.info(f"  ✓ Click pe buton: '{text}'")
            return True
        except PlaywrightTimeout:
            pass
        
        # Fallback cu locator text
        try:
            btn = page.locator(f"button:text-is('{text}')").first
            await btn.wait_for(state="visible", timeout=2000)
            await btn.click()
            log.info(f"  ✓ Click text-is: '{text}'")
            return True
        except PlaywrightTimeout:
            pass
    
    # Ultimul fallback: orice buton portocaliu/primary din modal
    try:
        btn = page.locator(
            "modal-container button.btn-primary, "
            "modal-container button[class*='orange'], "
            "modal-container button[style*='background'], "
            "[role='dialog'] button.btn-primary"
        ).first
        await btn.wait_for(state="visible", timeout=4000)
        text = await btn.text_content()
        log.info(f"  ✓ Click buton primary din modal: '{text}'")
        await btn.click()
        return True
    except PlaywrightTimeout:
        pass
    
    await ss(page, "ERROR_modal_not_confirmed")
    log.error("  ✗ Nu am putut confirma modalul!")
    return False

async def toggle_internet(page, action: str):
    """
    Din screenshot 2: cardul 'Internet mobil' (primul din grid) are:
      - text verde 'activ' + toggle portocaliu (checked)
    Trebuie să găsim toggle-ul din primul card.
    """
    log.info(f"▶ STEP 5: Toggle Internet Mobil → {action.upper()}")
    await page.wait_for_timeout(1500)

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
        await ss(page, "ERROR_no_toggle")
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
    await ss(page, "07_after_click_on_toggle")

    await ss(page, "DEBUG_before_confirm")

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
    
    # Dialog de confirmare: trebuie click pe butonul principal din modal (Activează/Dezactivează)
    confirm_selectors = [
        "[role='dialog'] button:has-text('Dezactivează')",
        "[role='dialog'] button:has-text('Dezactiveaza')",
        "[role='dialog'] button:has-text('Activează')",
        "[role='dialog'] button:has-text('Activeaza')",
        "[role='dialog'] button:has-text('Confirmă')",
        "[role='dialog'] button:has-text('Confirm')",
        "[role='dialog'] button:has-text('Da')",
        "[role='dialog'] button:has-text('OK')",
        "[role='dialog'] button:has-text('Continuă')",
        "[role='dialog'] button:has-text('Aplică')",
        "button:has-text('Dezactivează')",
        "button:has-text('Dezactiveaza')",
        "button:has-text('Activează')",
        "button:has-text('Activeaza')",
        "button:has-text('Confirmă')",
        "button:has-text('Confirm')",
    ]

    clicked_confirm = False
    for sel in confirm_selectors:
        try:
            btn = page.locator(sel).first
            await btn.wait_for(state="visible", timeout=4000)
            await btn.click()
            log.info(f"  ✓ Confirmat: '{sel}'")
            clicked_confirm = True
            break
        except PlaywrightTimeout:
            continue

    # Fallback explicit pe text din modal (dacă selecția de sus nu a prins)
    if not clicked_confirm:
        try:
            # 1) Evităm dialogul de confidențialitate, țintim modalul de confirmare real
            dialog = page.locator("modal-container").first
            await dialog.wait_for(state="visible", timeout=5000)

            confirm_btn = dialog.locator(
                "button:has-text('Dezactivează'), button:has-text('Dezactiveaza'), "
                "button:has-text('Activează'), button:has-text('Activeaza'), "
                "button:has-text('Confirmă'), button:has-text('Confirm'), "
                "a:has-text('Dezactivează'), a:has-text('Dezactiveaza'), "
                "a:has-text('Activează'), a:has-text('Activeaza'), "
                "a:has-text('Confirmă'), a:has-text('Confirm')"
            ).first

            await confirm_btn.wait_for(state="visible", timeout=4000)
            await confirm_btn.click()
            log.info("  ✓ Confirmat fallback modal-container")
            clicked_confirm = True
        except PlaywrightTimeout:
            # Dacă nu este modal-container, încercăm popover sau orice element cu text
            try:
                popover = page.locator("div.popover, div.tooltip, [class*='popover'], [class*='tooltip']").first
                await popover.wait_for(state="visible", timeout=5000)
                confirm_btn = popover.locator(
                    "button:has-text('Dezactivează'), button:has-text('Dezactiveaza'), "
                    "button:has-text('Activează'), button:has-text('Activeaza'), "
                    "button:has-text('Confirmă'), button:has-text('Confirm'), "
                    "a:has-text('Dezactivează'), a:has-text('Dezactiveaza'), "
                    "a:has-text('Activează'), a:has-text('Activeaza'), "
                    "a:has-text('Confirmă'), a:has-text('Confirm')"
                ).first
                await confirm_btn.wait_for(state="visible", timeout=4000)
                await confirm_btn.click()
                log.info("  ✓ Confirmat popover")
                clicked_confirm = True
            except PlaywrightTimeout:
                # Ultim fallback: căutăm direct butonul în pagină după click
                try:
                    await page.wait_for_timeout(3000)  # așteptăm să apară
                    confirm_btn = page.locator(
                        "button:has-text('Dezactivează'), button:has-text('Dezactiveaza'), "
                        "button:has-text('Activează'), button:has-text('Activeaza'), "
                        "button:has-text('Confirmă'), button:has-text('Confirm'), "
                        "a:has-text('Dezactivează'), a:has-text('Dezactiveaza'), "
                        "a:has-text('Activează'), a:has-text('Activeaza'), "
                        "a:has-text('Confirmă'), a:has-text('Confirm')"
                    ).first
                    await confirm_btn.wait_for(state="visible", timeout=4000)
                    await confirm_btn.click()
                    log.info("  ✓ Confirmat direct în pagină")
                    clicked_confirm = True
                except PlaywrightTimeout:
                    log.warning("  ⚠️ Nu am găsit modal confirmare explicit")

    if not clicked_confirm:
        log.warning("  ⚠️ Nu am reușit sa confirm modificarea via modal. Verifică selectorii")

    # Așteptăm procesarea să se termine
    await page.wait_for_timeout(2000)
    try:
        # Wait for "in procesare" to appear, then disappear
        processing_locator = page.locator("span:has-text('in procesare'), div:has-text('in procesare'), *:has-text('in procesare')").first
        await processing_locator.wait_for(state="visible", timeout=10000)  # wait up to 10s for it to appear
        log.info("  🔄 Procesare detectată")
        await processing_locator.wait_for(state="hidden", timeout=60000)  # wait up to 60s for it to disappear
        log.info("  ✅ Procesare terminată")
    except PlaywrightTimeout:
        log.warning("  ⚠️ Nu am detectat sau așteptat sfârșitul procesării")

    await ss(page, f"08_{action}_done")

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
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="ro-RO",
        )
        page = await context.new_page()
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
