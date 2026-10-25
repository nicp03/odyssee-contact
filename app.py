
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 Ko maximum

@app.get("/")
def accueil():
    return jsonify({
        "service": "ODYSSÉE — Contact",
        "statut": "actif"
    })

@app.post("/contact")
def contact():
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

    if not email or len(email) > 254 or "@" not in email:
        return jsonify({"erreur": "Adresse e-mail invalide."}), 400

    if not message or len(message) > 5000:
        return jsonify({"erreur": "Message invalide."}), 400

    # Aucun e-mail n'est envoyé à ce stade.
    return jsonify({
        "statut": "reçu",
        "message": "Le formulaire est en préparation."
    }), 202

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
