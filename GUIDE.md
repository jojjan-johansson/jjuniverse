# JJ Universe — Teknisk dokumentation

## Vad är JJ Universe?

JJ Universe är en webb-app för tarotläsning med AI-tolkning. Användare loggar in, väljer en läggningstyp, drar kort och får en personlig tolkning via Claude AI (Anthropic). Appen är byggd med Python/Flask och körs på en VPS-server.

---

## Teknisk stack

| Del | Teknologi |
|-----|-----------|
| Backend | Python 3, Flask |
| AI | Anthropic Claude Haiku (`claude-haiku-4-5`) |
| Databas | SQLite (användarkonton) |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Kortbilder | PNG/JPG, egengenererade via ChatGPT |
| Produktion | Gunicorn + Nginx |

---

## Projektstruktur

```
jjuniverse/
├── app.py                  # Flask-app, alla routes och AI-logik
├── cards.py                # Lista med alla 78 tarotkort
├── database.py             # SQLite-setup och anslutning
├── generate_cards.py       # Genererar reservbilder med Pillow (om egna saknas)
├── requirements.txt        # Python-beroenden
├── .env                    # API-nycklar (läggs INTE i Git)
├── users.db                # SQLite-databas (läggs INTE i Git)
├── templates/
│   ├── index.html          # Huvud-app (kräver inloggning)
│   └── login.html          # Inloggning och registrering
└── static/
    ├── css/
    │   ├── style.css       # Huvudstil — mörkt mystiskt tema
    │   └── login.css       # Stil för inloggningssidan
    ├── js/
    │   └── app.js          # All frontend-logik
    └── images/
        ├── cards/          # Kortbilder (78 st, används av appen)
        └── mycards/        # Originalkort uppladdade av ägaren
```

---

## Miljövariabler (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...    # API-nyckel från console.anthropic.com
SECRET_KEY=...                   # Slumpmässig sträng för Flask-sessioner
```

> **.env får aldrig läggas i Git.** Den är listad i `.gitignore`.

---

## Kortfilnamn

Kortbilderna ligger i `static/images/cards/` och följer detta mönster:

| Suit | Filer |
|------|-------|
| Stora Arkanan | `major_00.jpg` – `major_21.jpg` |
| Bägare (Cups) | `cups_01.jpg` – `cups_14.jpg` |
| Stavar (Wands) | `wands_01.jpg` – `wands_14.jpg` |
| Svärd (Swords) | `swords_01.jpg` – `swords_14.jpg` |
| Pentagram (Pentacles) | `pentacles_01.jpg` – `pentacles_14.jpg` |

Lägg nya bilder i `static/images/mycards/` och kör kopieringsskriptet nedan.

### Kopiera egna kort
```bash
python3 - <<'EOF'
import shutil, os
src = "static/images/mycards"
dst = "static/images/cards"
mapping = {
    # Lägg till dina filer här: "mittfilnamn.png": "cards_XX.jpg"
}
for s, d in mapping.items():
    sp = os.path.join(src, s)
    dp = os.path.join(dst, d)
    if os.path.exists(sp):
        shutil.copy2(sp, dp)
        print(f"✓ {s} → {d}")
EOF
```

---

## Läggningstyper

### 1. En Fråga (`single`)
- Användaren skriver en fråga
- Drar 3 kort: **Grunden / Kärnan / Vägen framåt**
- AI ger ett sammanhängande svar + råd

### 2. Tre Frågor (`triple`)
- Användaren skriver 3 frågor
- Drar 9 kort (3 per fråga)
- AI tolkar varje fråga + ett gemensamt råd

### 3. Årsstjärnan (`year`)
- Ingen fråga
- Drar 13 kort: 12 månader (jan–dec) i cirkel + 1 mittort (årets tema)
- AI ger månadsvis energi + råd för hela året

---

## Följdfrågor

Efter varje läsning kan användaren:
1. Ställa upp till **10 textfrågor** i en chatt under tolkningen
2. Klicka **"Följdfråga med kort"** för att dra 1 extra kort kopplat till en ny fråga

Konversationshistoriken skickas med varje anrop så AI:n har full kontext.

---

## AI — Anthropic Claude

- **Modell:** `claude-haiku-4-5` (billigaste, snabbaste)
- **Streaming:** Server-Sent Events (SSE) — texten skrivs ut i realtid
- **Systemprompt:** Definierar tonen — varm, jordnära, aldrig skrämmande
- **Regler:** Döden = förändring, aldrig mörker/katastrof, alltid råd i slutet

**Byta modell** (i `app.py`):
```python
model="claude-haiku-4-5"      # Billig, snabb (~0.05-0.10 kr/läsning)
model="claude-sonnet-4-6"     # Bättre kvalitet, dyrare
model="claude-opus-4-6"       # Bäst kvalitet, dyrast
```

---

## Inloggning

- Konton lagras i `users.db` (SQLite)
- Lösenord hashas med `werkzeug.security`
- Sessioner hanteras med Flask `session` + `SECRET_KEY`
- Alla API-routes skyddas med `@login_required`

---

## Köra lokalt

```bash
# 1. Klona repo
git clone https://github.com/DITT_NAMN/jjuniverse.git
cd jjuniverse

# 2. Skapa virtuell miljö
python3 -m venv venv
source venv/bin/activate

# 3. Installera beroenden
pip install -r requirements.txt

# 4. Skapa .env
echo "ANTHROPIC_API_KEY=sk-ant-DIN_NYCKEL" > .env
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env

# 5. Starta
python3 app.py
# Öppna http://localhost:5000
```

---

## Produktion (Loopia VPS)

### 1. Installera
```bash
sudo apt update && sudo apt install python3-pip python3-venv nginx
git clone https://github.com/DITT_NAMN/jjuniverse.git /var/www/jjuniverse
cd /var/www/jjuniverse
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Skapa .env på servern
```bash
nano /var/www/jjuniverse/.env
```

### 3. Gunicorn systemd-tjänst
```bash
sudo nano /etc/systemd/system/jjuniverse.service
```
```ini
[Unit]
Description=JJ Universe Tarot App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/jjuniverse
Environment="PATH=/var/www/jjuniverse/venv/bin"
ExecStart=/var/www/jjuniverse/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable jjuniverse && sudo systemctl start jjuniverse
```

### 4. Nginx
```nginx
server {
    listen 80;
    server_name din-domän.se;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
    }

    location /static {
        alias /var/www/jjuniverse/static;
    }
}
```

### 5. HTTPS (gratis)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d din-domän.se
```

---

## .gitignore

```
.env
users.db
venv/
__pycache__/
*.pyc
static/images/cards/
static/images/mycards/
```

---

## Felsökning

| Problem | Lösning |
|---------|---------|
| "credit balance too low" | Fyll på kredit på console.anthropic.com |
| Kort visas inte | Kontrollera att bildfilen finns i `static/images/cards/` |
| Streaming fungerar inte | Kontrollera `X-Accel-Buffering: no` i Nginx |
| Port 5000 upptagen | `fuser -k 5000/tcp` |
| Login-loop | Kontrollera att `SECRET_KEY` är satt i `.env` |

---

## Nästa steg / idéer

- [ ] Spara läsningshistorik per användare i databasen
- [ ] Betalningsfunktion (Stripe) för premium-åtkomst
- [ ] Fler läggningstyper (keltiskt kors, etc.)
- [ ] Admin-panel för att se antal användare och läsningar
- [ ] E-post-verifiering vid registrering
