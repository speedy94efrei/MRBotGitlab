from flask import Flask, request, jsonify
import requests
import os
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

    # === 🔔 COMMENTAIRE SUR MR ===
    if data.get("object_kind") == "note":
        note_type = data.get("object_attributes", {}).get("noteable_type")
        note_text = data.get("object_attributes", {}).get("note")
        author = data.get("user", {}).get("username", "Utilisateur inconnu")
        mr_title = data.get("merge_request", {}).get("title", "Titre inconnu")
        mr_url = data.get("merge_request", {}).get("url", "#")

        if note_type == "MergeRequest":
            message = {
                "text": f"💬 **Nouveau commentaire sur la MR _{mr_title}_**\n"
                        f"✏️ Auteur : **{author}**\n"
                        f"📝 Message :\n> {note_text}\n"
                        f"🔗 [Voir la MR]({mr_url})"
            }

            # Pour l’instant, notification aux Lions par défaut
            webhook_url = get_webhook_url("Lions")
            requests.post(webhook_url, json=message)

            return jsonify({"message": "Notification commentaire envoyée ✅"}), 200

    # === ✅ EVENEMENT DE MERGE REQUEST ===
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

        # Mentions (pour Teams, décoratifs sauf si mentions activées)
        mention_author = f"@{author_name}" if author_name != "Auteur inconnu" else author_name
        mention_reviewers = [f"@{name}" for name in reviewer_names]
        reviewer_list = "\n".join([f"- {name}" for name in mention_reviewers]) if mention_reviewers else "Aucun reviewer"

        # === Description de l’action ===
        if state == "merged":
            merge_actor = reviewers[0].get("name") if reviewers else action_user
            action_description = f"✅ La branche a été mergée par **{merge_actor}**"
            reviewer_block = ""
        elif state == "opened":
            action_description = f"✏️ Merge Request créée par **{mention_author}**"
            reviewer_block = f"\n**Reviewers** :\n{reviewer_list}"
        elif state == "closed":
            action_description = f"❌ Merge Request fermée par **{action_user}**"
            reviewer_block = f"\n**Reviewers** :\n{reviewer_list}"
        else:
            action_description = f"🔄 Action sur la MR par **{action_user}**"
            reviewer_block = f"\n**Reviewers** :\n{reviewer_list}"

        # === Message final ===
        message = {
            "text": f"🔵 Nouvelle Merge Request sur **{project_name}**\n"
                    f"📄 : {title}\n\n"
                    f"{action_description}\n"
                    f"{reviewer_block}\n\n"
                    f"🔗 [Voir la MR]({url})"
        }

        # === Détection des équipes à notifier ===
        author_team = detect_team(author_name)
        reviewer_teams = set(detect_team(name) for name in reviewer_names if detect_team(name))
        teams_to_notify = set()
        if author_team:
            teams_to_notify.add(author_team)
        teams_to_notify.update(reviewer_teams)

        # === Envoi du message dans chaque canal concerné
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
