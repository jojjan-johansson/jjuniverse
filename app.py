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
from cards import TAROT_CARDS
from database import (init_db, get_db, can_draw_free_card, record_free_card_draw,
                      log_visit, log_security_event, log_reading, log_consent)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
resend.api_key = os.environ.get("RESEND_API_KEY", "")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Initiera databasen vid start
init_db()

# ── Hjälpfunktion: inloggningskrav ──────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
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
        return redirect(url_for('index'))

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
            return redirect(url_for("index"))
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
    if not session.get("consent_given"):
        return redirect(url_for("welcome"))
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    return render_template("index.html", username=session.get("username"))


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
                max_tokens=1000,
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
            "from": "JJ Universe <no-reply@jjuniverse.se>",
            "to": [to_email],
            "subject": f"✦ Din {spread_label} från JJ Universe",
            "html": html
        })
        return jsonify({"ok": True})
    except Exception as e:
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
        session.permanent = False
        return redirect(url_for("admin_overview"))
    else:
        log_security_event("admin_failed_login", ip, f"username={username}")
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
    db.close()
    return render_template("admin_panel.html",
        tab="overview",
        total_users=total_users,
        total_readings=total_readings,
        today_visits=today_visits,
        week_visits=week_visits,
        readings_by_type=readings_by_type,
        recent_users=recent_users
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
    db.close()
    return render_template("admin_panel.html",
        tab="stats",
        daily_visits=daily_visits,
        daily_readings=daily_readings,
        top_paths=top_paths
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
    db.close()
    return render_template("admin_panel.html",
        tab="security",
        events=events,
        failed_logins=failed_logins
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
