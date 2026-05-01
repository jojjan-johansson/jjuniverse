# JJ Universe — Teknisk dokumentation

## Vad är JJ Universe?

JJ Universe är en betaltjänst för AI-genererad tarotläsning. Besökare köper en session via Stripe, väljer en läggningstyp, drar kort och får en personlig tolkning via Claude AI. Inga konton krävs — man betalar direkt som gäst.

Det finns också en gratis veckovisa sida (`/veckan`) med kärlek-, ekonomi- och energikort, månfasinfo och kinesiskt horoskop/numerologi — för att locka in besökare.

---

## Teknisk stack

| Del | Teknologi |
|-----|-----------|
| Backend | Python 3, Flask |
| AI | Anthropic Claude Haiku (`claude-haiku-4-5`) |
| Databas | SQLite (`users.db`) |
| Betalning | Stripe Checkout |
| E-post | Resend (access-mail) |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Produktion | Gunicorn + Caddy (HTTPS auto) |

---

## Projektstruktur

```
jjuniverse/
├── app.py                    # Flask-app — alla routes och logik
├── cards.py                  # Lista med alla 78 tarotkort
├── database.py               # SQLite-setup, tabeller och hjälpfunktioner
├── requirements.txt          # Python-beroenden
├── .env                      # API-nycklar (läggs INTE i Git)
├── users.db                  # SQLite-databas (läggs INTE i Git)
├── GUIDE.md                  # Denna fil
├── templates/
│   ├── index.html            # Huvud-app (kräver köpt session eller admin)
│   ├── login.html            # Landningssida med köpknapp + gratis dagskort
│   ├── veckan.html           # Gratis veckosida (kärlek/ekonomi/energi/måne)
│   ├── consent.html          # Villkorssida — visas alltid för nya besökare
│   ├── kop.html              # Paketval med priser
│   ├── kop_bekrafta.html     # Bekräftelse + checkboxar innan betalning
│   ├── payment_success.html  # Visas efter lyckad betalning
│   ├── payment_cancel.html   # Visas om betalning avbryts
│   ├── access_invalid.html   # Ogiltig access-token
│   ├── access_used.html      # Access-token redan använd
│   ├── terms.html            # Användarvillkor
│   ├── privacy.html          # Integritetspolicy
│   ├── payment_terms.html    # Betalningsvillkor
│   ├── admin_login.html      # Admin-inloggning (/star)
│   └── admin_panel.html      # Admin-panel (översikt/statistik/säkerhet/samtycken)
└── static/
    ├── css/
    │   ├── style.css         # Huvudstil — mörkt mystiskt tema
    │   ├── login.css         # Stil för inloggningssidan
    │   └── veckan.css        # Stil för veckosidan
    ├── js/
    │   ├── app.js            # All frontend-logik
    │   └── ambient.js        # Stjärnfält + ambient-ljud
    ├── favicon.png
    └── images/
        ├── cards/            # Kortbilder (78 st)
        └── mycards/          # Originalkort uppladdade av ägaren
```

---

## Miljövariabler (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...        # Från console.anthropic.com
SECRET_KEY=...                       # Slumpsträng för Flask-sessioner
RESEND_API_KEY=re_...                # Från resend.com (skicka mail)
ADMIN_USERNAME=jjadmin               # Admin-inlogg för /star
ADMIN_PASSWORD=...                   # Admin-lösenord för /star
ADMIN_EMAIL=jjuniverse.support@gmail.com  # Dit säkerhetsvarningar skickas
STRIPE_PUBLIC_KEY=pk_test_...        # Stripe publika nyckel (test/live)
STRIPE_SECRET_KEY=sk_test_...        # Stripe hemliga nyckel (test/live)
STRIPE_WEBHOOK_SECRET=               # Stripe webhook-signatur (valfritt)
```

> **OBS:** Dela aldrig dessa värden i chatt eller i git. `.env` är listad i `.gitignore`.

### Lägga till saknade värden på servern

```bash
nano ~/apps/jjuniverse/.env
```
Lägg till raden i slutet → `Ctrl+X` → `Y` → `Enter` → starta om:
```bash
sudo systemctl restart jjuniverse
```

---

## Betalningspaket & priser

| Paket | Nyckel | Pris | Innehåll |
|-------|--------|------|----------|
| 4 Frågor | `single` | 30 kr | 1 läggning (3 kort) + 4 följdfrågor |
| 12 Frågor | `triple` | 60 kr | 3 läggningar + 4 följdfrågor/läggning |
| Årsstjärnan | `year` | 100 kr | 13 kort (helår) + 4 följdfrågor |

Priserna anges i **öre** i koden (`3000` = 30 kr). Definerade i `PACKAGES` i `app.py`.

---

## Användarflöde (kund)

```
1. Besök jjuniverse.se
       ↓
2. /welcome — Villkorssida (4 checkboxar, sparas i DB)
       ↓
3. /login — Landningssida
   - Gratis dagskort visas
   - Länk till /veckan (gratis veckosida)
   - Knapp "Köp en läsning" → /kop
       ↓
4. /kop — Välj paket (single / triple / year)
       ↓
5. /kop/bekrafta — Bekräfta med 4 checkboxar (ångerrätt etc.)
       ↓
6. Stripe Checkout — Betalning med kort
       ↓
7. /payment/success — Bekräftelsesida
   - Session sätts: purchase_token + purchase_package
   - Access-mail skickas automatiskt till kundens e-post
   - Kunden klickar "Påbörja min läsning"
       ↓
8. / (index) — Appen, hoppar direkt till köpt läggningstyp
       ↓
9. Läsning genomförs (reading_done=1 sätts i DB)
       ↓
10. Kunden kan:
    - Ställa upp till 4 följdfrågor (text)
    - Göra "Följdfråga med kort" (extra kort)
    - Klicka "Ny läsning" → /kop (ny betalning krävs)
```

---

## Sessionssystem

Appen använder Flask-sessioner (krypterade cookies).

| Sessionsvariabel | Vad den gör |
|-----------------|-------------|
| `consent_given` | Satt när villkor godkänts. Krävs för att komma förbi /welcome |
| `purchase_token` | Unik token kopplad till ett köp i DB. Ger tillgång till appen |
| `purchase_package` | Vilken typ köptes (`single`/`triple`/`year`). Styr auto-val i appen |
| `admin_logged_in` | Satt vid admin-inlogg. Ger fri tillgång till hela appen |

### Accessskydd

- Alla behöver `purchase_token` **eller** `admin_logged_in` för att komma in i appen
- `login_required`-dekoratorn skyddar alla API-routes
- Om `purchase_token` saknas → redirect till `/login`

---

## Veckans Spådomar (`/veckan`)

Gratis sida utan inloggning. Uppdateras varje vecka (cachas per veckonummer + IP).

### Innehåll
- **Kärlek, Ekonomi, Energi, Visdom** — Tarotkort dras per tema. Varje användare får sitt eget kort (cachas per IP + vecka). AI genererar tolkning.
- **Månfas** — Beräknas matematiskt i realtid (ingen extern API). Visar rätt månform grafiskt, fasnamn, energibeskrivning och urtidens visdom.
- **Kinesiskt horoskop** — Användaren matar in födelseår och får djurkaraktär + veckovisa råd.
- **Numerologi** — Användaren matar in födelsedag och får livsnummer + tolkning.
- **Q&A** — Betalda frågor mot veckokontext (kräver Stripe-session).

### Databastabeller för veckan
- `weekly_cards` — Cachat kort + AI-text per IP/tema/vecka
- `weekly_extra` — Cachat kinesiskt/numerologi-innehåll per vecka
- `weekly_qa_sessions` — Betalda Q&A-sessioner

---

## Bakåtknapp-skydd (anti-fusk)

En kund som navigerar bakåt efter en läsning ska inte kunna göra en ny läsning gratis.

**Lösning — tre lager:**

**1. JS history-manipulation** körs när köpsessionen startar:
```javascript
history.replaceState(null, '', '/');
history.pushState(null, '', '/');
```

**2. Confirm-dialog** visas vid `popstate` (bakåtknapp).

**3. `/session/check`** (Flask-route) är den definitiva serverskyddet:
- `reading_done=0` → redirect till `/` (kan fortsätta)
- `reading_done=1` → rensar session → redirect till `/kop` (ny betalning krävs)

---

## Routes (app.py)

### Publika
| Route | Metod | Beskrivning |
|-------|-------|-------------|
| `/welcome` | GET | Villkorssida |
| `/api/consent` | POST | Sparar godkännande i DB |
| `/login` | GET | Landningssida med dagskort och köpknapp |
| `/kop` | GET | Paketval |
| `/kop/bekrafta` | GET | Bekräftelse innan betalning |
| `/api/create-checkout-session` | POST | Skapar Stripe-session, returnerar URL |
| `/payment/success` | GET | Bekräftelse efter betalning |
| `/payment/cancel` | GET | Avbruten betalning |
| `/webhook/stripe` | POST | Stripe-webhook (uppdaterar DB) |
| `/access/<token>` | GET | Engångslänk för att återfå tillgång |
| `/session/end` | GET | Avslutar session |
| `/session/check` | GET | Kontrollerar reading_done vid bakåtnavigering |
| `/terms` | GET | Användarvillkor |
| `/privacy` | GET | Integritetspolicy |
| `/payment-terms` | GET | Betalningsvillkor |
| `/api/free-card` | GET | Gratis dagskort (max 1/IP/dygn) |
| `/veckan` | GET | Gratis veckosida |
| `/api/weekly-card` | POST | Drar + genererar veckokort per tema |
| `/api/weekly-extra` | POST | Kinesiskt/numerologi-innehåll |
| `/api/weekly-qa` | POST | Q&A mot veckokontext |

### Kräver purchase_token eller admin
| Route | Metod | Beskrivning |
|-------|-------|-------------|
| `/` | GET | Huvud-appen |
| `/api/reading` | POST | Startar AI-läsning (SSE streaming) |
| `/api/followup` | POST | Följdfråga till AI |
| `/api/cards` | GET | Hämtar kortlistan |

### Admin (`/star`)
| Route | Beskrivning |
|-------|-------------|
| `/star` | Admin-inloggning |
| `/star/logout` | Loggar ut admin |
| `/star/overview` | Statistik-översikt |
| `/star/stats` | Besök och läsningar per dag |
| `/star/security` | Säkerhetshändelser + loggrensning |
| `/star/consent` | Samtycken från användare |
| `/star/cleanup` | POST — raderar loggar |

**Admin-inlogg:** `jjadmin` / lösenord i `.env` (`ADMIN_PASSWORD`)
**Admin har fri tillgång** till hela tarot-appen utan att behöva betala.

---

## Databas (SQLite — users.db)

### Tabeller

**`purchases`** — Köp via Stripe
```sql
id, stripe_session_id (UNIQUE), email, package, status,
access_token, ip, created, used_at, reading_done
```
- `status`: `pending` → `paid` → `used`
- `reading_done`: `0` eller `1`

**`consent_log`** — Juridiskt bevis på att villkor godkänts
```sql
id, ip, email, terms_version, accepted_terms, accepted_age,
accepted_entertainment, accepted_connectivity, accepted_withdrawal, created
```

**`free_card_draws`** — Begränsar gratis dagskort till 1/IP/dygn
```sql
ip, drawn (datum)
```

**`visits`** — Besöksloggning
```sql
id, ip, path, user_agent, created
```

**`security_events`** — Säkerhetshändelser (misslyckade inlogg, fil-scanning)
```sql
id, type, ip, detail, created
```

**`readings_log`** — Statistik över läsningar
```sql
id, user_id, spread_type, created
```

**`weekly_cards`** — Cachade veckokort per IP/tema/vecka
```sql
ip, tema, week, card_json, card_text, created
```

**`weekly_extra`** — Cachad kinesisk/numerologi-data per vecka
```sql
tema, cache_key, week, content
```

**`weekly_qa_sessions`** — Betalda Q&A-sessioner för veckan
```sql
id, stripe_session_id, access_token, tema, context,
questions_used, status, ip, created
```

---

## Stripe-integration

### Flöde
1. Frontend POST:ar till `/api/create-checkout-session` med paketkod
2. Server skapar `stripe.checkout.Session` och sparar pending-köp i DB
3. Kunden redirectas till Stripe's betalningssida
4. Efter betalning: Stripe redirectar till `/payment/success?session_id=...`
5. Server verifierar sessionen mot Stripe API, sätter status=`paid` i DB
6. Flask-sessionen sätts med `purchase_token` och `purchase_package`
7. Access-mail skickas automatiskt till kundens e-post

### Testa lokalt
Använd Stripe test-kortuppgifter: `4242 4242 4242 4242`, valfritt datum/CVC.

### Byta till live-nycklar (driftsättning)
Byt ut `pk_test_...` och `sk_test_...` mot live-nycklar i `.env` på servern.

---

## E-post (Resend)

**Access-mail** skickas automatiskt vid köp. Innehåller en engångslänk (`/access/<token>`) som ger tillbaka sessionen om kunden förlorar den.

**OBS:** Resend kräver verifierad domän för att skicka till godtyckliga e-postadresser. I produktion: verifiera `jjuniverse.se` i Resend-dashboarden och byt avsändare till `noreply@jjuniverse.se`.

---

## AI — Anthropic Claude

- **Modell:** `claude-haiku-4-5` (snabb och billig)
- **Streaming:** Server-Sent Events (SSE) — text skrivs ut i realtid
- **Systemprompt:** Varm, jordnära ton. Aldrig skrämmande. Döden = förändring.
- **Avslutning:** Varje läsning avslutas med `✦ Råd:` på egen rad
- **max_tokens:** 1500 för läsning och följdfrågor

**Byta modell** (i `app.py`):
```python
model="claude-haiku-4-5"   # Standard — billig, snabb
model="claude-sonnet-4-6"  # Bättre kvalitet
model="claude-opus-4-6"    # Bäst kvalitet, dyrast
```

---

## Läggningstyper

### 4 Frågor (`single`) — 30 kr
- Kunden skriver 1 fråga
- Drar 3 kort: Grunden / Kärnan / Vägen framåt
- AI ger sammanhängande tolkning + råd

### 12 Frågor (`triple`) — 60 kr
- Kunden skriver 3 frågor
- Drar 9 kort (3 per fråga)
- AI tolkar varje fråga + gemensamt råd

### Årsstjärnan (`year`) — 100 kr
- Ingen fråga
- 13 kort: 12 månader + 1 mittkort (årets tema)
- AI ger månadsvis energi (1-2 meningar/månad) + årsråd

---

## Juridik & villkor

Alla villkorssidor finns och är länkade i footern:
- `/terms` — Användarvillkor
- `/privacy` — Integritetspolicy
- `/payment-terms` — Betalningsvillkor (ångerrätt, ingen återbetalning)

Checkboxar som måste godkännas **vid villkorssidan** (sparas i `consent_log`):
1. Godkänner användarvillkor och integritetspolicy
2. Förstår att tjänsten är underhållning (ej medicinsk rådgivning)
3. Bekräftar 18+
4. Förstår att internetuppkoppling krävs

Checkboxar som måste godkännas **vid betalning** (kop_bekrafta):
1. 18+
2. Underhållning, ej rådgivning
3. Avsäger sig ångerrätten (EU-krav för digital leverans)
4. Inga återbetalningar vid missnöje

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

# 4. Skapa .env (lägg in dina riktiga nycklar)
cp .env.example .env

# 5. Starta
venv/bin/python3 app.py
# Öppna http://localhost:5001
```

### Testa som kund (lokalt)
1. `http://localhost:5001/welcome` → godkänn villkor
2. Klicka "Köp en läsning" → välj paket → bekräfta → betala med testkort `4242 4242 4242 4242`
3. Klicka "Påbörja min läsning" → gör läsning

### Testa som admin (lokalt)
1. Gå till `http://localhost:5001/star`
2. Logga in med `jjadmin` / `ADMIN_PASSWORD`
3. Gå sedan till `http://localhost:5001` — fri tillgång

---

## Produktion (Loopia VPS — jjuniverse.se)

**Server:** Ubuntu 24.04, Loopia VPS  
**Domän:** jjuniverse.se  
**Reverse proxy:** Caddy (sköter HTTPS automatiskt)  
**App-port:** 5001

### Sökvägar på servern
```
/home/johanna/apps/jjuniverse/
/etc/caddy/Caddyfile
/etc/systemd/system/jjuniverse.service
```

### Driftsätta en uppdatering
```bash
cd ~/apps/jjuniverse
git pull
sudo systemctl restart jjuniverse
sudo systemctl status jjuniverse
```

### Systemd-tjänst
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

---

## Felsökning

| Problem | Lösning |
|---------|---------|
| `ERR_TOO_MANY_REDIRECTS` | Session-loop — gå till `/welcome` och börja om |
| `ModuleNotFoundError: stripe` | `pip install stripe` i venv |
| `ModuleNotFoundError: resend` | `pip install resend` i venv |
| Stripe-betalning misslyckas | Kontrollera `STRIPE_SECRET_KEY` i `.env` |
| Mail skickas inte | Verifiera domänen i Resend-dashboarden |
| Streaming fungerar inte | Kontrollera `X-Accel-Buffering: no` i proxy |
| DB-fel | `venv/bin/python3 -c "from database import init_db; init_db()"` |
| Kunden kan inte backa | Korrekt — `/session/check` skyddar mot fusk |

---

## Support

**Support-mail:** jjuniverse.support@gmail.com

---

## Byggt & klart

- [x] Stripe-betalning (30/60/100 kr — test och live-redo)
- [x] Gästköp utan konto (ingen registrering)
- [x] Villkorssida med 4 checkboxar (sparas juridiskt i DB)
- [x] Betalningsbekräftelse med 4 checkboxar (ångerrätt)
- [x] Access-mail med engångslänk vid köp
- [x] Bakåtknapp-skydd (`/session/check` + `reading_done`)
- [x] Admin-panel på `/star` (översikt, statistik, säkerhet, samtycken)
- [x] Säkerhetsvarningsmail vid brute force/fil-scanning
- [x] Auto-rensning av loggar äldre än 7 dagar (vid serverstart)
- [x] Manuell loggrensning per dag eller allt >7 dagar i admin
- [x] Gratis dagskort (1 per IP och dygn)
- [x] Gratis veckosida (`/veckan`) med kärlek/ekonomi/energi/visdom, månfas, kinesiskt horoskop, numerologi
- [x] Dynamisk månfas-SVG (beräknas matematiskt, ingen extern API)
- [x] Dela-knappar för veckoläsningar
- [x] Kortförstoring via modal
- [x] Användarvillkor, Integritetspolicy, Betalningsvillkor

## Möjliga nästa steg

- [ ] Byta Resend-avsändare till `noreply@jjuniverse.se` (kräver DNS-verifiering)
- [ ] Sätta upp Stripe webhook-secret i produktion
- [ ] Byta Stripe test-nycklar mot live-nycklar
- [ ] Fler läggningstyper (keltiskt kors etc.)
