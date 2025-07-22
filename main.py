from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv() # charge variables d'environnement

Lions = {
    "Rayan", "Sullivan", "Steven", "Aymen", "Moustapha"
}
Titans = {
    "Aymen", "Youssef", "Walid", "Jawad", "Andy"
}
Chevaliers = {
    "Florian", "Nassim", "Moustoifa", "Nicolas"
}
Gardiens = {
    "Faïz", "Massil", "Kristina", "Sara"
}

# === Fonction de résolution du webhook cible ===
def get_webhook_url(canalCible: int) -> str:
    if canalCible == "Lions":
        return os.getenv("TEAMS_WEBHOOK_Lions")
    elif canalCible == "Titans":
        return os.getenv("TEAMS_WEBHOOK_Titans")
    elif canalCible == "Chevaliers":
        return os.getenv("TEAMS_WEBHOOK_Chevaliers")
    elif canalCible == "Gardiens":
        return os.getenv("TEAMS_WEBHOOK_Gardiens")
    else:
        return 0

# === Route de réception GitLab ===
@app.route("/gitlab-webhook", methods=["POST"])
def gitlab_webhook():
    data = request.json

    if data.get("object_kind") == "merge_request":
        project_name = data.get("project", {}).get("name", "Projet inconnu")
        title = data.get("object_attributes", {}).get("title", "Titre inconnu")
        author = data.get("user", {}).get("username", "Auteur inconnu")
        url = data.get("object_attributes", {}).get("url", "")
        reviewers = data.get("reviewers", [])

        reviewer_list = "\n".join([f"- {r.get('name')}" for r in reviewers]) if reviewers else "Aucun reviewer"

        message = {
            "text": f"\ud83d\udd34 Nouvelle Merge Request sur **{project_name}**"
                    f"\n : {title}\n"
                    f"\n**Auteur** : {author}\n"
                    f"\n**Reviewers** :\n{reviewer_list}\n"
                    f"\n[\ud83d\udcc8 Voir la MR]({url})"
                    f"{data}"
        }

        canalCible = "Lions"

        webhook_url = get_webhook_url(canalCible)
        response = requests.post(webhook_url, json=message) 

        if response.status_code == 200:
            return jsonify({"message": "Notification envoyée à Teams ✅"}), 200
        else:
            return jsonify({"error": f"Erreur lors de l'envoi à Teams: {response.text}"}), 500

    return jsonify({"message": "Evénement ignoré (pas une MR)"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
