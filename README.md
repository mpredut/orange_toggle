# Orange Internet Toggle 🟠

Dezactivează automat internetul mobil la **23:00** și îl reactivează la **05:00**.

---

## Instalare (o singură dată)

```bash
# 1. Copiază folderul pe server, intră în el
cd orange_toggle

# 2. Pune parola în .env
nano .env
# Schimbă XXX cu parola ta reală de My Orange

# 3. Rulează setup
bash setup.sh

# 4. Instalează cron jobs
bash install_cron.sh
```

---

## Test manual

```bash
source venv/bin/activate

# Dezactivează acum
python orange_internet.py disable

# Activează acum
python orange_internet.py enable
```

---

## Monitorizare

```bash
# Urmărește log-ul în timp real
tail -f orange.log

# Verifică cron jobs active
crontab -l
```

---

## Debug

Dacă ceva nu merge, scriptul salvează **screenshot-uri** în același folder:
- `debug_01_after_login.png` — după login
- `debug_03_servicii_page.png` — pagina servicii
- `debug_ERROR_*.png` — dacă nu găsește butonul

Trimite aceste screenshot-uri dacă vrei să depanăm.

---

## Fișiere

| Fișier | Rol |
|--------|-----|
| `orange_internet.py` | Scriptul principal |
| `.env` | Credențiale (nu da share la acest fișier!) |
| `setup.sh` | Instalare inițială |
| `install_cron.sh` | Adaugă cron jobs |
| `remove_cron.sh` | Șterge cron jobs |
| `orange.log` | Log-ul execuțiilor |

---

## Note

- Scriptul rulează în **mod headless** (fără interfață grafică)
- Dacă Orange schimbă site-ul, selectoarele CSS pot necesita actualizare
- Parola este stocată în `.env` — asigură-te că fișierul nu e accesibil altor useri (`chmod 600 .env`)
