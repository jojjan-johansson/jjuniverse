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
RESEND_API_KEY=re_...            # API-nyckel från resend.com (för att maila läsningar)
ADMIN_USERNAME=jjadmin           # Admin-användarnamn för /star
ADMIN_PASSWORD=...               # Admin-lösenord för /star
```

> **OBS:** Dela aldrig dessa värden i chatt eller i git. .env är listad i .gitignore.

> **.env får aldrig läggas i Git.** Den är listad i `.gitignore`.

### ⚠️ Skriva .env på servern — gör SÅ HÄR

API-nyckeln är lång och **får inte kopieras direkt i terminalen** — radbrytningar förstör filen.
Dela upp nyckeln i kortare delar och sätt ihop med bash-variabler:

```bash
# Dela upp API-nyckeln i bitar (justera delarna efter din nyckel)
P1='sk-ant-api03-FÖRSTA_DELEN'
P2='ANDRA_DELEN'
P3='TREDJE_DELEN'
SK='din-secret-key-här'
{ echo "ANTHROPIC_API_KEY=${P1}${P2}${P3}"; echo "SECRET_KEY=${SK}"; } > ~/apps/jjuniverse/.env

# Verifiera att filen ser rätt ut ($ = radbrytning, ska vara EN rad per variabel)
cat -A ~/apps/jjuniverse/.env
```

Om filen är trasig syns det med `python-dotenv could not parse statement` i loggarna:
```bash
sudo journalctl -u jjuniverse --no-pager | tail -20
```

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

## Produktion (Loopia VPS — jjuniverse.se)

**Server:** Ubuntu 24.04, Loopia VPS
**Domän:** jjuniverse.se → 213.188.153.93
**Reverse proxy:** Caddy (sköter HTTPS automatiskt)
**App-port:** 5001

### Sökvägar på servern
```
/home/johanna/apps/jjuniverse/   # App-katalog
/etc/caddy/Caddyfile             # Caddy-konfiguration
/etc/systemd/system/jjuniverse.service
```

### Driftsätta en uppdatering
```bash
cd ~/apps/jjuniverse
git pull
sudo systemctl restart jjuniverse
sudo systemctl status jjuniverse
```

### Systemd-tjänst (`/etc/systemd/system/jjuniverse.service`)
```ini
[Unit]
Description=JJ Universe Tarot
After=network.target

[Service]
User=johanna
WorkingDirectory=/home/johanna/apps/jjuniverse
Environment=PATH=/home/johanna/apps/jjuniverse/venv/bin
ExecStart=/home/johanna/apps/jjuniverse/venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Caddy (`/etc/caddy/Caddyfile`)
```
jjuniverse.se {
    reverse_proxy 127.0.0.1:5001
}
```
Caddy sköter HTTPS/SSL automatiskt. Starta om Caddy efter ändringar:
```bash
sudo systemctl reload caddy
```

### Skapa .env på servern (se avsnitt ovan om .env)

---

## .gitignore

```
.env
users.db
venv/
__pycache__/
*.pyc
*.log
nohup.out
```

> Kortbilderna (`static/images/cards/` och `static/images/mycards/`) **är med i Git** för säker backup.

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

## Support

**Support-mail:** jjuniverse.support@gmail.com
Används för: kundsupport, transaktionella mail (läsningar skickas hit från), Resend/SendGrid avsändaradress.

---

## Betalning — Stripe (planerat)

### Paket & priser (SEK inkl. moms)

| Paket | Pris | Innehåll |
|-------|------|----------|
| En fråga | 60 kr | 1 läggning (3 kort) + 3 följdfrågor |
| Tre frågor | 150 kr | 3 läggningar + 3 följdfrågor per läggning |
| Årsstjärnan | 300 kr | 1 stor läggning (13 kort) + 3 följdfrågor |

### Teknisk plan
- **Betalningslösning:** Stripe Checkout (Stripe hanterar kortuppgifter, vi ser dem aldrig)
- **Gästköp:** Tillåtet — man behöver inte konto för att betala
- **Leverans:** Läsningen mailas automatiskt till angiven e-post när den är klar
- **Valuta:** SEK
- **Marknad:** Sverige (till att börja med)
- **Webhook-verifiering:** Stripe-signatur verifieras på backend innan köp aktiveras
- **Idempotency:** `stripe_session_id` sparas i DB så dubbla webhooks inte ger dubbla läsningar

### Databastabeller som behövs
```sql
purchases (
  id, email, stripe_session_id, package, status, created_at
)
```

### En läggning = ett köp
En köpt session = en läggning + upp till 3 följdfrågor. Sedan är sessionen klar. Vill man ha mer köper man ett nytt paket.

---

## Juridik & villkor (att bygga)

### Dokument som ska finnas
- **Användarvillkor** — länk i footern
- **Integritetspolicy** — länk i footern
- **Betalningsvillkor** — visas direkt innan Stripe-checkout
- **Cookie-banner** — enkel, bara "Okej"-knapp (endast nödvändiga cookies)

### Obligatoriskt innehåll (checklista)

**Ansvarsbegränsning (skyddsväst)**
- Tjänsten ges "i befintligt skick"
- Inget garanterat resultat
- Ej ansvarig för indirekta skador (dåliga beslut baserade på läsning)

**Ångerrätt (EU-lag — KRITISKT)**
- Kunden måste avsäga sig ångerrätten
- Checkbox vid köp: *"Jag samtycker till att leveransen påbörjas direkt och att ångerrätten därmed upphör"*
- Utan detta kan kunder lagligt kräva pengarna tillbaka

**Tjänstens natur (extra viktigt för tarot)**
- AI-genererad tolkning
- Ej vetenskapligt bevisad
- Endast för personlig reflektion och underhållning
- Ingen medicinsk, psykologisk, juridisk eller finansiell rådgivning
- Du måste vara 18+ (checkbox vid köp)

**Företagsinfo (måste finnas)**
- Namn (företag eller privatperson)
- E-post: jjuniverse.support@gmail.com
- Land: Sverige

**Betalning**
- Betalning hanteras av Stripe
- Vi lagrar inga kortuppgifter

**Övrigt**
- Rätt att stänga av/blockera användare och konton
- Svensk lag gäller, tvister hanteras i Sverige
- Tjänsten garanterar inte alltid tillgänglighet
- Villkoren kan ändras när som helst

---

## Admin-panel (planerat)

### Åtkomst
- URL: `jjuniverse.se/star`
- Användarnamn: satt i `.env` som `ADMIN_USERNAME` (värde: jjadmin)
- Lösenord: satt i `.env` som `ADMIN_PASSWORD`
- Separat inloggning, helt separerat från vanliga användarkonton
- Syns inte i källkoden eller frontend

### Statistik att visa
- Antal besök per dag/vecka (sidvisningar)
- Antal registrerade användare
- Antal läsningar per typ (single/triple/year)
- Antal köp + intäkter (när Stripe är aktivt)

### Säkerhetsövervakning
- Misslyckade inloggningsförsök (många från samma IP = misstänkt)
- Nya konton (ovanlig spike = möjlig bot-registrering)
- 404-fel (scanning av routes)

### Struktur
Admin-panelen har egen meny med flikar:
1. **Översikt** — nyckeltal i kortformat
2. **Statistik** — grafer/tabeller med besök och läsningar
3. **Säkerhet** — inloggningsförsök, misstänkt aktivitet
4. **Användare** — lista, blockera konton (när betalning är på plats)

---

## Byggt & klart

- [x] Admin-panel på `/star` med översikt, statistik och säkerhetsflik
- [x] Besöksloggning, läsningsloggning, säkerhetshändelser (SQLite)
- [x] Cookie-banner (localStorage)
- [x] Användarvillkor (`/terms`), Integritetspolicy (`/privacy`), Betalningsvillkor (`/payment-terms`)
- [x] "Skicka till min mail"-knapp med Resend-integration
- [x] Kortförstoring via modal (klick på kort)
- [x] Footer med villkorslänkar på alla sidor

## Nästa steg

- [ ] Stripe-integration (betalning)
- [ ] Fler läggningstyper (keltiskt kors, etc.)
- [ ] E-post-verifiering vid registrering
