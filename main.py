from flask import Flask, request, jsonify
import requests
import os
import re
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()  # Charge les variables d'environnement

# === Membres des équipes ===
Lions = {
    "Rayan BOUSSAD", "Sullivan Allamelou", "Steven NICHOLLS", "Aymen LTIFI", "Moustapha CHANFIOU"
}
Titans = {
    "Aymen BOUSHABI", "Youssef EL ABDI", "Walid AIT-DAOUD", "Jawâd BOUGHALEM", "Andy KADIAMBU"
}
Chevaliers = {
    "Florian PILVEN", "Nassim ALI", "Mousstoifa ABOUDOU", "Nicolas DE-ALMEIDA"
}
Gardiens = {
    "Faïz ALI", "Massil AMIRAT", "Kristina HANSSON-MBOW", "Sara BEN-GHARSALLAH"
}

# === Résolution du bon webhook Teams ===
def get_webhook_url(canalCible: str) -> str:
    return os.getenv(f"TEAMS_WEBHOOK_{canalCible}", "")

# === Détecte à quelle équipe appartient une personne ===
def detect_team(user_name: str):
    all_teams = {
        "Lions": Lions,
        "Titans": Titans,
        "Chevaliers": Chevaliers,
        "Gardiens": Gardiens
    }
    for team, members in all_teams.items():
        for member in members:
            if member.lower().strip() == user_name.lower().strip():
                return team
    return None

# === Route principale ===
@app.route("/gitlab-webhook", methods=["POST"])
def gitlab_webhook():
    data = request.json

    # === Gestion des commentaires sur MR ===
    if data.get("object_kind") == "note":
        note_type = data.get("object_attributes", {}).get("noteable_type")
        note_text = data.get("object_attributes", {}).get("note")
        author = data.get("user", {}).get("username", "Utilisateur inconnu")
        mr_title = data.get("merge_request", {}).get("title", "Titre inconnu")
        mr_url = data.get("merge_request", {}).get("url", "#")
        assignees = data.get("merge_request", {}).get("assignees", [])
        assigned_name = assignees[0].get("name", "Aucun") if assignees else "Aucun"

        # 🔍 Extraction des images dans le commentaire
        image_urls = re.findall(r'!\[.*?\]\((http.*?)\)', note_text)
        image_block = ""
        if image_urls:
            image_block = "\n📷 **Images jointes :**\n" + "\n".join(image_urls)

        message = {
            "text": f"💬 **Nouveau commentaire sur la MR _{mr_title}_**\n"
                    f"✏️ Auteur : **{author}**\n"
                    f"👤 Destinataire : **{assigned_name}**\n"
                    f"📝 Message :\n> {note_text}\n"
                    f"{image_block}\n"
                    f"🔗 [Voir la MR]({mr_url})"
        }

        # Envoi uniquement dans le canal de l'assigné principal
        assigned_team = detect_team(assigned_name)
        if assigned_team:
            webhook_url = get_webhook_url(assigned_team)
            if webhook_url:
                requests.post(webhook_url, json=message)

        return jsonify({"message": "Notification commentaire envoyée ✅"}), 200

    # === Gestion des Merge Requests ===
    if data.get("object_kind") == "merge_request":
        action = data.get("object_attributes", {}).get("action", "")
        project_name = data.get("project", {}).get("name", "Projet inconnu")
        title = data.get("object_attributes", {}).get("title", "Titre inconnu")
        url = data.get("object_attributes", {}).get("url", "#")
        author_id = data.get("object_attributes", {}).get("author_id", None)
        description = data.get("object_attributes", {}).get("description", "")
        assignees = data.get("assignees", [])
        reviewers = data.get("reviewers", [])
        action_user = data.get("user", {}).get("username", "Utilisateur inconnu")

        author_name = next((a.get("name") for a in assignees if a.get("id") == author_id), "Auteur inconnu")
        reviewer_names = [r.get('name', '') for r in reviewers]
        reviewer_list = "\n".join([f"- {r}" for r in reviewer_names]) if reviewer_names else "Aucun reviewer"

        mentioned_usernames = [word[1:] for word in description.split() if word.startswith("@")]
        mention_block = ""
        if mentioned_usernames:
            mention_block = "\n**Approuveurs désignés :**\n" + "\n".join([f"- @{u}" for u in mentioned_usernames])

        if action == "open":
            message_text = (
                f"✏️ Nouvelle Merge Request dans **{project_name}**\n"
                f"📄 Titre : _{title}_\n"
                f"👤 Auteur : **{author_name}**\n"
                f"👀 Reviewers :\n{reviewer_list}"
                f"{mention_block}\n"
                f"🔗 [Voir la MR]({url})"
            )
        elif action == "reopen":
            message_text = (
                f"🔁 Merge Request _{title}_ **rouverte** dans **{project_name}** par **{action_user}**\n"
                f"🔗 [Voir la MR]({url})"
            )
        elif action == "close":
            message_text = (
                f"❌ Merge Request _{title}_ **fermée** par **{action_user}**\n"
                f"🔗 [Voir la MR]({url})"
            )
        elif action == "update":
            message_text = (
                f"🔄 Merge Request _{title}_ **mise à jour** par **{action_user}**\n"
                f"🔗 [Voir la MR]({url})"
            )
        elif action == "merge":
            merge_actor = reviewers[0].get("name") if reviewers else action_user
            message_text = (
                f"✅ Merge Request _{title}_ **mergée** dans **{project_name}** par **{merge_actor}**\n"
                f"🔗 [Voir la MR]({url})"
            )
        elif action == "approved":
            message_text = (
                f"👍 **{action_user}** a **approuvé** la Merge Request _{title}_ dans **{project_name}**\n"
                f"🔗 [Voir la MR]({url})"
            )
        else:
            message_text = (
                f"📌 Action `{action}` détectée sur la MR _{title}_ par **{action_user}**\n"
                f"🔗 [Voir la MR]({url})"
            )

        message = {"text": message_text}

        # === Notification à l'équipe de l'auteur uniquement (plus de fallback "Lions") ===
        teams_to_notify = set()
        author_team = detect_team(author_name)
        if author_team:
            teams_to_notify.add(author_team)

        for team in teams_to_notify:
            webhook_url = get_webhook_url(team)
            if webhook_url:
                requests.post(webhook_url, json=message)

        return jsonify({"message": "Notification MR envoyée ✅"}), 200

    return jsonify({"message": "Événement ignoré (pas une MR/note)"}), 200

# === Lancement serveur ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
