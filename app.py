import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 Ko maximum

DESTINATAIRE = "contact.odyssee.projet@gmail.com"
ORIGINE_AUTORISEE = "https://nicp03.github.io"


@app.after_request
def ajouter_entetes(response):
    origine = request.headers.get("Origin")

    if origine == ORIGINE_AUTORISEE:
        response.headers["Access-Control-Allow-Origin"] = origine
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"

    return response


@app.get("/")
def accueil():
    return jsonify({
        "service": "ODYSSÉE — Contact",
        "statut": "actif"
    })


@app.route("/contact", methods=["POST", "OPTIONS"])
def contact():
    if request.method == "OPTIONS":
        return "", 204

    donnees = request.get_json(silent=True)

    if not isinstance(donnees, dict):
        return jsonify({"erreur": "Données JSON attendues."}), 400

    nom = donnees.get("nom", "")
    email = donnees.get("email", "")
    message = donnees.get("message", "")

    if not all(isinstance(v, str) for v in (nom, email, message)):
        return jsonify({"erreur": "Format des champs invalide."}), 400

    nom, email, message = nom.strip(), email.strip(), message.strip()

    if not nom or len(nom) > 100:
        return jsonify({"erreur": "Nom invalide."}), 400

    if (
        not email
        or len(email) > 254
        or "@" not in email
        or any(c in email for c in "\r\n")
    ):
        return jsonify({"erreur": "Adresse e-mail invalide."}), 400

    if not message or len(message) > 5000:
        return jsonify({"erreur": "Message invalide."}), 400

    cle_api = os.environ.get("RESEND_API_KEY")
    if not cle_api:
        return jsonify({
            "erreur": "Le service d'envoi n'est pas configuré."
        }), 503

    contenu = {
        "from": "ODYSSÉE <onboarding@resend.dev>",
        "to": [DESTINATAIRE],
        "reply_to": email,
        "subject": f"Nouveau message ODYSSÉE — {nom}",
        "text": (
            f"Nouveau message reçu depuis le site ODYSSÉE.\n\n"
            f"Nom : {nom}\n"
            f"Adresse e-mail : {email}\n\n"
            f"Message :\n{message}\n"
        ),
    }

    requete = Request(
        "https://api.resend.com/emails",
        data=json.dumps(contenu).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {cle_api}",
            "Content-Type": "application/json",
            "User-Agent": "ODYSSEE-Contact/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(requete, timeout=15) as reponse:
            if not 200 <= reponse.status < 300:
                return jsonify({
                    "erreur": "L'envoi du message a échoué."
                }), 502

    except HTTPError as erreur:
        # Diagnostic interne : ne jamais journaliser la clé API.
        details = erreur.read().decode("utf-8", errors="replace")
        app.logger.error(
            "Refus Resend — code HTTP %s — réponse : %s",
            erreur.code,
            details[:2000],
        )
        return jsonify({
            "erreur": "L'envoi du message a échoué."
        }), 502

    except (URLError, TimeoutError):
        app.logger.error("Le service Resend est temporairement inaccessible.")
        return jsonify({
            "erreur": "Le service d'envoi est temporairement indisponible."
        }), 503

    return jsonify({
        "statut": "envoyé",
        "message": "Votre message a été transmis."
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
