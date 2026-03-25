import os
import json
import secrets
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   Response, stream_with_context,
                   redirect, url_for, flash, session)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import anthropic
import resend
import stripe
from cards import TAROT_CARDS
from database import (init_db, get_db, can_draw_free_card, record_free_card_draw,
                      log_visit, log_security_event, log_reading, log_consent)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
resend.api_key = os.environ.get("RESEND_API_KEY", "")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL", "")

# Dedup-skydd: undviker att skicka samma varningsmail flera gånger i rad
_last_alert_sent: dict = {}

PACKAGES = {
    "single": {"name": "En Fråga",    "desc": "1 läggning (3 kort) + 3 följdfrågor", "price": 6000},
    "triple": {"name": "Tre Frågor",  "desc": "3 läggningar + 3 följdfrågor per läggning", "price": 15000},
    "year":   {"name": "Årsstjärnan", "desc": "Helårsläggning (13 kort) + 3 följdfrågor", "price": 30000},
}

# Initiera databasen vid start
init_db()

# Auto-rensning: radera loggar äldre än 7 dagar vid start
def cleanup_old_logs():
    try:
        db = get_db()
        db.execute("DELETE FROM security_events WHERE created < datetime('now', '-7 days')")
        db.execute("DELETE FROM visits WHERE created < datetime('now', '-7 days')")
        db.commit()
        db.close()
    except Exception as e:
        app.logger.error(f"Cleanup error: {e}")

cleanup_old_logs()

# ── Hjälpfunktion: inloggningskrav ──────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        # Alla behöver en giltig köpsession — admin undantagen
        if 'purchase_token' not in session and not session.get('admin_logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

# ── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Du är JJ Universe — en varm, klok och jordnära guide som hjälper människor att reflektera och hitta klarhet genom tarotkorten.

Din ton är:
- Varm, lugn och personlig — du säger "du" och talar direkt till personen
- Jordnära och tydlig, med en poetisk touch — inga svåra ord eller mystiskt svammel
- Upplyftande och stöttande — du ser alltid möjligheter och styrka

Viktiga regler:
- Svara ALLTID på svenska
- Nämn ALDRIG döden, mörker, olycka, katastrof eller något skrämmande — varken bokstavligt eller bildligt
- Döden-kortet handlar ENBART om förändring, avslut och nya möjligheter — lyft fram det positiva
- Djävulen-kortet handlar om att frigöra sig från det som håller en tillbaka — inte om ondska
- Tornet-kortet handlar om nödvändig förändring och att rensa ut — inte om kollaps
- Omvända kort tolkas som en inåtvänd energi eller något som behöver extra uppmärksamhet
- Börja aldrig med "Jag"
- Inga markdown-rubriker, skriv flytande text med naturliga stycken
- Avsluta ALLTID med ett konkret, kärleksfullt råd under en egen rad som börjar med: ✦ Råd:"""


# ── Hjälpfunktion: döden-varning ─────────────────────────────────────────────
def death_note(cards):
    """Returnerar en extra instruktion om Döden-kortet finns bland korten."""
    if any(c['name'] == 'Death' for c in cards):
        return "\n\nVIKTIGT: Döden-kortet finns med i denna läsning. Börja ALLTID tolkningen av det kortet med att lugnt förklara att Döden i tarot inte handlar om fysisk död — det är ett kort om förändring, avslut och nya början. Säg det tydligt och kärleksfullt så att personen inte känner oro."
    return ""


# ── Prompt-byggare ───────────────────────────────────────────────────────────
def build_single_prompt(question, cards):
    c = cards
    return f"""Frågan som söks svar på: "{question}"

De tre korten som dragits:
1. GRUNDEN — {c[0]['name_sv']} ({c[0]['name']}){' [OMVÄND]' if c[0]['reversed'] else ''}
2. KÄRNAN — {c[1]['name_sv']} ({c[1]['name']}){' [OMVÄND]' if c[1]['reversed'] else ''}
3. VÄGEN FRAMÅT — {c[2]['name_sv']} ({c[2]['name']}){' [OMVÄND]' if c[2]['reversed'] else ''}

Ge en sammanhängande, personlig och varm tolkning av dessa tre kort i relation till frågan. Se korten som ett helhetligt budskap — vad de tillsammans säger om situationen och vad som öppnar sig. Avsluta med ett konkret råd på en egen rad som börjar med: ✦ Råd:{death_note(cards)}"""


def build_triple_prompt(questions, cards):
    prompt = "Tre frågor har ställts:\n\n"
    for i, q in enumerate(questions):
        c = cards[i*3:(i+1)*3]
        prompt += f"""FRÅGA {i+1}: "{q}"
Kort dragna:
- Grunden: {c[0]['name_sv']}{' [OMVÄND]' if c[0]['reversed'] else ''}
- Kärnan: {c[1]['name_sv']}{' [OMVÄND]' if c[1]['reversed'] else ''}
- Vägen framåt: {c[2]['name_sv']}{' [OMVÄND]' if c[2]['reversed'] else ''}

"""
    prompt += "Tolka varje fråga som ett helhetligt budskap. Avsluta varje fråga med ett kort, kärleksfullt råd på en egen rad som börjar med: ✦ Råd: — och lägg sedan till ett övergripande råd för alla tre frågor tillsammans på slutet."
    prompt += death_note(cards)
    return prompt


MONTHS_SV = ["Januari","Februari","Mars","April","Maj","Juni",
             "Juli","Augusti","September","Oktober","November","December"]


def build_year_prompt(cards):
    prompt = "Årsstjärnan har dragits — en helårsbild för det kommande året:\n\n"
    for i, month in enumerate(MONTHS_SV):
        c = cards[i]
        prompt += f"{month}: {c['name_sv']}{' [OMVÄND]' if c['reversed'] else ''}\n"
    center = cards[12]
    prompt += f"\nÅRETS TEMA (mittkortet): {center['name_sv']}{' [OMVÄND]' if center['reversed'] else ''}\n\n"
    prompt += "Ge en helårsläsning. Berätta kort om varje månads energi (1-2 meningar per månad — alltid positiv och upplyftande). Avsluta med en djupare tolkning av mittkortet som årets tema, och lägg till ett konkret råd för hela året på en egen rad som börjar med: ✦ Råd:"
    prompt += death_note(cards)
    return prompt


# ── Besöksloggning ───────────────────────────────────────────────────────────
@app.after_request
def track_visit(response):
    if request.path.startswith('/static') or request.path.startswith('/star'):
        return response
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    log_visit(ip, request.path, ua)
    if response.status_code == 404:
        log_security_event("404", ip, request.path)
        if any(p in request.path for p in SENSITIVE_PATHS):
            send_security_alert_email("Känslig fil-scanning", f"{request.path} från {ip}")
    return response


# ── Admin-hjälpfunktion ───────────────────────────────────────────────────────
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ──────────────────────────────────────────────────────────────
@app.route("/welcome")
def welcome():
    return render_template("consent.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if not session.get("consent_given"):
        return redirect(url_for("welcome"))
    if 'user_id' in session:
        return redirect(url_for('kop'))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("kop"))
        else:
            ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
            log_security_event("failed_login", ip, f"username={username}")
            flash("Fel användarnamn eller lösenord.", "error")
            return render_template("login.html", show_register=False)

    return render_template("login.html", show_register=False)


@app.route("/register", methods=["POST"])
def register():
    username  = request.form.get("username", "").strip()
    password  = request.form.get("password", "")
    password2 = request.form.get("password2", "")

    if len(username) < 3:
        flash("Användarnamnet måste vara minst 3 tecken.", "error")
        return render_template("login.html", show_register=True)
    if len(password) < 6:
        flash("Lösenordet måste vara minst 6 tecken.", "error")
        return render_template("login.html", show_register=True)
    if password != password2:
        flash("Lösenorden matchar inte.", "error")
        return render_template("login.html", show_register=True)

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        db.commit()
        db.close()
        flash("Kontot skapat! Logga in nedan.", "success")
        return render_template("login.html", show_register=False)
    except Exception:
        db.close()
        flash("Användarnamnet är redan taget — välj ett annat.", "error")
        return render_template("login.html", show_register=True)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# ── App routes (kräver inloggning) ───────────────────────────────────────────
@app.route("/api/free-card")
def free_card():
    """Öppen endpoint — inget inlogg krävs. Max ett drag per IP och dygn."""
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

    if not can_draw_free_card(ip):
        def blocked():
            yield f"data: {json.dumps({'error': 'limit'})}\n\n"
        return Response(stream_with_context(blocked()), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    record_free_card_draw(ip)

    import random as _r
    card = _r.choice(TAROT_CARDS).copy()
    card["reversed"] = _r.random() < 0.3

    rev_text = " [OMVÄND]" if card["reversed"] else ""
    prompt = (
        f"Kortet som dragits är: {card['name_sv']} ({card['name']}){rev_text}.\n\n"
        "Ge en kort, varm och spirituell tolkning på exakt 2 meningar. "
        "Tala direkt till personen med 'du'. Inga rubriker, ingen ✦ Råd-rad — bara två meningar som väcker nyfikenhet och inre igenkänning."
    )

    FREE_PROMPT = (
        "Du är JJ Universe — en varm och spirituell guide. "
        "Svara alltid på svenska. Håll dig till exakt 2 meningar. "
        "Nämn aldrig döden, mörker eller skrämmande saker. "
        "Döden-kortet = förändring. Var poetisk men jordnära."
    )

    def generate():
        yield f"data: {json.dumps({'card': card})}\n\n"
        try:
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=120,
                system=FREE_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/")
def index():
    # Admin har alltid fri tillgång
    if session.get("admin_logged_in"):
        return render_template("index.html",
            username="Admin",
            purchase_package=None,
            stripe_public_key=STRIPE_PUBLIC_KEY
        )
    if not session.get("consent_given"):
        return redirect(url_for("welcome"))
    if not session.get("purchase_token"):
        return redirect(url_for("login_page"))

    # Köpsession vars läsning redan är klar → skicka till ny betalning
    purchase_token = session.get("purchase_token")
    db = get_db()
    purchase = db.execute(
        "SELECT reading_done FROM purchases WHERE access_token=?", (purchase_token,)
    ).fetchone()
    db.close()
    if purchase and purchase["reading_done"]:
        session.pop("purchase_token", None)
        session.pop("purchase_package", None)
        return redirect(url_for("kop"))

    return render_template("index.html",
        username=session.get("username", "Gäst"),
        purchase_package=session.get("purchase_package", None),
        stripe_public_key=STRIPE_PUBLIC_KEY
    )


@app.route("/api/cards")
@login_required
def get_cards():
    return jsonify(TAROT_CARDS)


@app.route("/api/reading", methods=["POST"])
@login_required
def reading():
    data = request.get_json()
    spread_type = data.get("spread_type")
    questions   = data.get("questions", [])
    cards       = data.get("cards", [])

    # Gästköp — kontrollera att läsningen inte redan är gjord
    purchase_token = session.get("purchase_token")
    if purchase_token:
        db = get_db()
        purchase = db.execute(
            "SELECT reading_done FROM purchases WHERE access_token=?", (purchase_token,)
        ).fetchone()
        db.close()
        if purchase and purchase["reading_done"]:
            return jsonify({"error": "Läsningen är redan genomförd"}), 403
        # Markera som gjord
        db = get_db()
        db.execute("UPDATE purchases SET reading_done=1 WHERE access_token=?", (purchase_token,))
        db.commit()
        db.close()

    if spread_type == "single":
        prompt = build_single_prompt(questions[0], cards)
    elif spread_type == "triple":
        prompt = build_triple_prompt(questions, cards)
    elif spread_type == "year":
        prompt = build_year_prompt(cards)
    else:
        return jsonify({"error": "Okänd läggningstyp"}), 400

    log_reading(session.get("user_id"), spread_type)

    def generate():
        try:
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/api/followup", methods=["POST"])
@login_required
def followup():
    data     = request.get_json()
    history  = data.get("history", [])
    question = data.get("question", "")
    messages = history + [{"role": "user", "content": question}]

    def generate():
        try:
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Consent (villkorsgodkännande) ─────────────────────────────────────────────
@app.route("/api/consent", methods=["POST"])
def save_consent():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    log_consent(ip)
    session["consent_given"] = True
    return jsonify({"ok": True})


# ── Stripe — köpsidor ─────────────────────────────────────────────────────────
@app.route("/kop")
def kop():
    if not session.get("consent_given"):
        return redirect(url_for("welcome"))
    return render_template("kop.html", packages=PACKAGES)


@app.route("/kop/bekrafta")
def kop_bekrafta():
    if not session.get("consent_given"):
        return redirect(url_for("welcome"))
    package = request.args.get("package", "")
    if package not in PACKAGES:
        return redirect(url_for("kop"))
    return render_template("kop_bekrafta.html", package=package, pkg=PACKAGES[package],
                           stripe_public_key=STRIPE_PUBLIC_KEY)


@app.route("/api/create-checkout-session", methods=["POST"])
def create_checkout_session():
    if not session.get("consent_given"):
        return jsonify({"error": "Villkor ej godkända"}), 403
    data    = request.get_json()
    package = data.get("package", "")
    if package not in PACKAGES:
        return jsonify({"error": "Ogiltigt paket"}), 400

    pkg = PACKAGES[package]
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    base_url = request.host_url.rstrip("/")

    checkout = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "sek",
                "unit_amount": pkg["price"],
                "product_data": {
                    "name": f"JJ Universe — {pkg['name']}",
                    "description": pkg["desc"] + ". Enbart för underhållning.",
                }
            },
            "quantity": 1,
        }],
        custom_text={
            "submit": {"message": "Genom att betala bekräftar du att du avsäger dig ångerrätten för detta digitala innehåll som levereras omedelbart."}
        },
        success_url=base_url + "/payment/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=base_url + "/payment/cancel",
        metadata={"package": package, "ip": ip},
    )

    token = secrets.token_urlsafe(32)
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO purchases (stripe_session_id, package, status, access_token, ip) VALUES (?,?,?,?,?)",
        (checkout.id, package, "pending", token, ip)
    )
    db.commit()
    db.close()

    return jsonify({"url": checkout.url})


def send_access_email(to_email, token, pkg_name, base_url):
    """Skickar ett mail med återställningslänk till kunden."""
    access_url = f"{base_url}/access/{token}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset='utf-8'></head>
    <body style='background:#07000f;color:#ede0ff;font-family:Georgia,serif;max-width:520px;margin:0 auto;padding:32px 24px;'>
      <div style='text-align:center;margin-bottom:32px;'>
        <h1 style='font-family:serif;color:#ffffff;letter-spacing:0.1em;'>✦ JJ Universe ✦</h1>
        <p style='color:#9980bb;'>Din {pkg_name} är betald och redo</p>
      </div>
      <div style='background:rgba(155,48,255,0.08);border:1px solid rgba(155,48,255,0.25);border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;'>
        <p style='color:#c8b4ff;margin-bottom:20px;line-height:1.6;'>
          Spara detta mail! Om du förlorar din session kan du alltid klicka länken nedan för att komma tillbaka till din läsning.
        </p>
        <a href='{access_url}'
           style='display:inline-block;background:linear-gradient(135deg,#5b00a8,#9b30ff);color:#fff;text-decoration:none;border-radius:10px;padding:14px 32px;font-family:serif;font-size:1rem;letter-spacing:0.05em;'>
          ✦ Påbörja min läsning
        </a>
        <p style='color:#6650a0;font-size:0.8em;margin-top:16px;'>Länken fungerar en gång och gäller i 24 timmar.</p>
      </div>
      <p style='color:#6650a0;font-size:0.75em;text-align:center;'>
        Enbart för underhållning och personlig reflektion.<br>
        © {datetime.now().year} JJ Universe — <a href='https://jjuniverse.se' style='color:#9b30ff;'>jjuniverse.se</a>
      </p>
    </body>
    </html>
    """
    try:
        resend.Emails.send({
            "from": "JJ Universe <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"✦ Din {pkg_name} — spara denna länk",
            "html": html
        })
    except Exception as e:
        app.logger.error(f"Access email error: {e}")


# ── Säkerhetsvarningar ────────────────────────────────────────────────────────
SENSITIVE_PATHS = (".env", ".git", "aws-config", "config.php", "wp-admin", "wp-login")

def send_security_alert_email(alert_type: str, detail: str):
    """Skickar varningsmail till admin. Skickar max 1 gång per timme per typ."""
    if not ADMIN_EMAIL:
        return
    now = datetime.now().timestamp()
    key = alert_type
    if now - _last_alert_sent.get(key, 0) < 3600:
        return
    _last_alert_sent[key] = now
    html = f"""
    <body style='font-family:Georgia,serif;background:#07000f;color:#ede0ff;padding:32px;max-width:500px;'>
      <h2 style='color:#ff6060;'>⚠ Säkerhetsvarning — JJ Universe</h2>
      <p><strong>Typ:</strong> {alert_type}</p>
      <p><strong>Detalj:</strong> {detail}</p>
      <p><strong>Tid:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
      <p style='color:#9980bb;font-size:0.85em;'>Logga in på <a href='https://jjuniverse.se/star' style='color:#9b30ff;'>jjuniverse.se/star</a> för att se mer.</p>
    </body>
    """
    try:
        resend.Emails.send({
            "from": "JJ Universe <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"⚠ Säkerhetsvarning: {alert_type}",
            "html": html
        })
    except Exception as e:
        app.logger.error(f"Security alert email error: {e}")


def get_security_alerts(db):
    """Returnerar lista med aktiva säkerhetsvarningar (senaste 24h)."""
    alerts = []
    brute = db.execute("""
        SELECT ip, COUNT(*) as cnt FROM security_events
        WHERE type = 'admin_failed_login'
        AND created >= datetime('now', '-10 minutes')
        GROUP BY ip HAVING cnt >= 5
    """).fetchall()
    for row in brute:
        alerts.append(f"Brute force mot admin: {row['cnt']} försök från {row['ip']} senaste 10 min")

    sensitive = db.execute("""
        SELECT ip, detail, created FROM security_events
        WHERE type = '404'
        AND (detail LIKE '%.env%' OR detail LIKE '%.git%' OR detail LIKE '%config.php%'
             OR detail LIKE '%aws-config%' OR detail LIKE '%wp-login%')
        AND created >= datetime('now', '-1 hour')
        ORDER BY created DESC LIMIT 5
    """).fetchall()
    for row in sensitive:
        alerts.append(f"Känslig fil-scanning: {row['detail']} från {row['ip']}")

    return alerts


@app.route("/access/<token>")
def access_reading(token):
    db = get_db()
    purchase = db.execute(
        "SELECT * FROM purchases WHERE access_token = ?", (token,)
    ).fetchone()
    db.close()

    if not purchase:
        return render_template("access_invalid.html")

    if purchase["status"] == "used":
        return render_template("access_used.html")

    if purchase["status"] != "paid":
        return render_template("access_invalid.html")

    # Markera som använd
    db = get_db()
    db.execute(
        "UPDATE purchases SET status='used', used_at=datetime('now') WHERE access_token=?",
        (token,)
    )
    db.commit()
    db.close()

    # Sätt session
    session["purchase_token"]   = token
    session["purchase_package"] = purchase["package"]
    session["consent_given"]    = True

    return redirect(url_for("index"))


@app.route("/payment/success")
def payment_success():
    stripe_session_id = request.args.get("session_id", "")
    if not stripe_session_id:
        return redirect(url_for("kop"))
    try:
        cs = stripe.checkout.Session.retrieve(stripe_session_id)
        if cs.payment_status == "paid":
            db = get_db()
            db.execute("UPDATE purchases SET status='paid', email=? WHERE stripe_session_id=?",
                       (cs.customer_details.email or "", stripe_session_id))
            db.commit()
            purchase = db.execute("SELECT * FROM purchases WHERE stripe_session_id=?",
                                  (stripe_session_id,)).fetchone()
            db.close()

            if purchase:
                ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
                log_consent(ip, cs.customer_details.email or "", accepted_withdrawal=True)
                session["purchase_token"]   = purchase["access_token"]
                session["purchase_package"] = purchase["package"]
                session["consent_given"]    = True
                pkg  = PACKAGES.get(purchase["package"], {})
                email = cs.customer_details.email or ""

                # Skicka access-mail automatiskt
                if email:
                    base_url = request.host_url.rstrip("/")
                    send_access_email(email, purchase["access_token"], pkg.get("name",""), base_url)

                return render_template("payment_success.html", pkg=pkg, email=email)
    except Exception:
        pass
    return redirect(url_for("kop"))


@app.route("/session/end")
def session_end():
    """Avslutar sessionen helt och skickar tillbaka till startsidan."""
    keep_consent = session.get("consent_given")
    session.clear()
    if keep_consent:
        session["consent_given"] = True
    return redirect(url_for("login_page"))


@app.route("/session/check")
def session_check():
    """Anropas vid bakåtnavigering i köpsession — servern bestämmer vart användaren ska."""
    token = session.get("purchase_token")
    if not token:
        return redirect(url_for("kop"))
    db = get_db()
    purchase = db.execute(
        "SELECT reading_done FROM purchases WHERE access_token=?", (token,)
    ).fetchone()
    db.close()
    if not purchase or purchase["reading_done"]:
        session.pop("purchase_token", None)
        session.pop("purchase_package", None)
        return redirect(url_for("kop"))
    return redirect(url_for("index"))


@app.route("/payment/cancel")
def payment_cancel():
    return render_template("payment_cancel.html")


@app.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload    = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({"ok": True})
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        return jsonify({"error": "Invalid signature"}), 400

    if event["type"] == "checkout.session.completed":
        cs = event["data"]["object"]
        if cs["payment_status"] == "paid":
            email = (cs.get("customer_details") or {}).get("email", "")
            db = get_db()
            db.execute("UPDATE purchases SET status='paid', email=? WHERE stripe_session_id=?",
                       (email, cs["id"]))
            db.commit()
            db.close()
    return jsonify({"ok": True})


# ── Terms & policy ───────────────────────────────────────────────────────────
@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/payment-terms")
def payment_terms():
    return render_template("payment_terms.html")


# ── Email — skicka läsning ────────────────────────────────────────────────────
@app.route("/api/send-reading", methods=["POST"])
@login_required
def send_reading():
    data        = request.get_json()
    to_email    = data.get("email", "").strip()
    spread_type = data.get("spread_type", "")
    cards       = data.get("cards", [])
    reading_text = data.get("reading_text", "")
    followups   = data.get("followups", [])

    if not to_email or "@" not in to_email:
        return jsonify({"error": "Ogiltig e-postadress"}), 400

    spread_names = {"single": "En Fråga", "triple": "Tre Frågor", "year": "Årsstjärnan"}
    spread_label = spread_names.get(spread_type, "Tarotläsning")

    cards_html = ""
    for c in cards:
        rev = " <em>(omvänd)</em>" if c.get("reversed") else ""
        pos = f"<span style='color:#9b30ff;font-size:0.8em;'>{c.get('position','')}</span><br>" if c.get("position") else ""
        cards_html += f"<div style='text-align:center;margin:0 8px;'>{pos}<strong style='color:#f0e6ff;'>{c.get('name_sv','')}</strong>{rev}</div>"

    followups_html = ""
    for fq in followups:
        followups_html += f"""
        <div style='margin-bottom:16px;'>
            <div style='color:#c8b4ff;font-weight:bold;margin-bottom:4px;'>Fråga: {fq.get('q','')}</div>
            <div style='color:#e8d8ff;'>{fq.get('a','')}</div>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset='utf-8'></head>
    <body style='background:#07000f;color:#ede0ff;font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:32px 24px;'>
      <div style='text-align:center;margin-bottom:32px;'>
        <h1 style='font-family:serif;color:#ffffff;letter-spacing:0.1em;margin-bottom:4px;'>✦ JJ Universe ✦</h1>
        <p style='color:#9980bb;font-size:0.9em;'>Din {spread_label}</p>
      </div>

      <div style='display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin-bottom:32px;'>
        {cards_html}
      </div>

      <div style='border-top:1px solid rgba(155,48,255,0.3);padding-top:24px;margin-bottom:24px;'>
        <h2 style='color:#c8a8ff;font-size:1em;letter-spacing:0.08em;margin-bottom:16px;'>DIN TOLKNING</h2>
        <div style='line-height:1.8;color:#ede0ff;white-space:pre-line;'>{reading_text}</div>
      </div>

      {"<div style='border-top:1px solid rgba(155,48,255,0.3);padding-top:24px;margin-bottom:24px;'><h2 style='color:#c8a8ff;font-size:1em;letter-spacing:0.08em;margin-bottom:16px;'>FÖLJDFRÅGOR</h2>" + followups_html + "</div>" if followups_html else ""}

      <div style='border-top:1px solid rgba(155,48,255,0.3);padding-top:16px;text-align:center;'>
        <p style='color:#6650a0;font-size:0.75em;'>Denna läsning är enbart för underhållning och personlig reflektion.<br>
        JJ Universe erbjuder inte medicinsk, psykologisk eller juridisk rådgivning.<br>
        © {datetime.now().year} JJ Universe — <a href='https://jjuniverse.se' style='color:#9b30ff;'>jjuniverse.se</a></p>
      </div>
    </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from": "JJ Universe <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"✦ Din {spread_label} från JJ Universe",
            "html": html
        })
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.error(f"Resend error: {e}")
        return jsonify({"error": str(e)}), 500


# ── Admin-panel ───────────────────────────────────────────────────────────────
@app.route("/star", methods=["GET"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_overview"))
    return render_template("admin_login.html")


@app.route("/star", methods=["POST"])
def admin_login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        session["consent_given"] = True
        session.permanent = False
        return redirect(url_for("admin_overview"))
    else:
        log_security_event("admin_failed_login", ip, f"username={username}")
        # Kolla brute force och skicka varningsmail om nödvändigt
        try:
            db = get_db()
            cnt = db.execute("""
                SELECT COUNT(*) FROM security_events
                WHERE type='admin_failed_login' AND ip=?
                AND created >= datetime('now', '-10 minutes')
            """, (ip,)).fetchone()[0]
            db.close()
            if cnt >= 5:
                send_security_alert_email("Brute force admin", f"{cnt} misslyckade inlogg från {ip}")
        except Exception:
            pass
        return render_template("admin_login.html", error="Fel uppgifter")


@app.route("/star/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/star/overview")
@admin_required
def admin_overview():
    db = get_db()
    total_users    = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_readings = db.execute("SELECT COUNT(*) FROM readings_log").fetchone()[0]
    today_visits   = db.execute("SELECT COUNT(*) FROM visits WHERE date(created) = date('now')").fetchone()[0]
    week_visits    = db.execute("SELECT COUNT(*) FROM visits WHERE created >= datetime('now', '-7 days')").fetchone()[0]
    readings_by_type = db.execute(
        "SELECT spread_type, COUNT(*) as cnt FROM readings_log GROUP BY spread_type"
    ).fetchall()
    recent_users = db.execute(
        "SELECT username, created FROM users ORDER BY created DESC LIMIT 10"
    ).fetchall()
    alerts = get_security_alerts(db)
    db.close()
    return render_template("admin_panel.html",
        tab="overview",
        total_users=total_users,
        total_readings=total_readings,
        today_visits=today_visits,
        week_visits=week_visits,
        readings_by_type=readings_by_type,
        recent_users=recent_users,
        alerts=alerts
    )


@app.route("/star/stats")
@admin_required
def admin_stats():
    db = get_db()
    daily_visits = db.execute("""
        SELECT date(created) as day, COUNT(*) as cnt
        FROM visits GROUP BY date(created)
        ORDER BY day DESC LIMIT 30
    """).fetchall()
    daily_readings = db.execute("""
        SELECT date(created) as day, COUNT(*) as cnt
        FROM readings_log GROUP BY date(created)
        ORDER BY day DESC LIMIT 30
    """).fetchall()
    top_paths = db.execute("""
        SELECT path, COUNT(*) as cnt FROM visits
        GROUP BY path ORDER BY cnt DESC LIMIT 15
    """).fetchall()
    alerts = get_security_alerts(db)
    db.close()
    return render_template("admin_panel.html",
        tab="stats",
        daily_visits=daily_visits,
        daily_readings=daily_readings,
        top_paths=top_paths,
        alerts=alerts
    )


@app.route("/star/security")
@admin_required
def admin_security():
    db = get_db()
    events = db.execute(
        "SELECT * FROM security_events ORDER BY created DESC LIMIT 100"
    ).fetchall()
    failed_logins = db.execute("""
        SELECT ip, COUNT(*) as cnt FROM security_events
        WHERE type = 'failed_login'
        GROUP BY ip ORDER BY cnt DESC LIMIT 20
    """).fetchall()
    alerts = get_security_alerts(db)
    db.close()
    return render_template("admin_panel.html",
        tab="security",
        events=events,
        failed_logins=failed_logins,
        alerts=alerts
    )


@app.route("/star/consent")
@admin_required
def admin_consent():
    db = get_db()
    consents = db.execute(
        "SELECT * FROM consent_log ORDER BY created DESC"
    ).fetchall()
    db.close()
    return render_template("admin_panel.html", tab="consent", consents=consents, alerts=[])


@app.route("/star/cleanup", methods=["POST"])
@admin_required
def admin_cleanup():
    day = request.form.get("day", "")
    try:
        db = get_db()
        if day:
            db.execute("DELETE FROM security_events WHERE date(created) = ?", (day,))
            db.execute("DELETE FROM visits WHERE date(created) = ?", (day,))
        else:
            db.execute("DELETE FROM security_events WHERE created < datetime('now', '-7 days')")
            db.execute("DELETE FROM visits WHERE created < datetime('now', '-7 days')")
        db.commit()
        db.close()
    except Exception as e:
        app.logger.error(f"Manual cleanup error: {e}")
    return redirect(url_for("admin_security"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
