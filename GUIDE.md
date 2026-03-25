# JJ Universe — Teknisk dokumentation

## Vad är JJ Universe?

JJ Universe är en betaltjänst för AI-genererad tarotläsning. Besökare köper en session via Stripe, väljer en läggningstyp, drar kort och får en personlig tolkning via Claude AI. Inga konton krävs — man betalar direkt som gäst.

---

## Teknisk stack

| Del | Teknologi |
|-----|-----------|
| Backend | Python 3, Flask |
| AI | Anthropic Claude Haiku (`claude-haiku-4-5`) |
| Databas | SQLite (`users.db`) |
| Betalning | Stripe Checkout |
| E-post | Resend (läsningar + access-mail) |
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
│   ├── login.html            # Inloggning, registrering och köp-knapp
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
│   └── admin_panel.html      # Admin-panel (översikt/statistik/säkerhet)
└── static/
    ├── css/
    │   ├── style.css         # Huvudstil — mörkt mystiskt tema
    │   └── login.css         # Stil för inloggningssidan
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
ADMIN_PASSWORD=kokobahia3535A!       # Admin-lösenord för /star
ADMIN_EMAIL=jjuniverse.support@gmail.com  # Dit säkerhetsvarningar skickas
STRIPE_PUBLIC_KEY=pk_test_...        # Stripe publika nyckel (test/live)
STRIPE_SECRET_KEY=sk_test_...        # Stripe hemliga nyckel (test/live)
STRIPE_WEBHOOK_SECRET=               # Stripe webhook-signatur (valfritt, kan lämnas tom)
```

> **OBS:** Dela aldrig dessa värden i chatt eller i git. `.env` är listad i `.gitignore`.

### Lägga till saknade värden på servern

Om en nyckel saknas på servern, lägg till den med:
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
| En Fråga | `single` | 60 kr | 1 läggning (3 kort) + 3 följdfrågor |
| Tre Frågor | `triple` | 150 kr | 3 läggningar + 3 följdfrågor/läggning |
| Årsstjärnan | `year` | 300 kr | 13 kort (helår) + 3 följdfrågor |

Priserna anges i **öre** i koden (`6000` = 60 kr). Definerade i `PACKAGES` i `app.py`.

---

## Användarflöde (kund)

```
1. Besök jjuniverse.se
       ↓
2. /welcome — Villkorssida (4 checkboxar, sparas i DB)
       ↓
3. /login — Inloggningssida
   - Kan skapa konto (ger INTE fri tillgång — måste ändå köpa)
   - Kan logga in (ger INTE fri tillgång — måste ändå köpa)
   - Klickar "Köp en läsning" → /kop
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
    - Ställa upp till 3 följdfrågor (text)
    - Göra "Följdfråga med kort" (extra kort)
    - Skicka läsningen till sin e-post
    - Klicka "Ny läsning" → /kop (ny betalning krävs)
    - Klicka "Logga ut" → sessionen rensas → /login
```

---

## Sessionssystem

Appen använder Flask-sessioner (krypterade cookies).

| Sessionsvariabel | Vad den gör |
|-----------------|-------------|
| `consent_given` | Satt när villkor godkänts. Krävs för att komma förbi /welcome |
| `purchase_token` | Unik token kopplad till ett köp i DB. Ger tillgång till appen |
| `purchase_package` | Vilken typ köptes (`single`/`triple`/`year`). Styr auto-val i appen |
| `user_id` | Satt om man loggat in med konto. Ger INTE fri tillgång |
| `username` | Kontonamn (visas i appen om inloggad) |
| `admin_logged_in` | Satt vid admin-inlogg. Ger fri tillgång till hela appen |

### Accessskydd

- Alla behöver `purchase_token` **eller** `admin_logged_in` för att komma in i appen
- `login_required`-dekoratorn skyddar alla API-routes
- Om `purchase_token` saknas → redirect till `/login`

---

## Säkerhetsvarningar

### Vad triggar en varning?

| Händelse | Gräns |
|----------|-------|
| Brute force mot admin | 5+ misslyckade inlogg från samma IP på 10 minuter |
| Känslig fil-scanning | Någon försöker nå `.env`, `.git`, `config.php`, `aws-config`, `wp-login` |

### Var syns varningarna?

**Varningsbanner i admin-panelen** — visas högst upp på alla admin-sidor om en aktiv varning finns (senaste 10 min / 1 timme beroende på typ).

**Varningsmail** — skickas till `ADMIN_EMAIL` i `.env` (max 1 gång per timme per typ för att undvika spam).

### Loggrensning

Loggar (`security_events` och `visits`) rensas automatiskt **vid varje serveromstart** om de är äldre än 7 dagar.

Under **Säkerhet** i admin-panelen finns även två manuella knappar:
- **Radera dag** — välj ett datum i datumväljaren och radera enbart den dagens loggar
- **Rensa >7 dagar** — raderar allt äldre än 7 dagar direkt (samma som auto-rensningen)

---

## Bakåtknapp-skydd (anti-fusk)

En kund som navigerar bakåt efter en läsning ska inte kunna göra en ny läsning gratis.

**Lösning — tre lager:**

**1. JS history-manipulation** körs när köpsessionen startar:
```javascript
history.replaceState(null, '', '/');
history.pushState(null, '', '/');
```
Lägger till ett extra historik-steg så att bakåtknappen triggar `popstate` istället för att lämna sidan direkt.

**2. Confirm-dialog** visas vid `popstate` (bakåtknapp):
```javascript
window.addEventListener('popstate', () => {
  history.pushState(null, '', '/');  // tryck tillbaka historiken igen
  const leave = confirm(
    'Vill du lämna din läsning?\n\n' +
    'Din session kan gå förlorad och du kan behöva köpa en ny läsning.'
  );
  if (leave) {
    window.location.replace('/session/check');
  }
});
```
- Kunden väljer **Avbryt** → stannar kvar på sidan, ingenting händer
- Kunden väljer **OK** → server-kontroll via `/session/check`

**3. `/session/check`** (Flask-route) är den definitiva serverskyddet:
- `reading_done=0` → redirect till `/` (kan fortsätta läsningen)
- `reading_done=1` → rensar session → redirect till `/kop` (ny betalning krävs)
- Ingen `purchase_token` alls → redirect till `/kop`

**`reading_done`** sätts till `1` i DB direkt när `/api/reading` anropas (innan streaming startar). Det innebär att om kunden stänger webbläsaren mitt i läsningen räknas sessionen som förbrukad.

**OBS:** `beforeunload`-skyddet (som visas vid sidstängning/reload) aktiveras enbart under pågående AI-streaming — inte hela sessionen — för att inte störa normal navigering.

---

## Routes (app.py)

### Publika
| Route | Metod | Beskrivning |
|-------|-------|-------------|
| `/welcome` | GET | Villkorssida |
| `/api/consent` | POST | Sparar godkännande i DB |
| `/login` | GET/POST | Inloggning + registrering |
| `/register` | POST | Skapa konto |
| `/logout` | GET | Rensar hela sessionen |
| `/kop` | GET | Paketval |
| `/kop/bekrafta` | GET | Bekräftelse innan betalning |
| `/api/create-checkout-session` | POST | Skapar Stripe-session, returnerar URL |
| `/payment/success` | GET | Bekräftelse efter betalning |
| `/payment/cancel` | GET | Avbruten betalning |
| `/webhook/stripe` | POST | Stripe-webhook (uppdaterar DB) |
| `/access/<token>` | GET | Engångslänk för att återfå tillgång |
| `/session/end` | GET | Loggar ut kunden (rensar session, behåller consent) |
| `/session/check` | GET | Kontrollerar reading_done vid bakåtnavigering |
| `/terms` | GET | Användarvillkor |
| `/privacy` | GET | Integritetspolicy |
| `/payment-terms` | GET | Betalningsvillkor |
| `/api/free-card` | GET | Gratis dagskort (max 1/IP/dygn) |

### Kräver purchase_token eller admin
| Route | Metod | Beskrivning |
|-------|-------|-------------|
| `/` | GET | Huvud-appen |
| `/api/reading` | POST | Startar AI-läsning (SSE streaming) |
| `/api/followup` | POST | Följdfråga till AI |
| `/api/send-reading` | POST | Skickar läsning via Resend |
| `/api/cards` | GET | Hämtar kortlistan |

### Admin (`/star`)
| Route | Beskrivning |
|-------|-------------|
| `/star` | Admin-inloggning |
| `/star/logout` | Loggar ut admin |
| `/star/overview` | Statistik-översikt |
| `/star/stats` | Besök och läsningar per dag |
| `/star/security` | Säkerhetshändelser + loggrensning |
| `/star/cleanup` | POST — raderar loggar (används av knapparna i admin-panelen) |

**Admin-inlogg:** `jjadmin` / lösenord i `.env` (`ADMIN_PASSWORD`)
**Admin har fri tillgång** till hela tarot-appen utan att behöva betala.

---

## Databas (SQLite — users.db)

### Tabeller

**`users`** — Konton
```sql
id, username (UNIQUE), password (hashad), created
```

**`purchases`** — Köp via Stripe
```sql
id, stripe_session_id (UNIQUE), email, package, status,
access_token, ip, created, used_at, reading_done
```
- `status`: `pending` → `paid` → `used`
- `reading_done`: `0` eller `1`
- `access_token`: unik token för access-mail

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

**`security_events`** — Säkerhetshändelser
```sql
id, type, ip, detail, created
```

**`readings_log`** — Statistik över läsningar
```sql
id, user_id, spread_type, created
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

Två sorters mail skickas:
1. **Access-mail** — skickas automatiskt vid köp. Innehåller en engångslänk (`/access/<token>`) som ger tillbaka sessionen om kunden förlorar den.
2. **Läsningsmail** — kunden kan klicka "Skicka till min mail" i appen och få hela läsningen skickad.

**OBS:** Resend kräver verifierad domän för att skicka till godtyckliga e-postadresser. Under development används `onboarding@resend.dev` som avsändare (begränsad). I produktion: verifiera `jjuniverse.se` i Resend-dashboarden och byt avsändare till `noreply@jjuniverse.se`.

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

## Följdfrågor

- Max **3 textfrågor** per läsning (enforced i JS + räknas av MAX_FOLLOWUPS)
- Max **3 kortfrågor** per läsning (eget kort dras till varje fråga)
- Konversationshistoriken skickas med varje anrop (full kontext för AI:n)
- Korten stannar synliga i historiken vid kortfrågor

---

## Läggningstyper

### En Fråga (`single`) — 60 kr
- Kunden skriver 1 fråga
- Drar 3 kort: Grunden / Kärnan / Vägen framåt
- AI ger sammanhängande tolkning + råd

### Tre Frågor (`triple`) — 150 kr
- Kunden skriver 3 frågor
- Drar 9 kort (3 per fråga)
- AI tolkar varje fråga + gemensamt råd

### Årsstjärnan (`year`) — 300 kr
- Ingen fråga
- 13 kort: 12 månader + 1 mittort (årets tema)
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
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Installera beroenden
pip install -r requirements.txt

# 4. Skapa .env (lägg in dina riktiga nycklar)
cp .env.example .env   # eller skapa manuellt

# 5. Starta
python app.py
# Öppna http://localhost:5000
```

### Testa som kund (lokalt)
1. `http://localhost:5000/logout` — rensa eventuell session
2. Godkänn villkor → inloggningssida
3. Klicka "Köp en läsning" → välj paket → bekräfta → betala med testkort `4242 4242 4242 4242`
4. Klicka "Påbörja min läsning" → gör läsning

### Testa som admin (lokalt)
1. Gå till `http://localhost:5000/star`
2. Logga in med `jjadmin` / `ADMIN_PASSWORD`
3. Gå sedan till `http://localhost:5000` — fri tillgång

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

### Installera nya paket på servern
```bash
source ~/apps/jjuniverse/venv/bin/activate
pip install resend stripe
sudo systemctl restart jjuniverse
```

---

## Felsökning

| Problem | Lösning |
|---------|---------|
| `ERR_TOO_MANY_REDIRECTS` | Session-loop — gå till `/logout` för att rensa |
| `ModuleNotFoundError: stripe` | `pip install stripe` i venv |
| `ModuleNotFoundError: resend` | `pip install resend` i venv |
| Stripe-betalning misslyckas | Kontrollera `STRIPE_SECRET_KEY` i `.env` |
| Mail skickas inte | Verifiera domänen i Resend-dashboarden |
| Streaming fungerar inte | Kontrollera `X-Accel-Buffering: no` i proxy |
| Port 5000 upptagen | `fuser -k 5000/tcp` |
| DB-fel | `python -c "from database import init_db; init_db()"` |
| Kunden kan inte backa | Korrekt — `/session/check` skyddar mot fusk |

---

## Support

**Support-mail:** jjuniverse.support@gmail.com

---

## Byggt & klart

- [x] Stripe-betalning (single/triple/year — test och live-redo)
- [x] Gästköp utan konto
- [x] Villkorssida med 4 checkboxar (sparas juridiskt i DB)
- [x] Betalningsbekräftelse med 4 checkboxar (ångerrätt)
- [x] Access-mail med engångslänk vid köp
- [x] Bakåtknapp-skydd (`/session/check` + `reading_done`)
- [x] "Logga ut"-knapp efter läsning + "Avsluta" på köpsidan
- [x] Admin-panel på `/star` (fri tillgång till appen, statistik, säkerhet)
- [x] Säkerhetsvarningar — banner i admin + varningsmail vid brute force/fil-scanning
- [x] Auto-rensning av loggar äldre än 7 dagar (vid serverstart)
- [x] Manuell loggrensning per dag eller allt >7 dagar i admin-panelen
- [x] Gratis dagskort (1 per IP och dygn, på inloggningssidan)
- [x] Kortförstoring via modal
- [x] Skicka läsning till e-post (Resend)
- [x] Cookie-banner
- [x] Användarvillkor, Integritetspolicy, Betalningsvillkor
- [x] Besöksloggning, läsningsloggning, säkerhetshändelser

## Möjliga nästa steg

- [ ] Byta Resend-avsändare till `noreply@jjuniverse.se` (kräver DNS-verifiering)
- [ ] Sätta upp Stripe webhook-secret i produktion
- [ ] Byta Stripe test-nycklar mot live-nycklar
- [ ] Fler läggningstyper (keltiskt kors etc.)
- [ ] Erbjuda paket med rabatt (t.ex. prenumeration)
