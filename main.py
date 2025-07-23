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
        state = data.get("object_attributes", {}).get("state", "")
        url = data.get("object_attributes", {}).get("url", "")
        action_user = data.get("user", {}).get("username", "Utilisateur inconnu")
        reviewers = data.get("reviewers", [])
        assignees = data.get("assignees", [])
        author_id = data.get("object_attributes", {}).get("author_id", None)

        author_name = next((a.get("name") for a in assignees if a.get("id") == author_id), "Auteur inconnu")
        reviewer_names = [r.get('name', '') for r in reviewers]
        reviewer_list = "\n".join([f"- {name}" for name in reviewer_names]) if reviewer_names else "Aucun reviewer"

        if state == "merged":
            merge_actor = reviewers[0].get("name") if reviewers else action_user
            action_description = f"✅ La branche a été mergée par **{merge_actor}**"
        elif state == "opened":
            action_description = f"✏️ Merge Request créée par **{author_name }**"
        elif state == "closed":
            action_description = f"❌ Merge Request fermée par **{merge_actor}**"
        else:
            action_description = f"🔄 Action sur la MR par **{action_user}**"

        message = {
            "text": f"\ud83d\udd34 Nouvelle Merge Request sur **{project_name}**"
                    f"\n : {title}\n"
                    f"{action_description}\n\n"              
                    f"\n**Reviewers** :\n{reviewer_list}\n"
                    f"\n[\ud83d\udcc8 Voir la MR]({url})"
                    f"\n{data}"
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