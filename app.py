import os
import json
import secrets
from flask import (Flask, render_template, request, jsonify,
                   Response, stream_with_context,
                   redirect, url_for, flash, session)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import anthropic
from cards import TAROT_CARDS
from database import init_db, get_db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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


# ── Prompt-byggare ───────────────────────────────────────────────────────────
def build_single_prompt(question, cards):
    c = cards
    return f"""Frågan som söks svar på: "{question}"

De tre korten som dragits:
1. GRUNDEN — {c[0]['name_sv']} ({c[0]['name']}){' [OMVÄND]' if c[0]['reversed'] else ''}
2. KÄRNAN — {c[1]['name_sv']} ({c[1]['name']}){' [OMVÄND]' if c[1]['reversed'] else ''}
3. VÄGEN FRAMÅT — {c[2]['name_sv']} ({c[2]['name']}){' [OMVÄND]' if c[2]['reversed'] else ''}

Ge en sammanhängande, personlig och varm tolkning av dessa tre kort i relation till frågan. Se korten som ett helhetligt budskap — vad de tillsammans säger om situationen och vad som öppnar sig. Avsluta med ett konkret råd på en egen rad som börjar med: ✦ Råd:"""


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
    return prompt


# ── Auth routes ──────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login_page():
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
@app.route("/")
@login_required
def index():
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
