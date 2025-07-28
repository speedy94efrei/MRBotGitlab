
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

    if data.get("object_kind") == "note":
        note_type = data.get("object_attributes", {}).get("noteable_type")
        note_text = data.get("object_attributes", {}).get("note")
        author = data.get("user", {}).get("username", "Utilisateur inconnu")
        mr_title = data.get("merge_request", {}).get("title", "Titre inconnu")
        mr_url = data.get("merge_request", {}).get("url", "#")

        if note_type == "MergeRequest":
            message = {
                "text": f"💬 **Nouveau commentaire sur la MR {mr_title}**\n"
                        f"\n✏️ Auteur : **{author}**\n"
                        f"\n📝 Message :\n> {note_text}\n"
                        f"\n 🔗 [Voir la MR]({mr_url})"
            }

            # Pour l'instant, envoie au canal par défaut
            webhook_url = get_webhook_url("Lions")  # ou autre logique selon l’auteur
            response = requests.post(webhook_url, json=message)

            if response.status_code == 200:
                return jsonify({"message": "Notification commentaire envoyée ✅"}), 200
            else:
                return jsonify({"error": f"Erreur Teams commentaire : {response.text}"}), 500

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

        # Ajouter le @ devant chaque nom pour mentionner dans Teams
        mention_author = f"@{author_name}" if author_name != "Auteur inconnu" else author_name
        mention_reviewers = [f"@{name}" for name in reviewer_names]

        # Texte affiché dans la notification
        reviewer_list = "\n".join([f"- {name}" for name in mention_reviewers]) if mention_reviewers else "Aucun reviewer"

                # Déterminer le bon message selon l'action
        if state == "merged":
            merge_actor = reviewers[0].get("name") if reviewers else action_user
            action_description = f"✅ La branche a été mergée par **{merge_actor}**"
            reviewer_block = ""  # Ne pas afficher les reviewers dans ce cas
        elif state == "opened":
            action_description = f"✏️ Merge Request créée par **{mention_author}**"
            reviewer_block = f"\n**Reviewers** :\n{reviewer_list}"
        elif state == "closed":
            action_description = f"❌ Merge Request fermée par **{action_user}**"
            reviewer_block = f"\n**Reviewers** :\n{reviewer_list}"
        else:
            action_description = f"🔄 Action sur la MR par **{action_user}**"
            reviewer_block = f"\n**Reviewers** :\n{reviewer_list}"


        message = {
            "text": f"\ud83d\udd34 Nouvelle Merge Request sur **{project_name}**"
                    f"\n : {title}\n"
                    f"\n{action_description}\n\n"              
                    f"\n{reviewer_block}\n"
                    f"\n[\ud83d\udcc8 Voir la MR]({url})"
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
