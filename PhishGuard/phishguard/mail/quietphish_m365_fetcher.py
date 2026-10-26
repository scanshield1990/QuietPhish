import requests

from phishguard.mail.m365_auth import M365Auth


class M365MailFetcher:
    GRAPH_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, tenant_id, client_id):
        self.auth = M365Auth(tenant_id, client_id)

    def fetch_unseen(self, limit=10):
        token = self.auth.get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        response = requests.get(
            f"{self.GRAPH_URL}/me/mailFolders/inbox/messages",
            headers=headers,
            params={
                "$filter": "isRead eq false",
                "$top": max(1, min(int(limit), 100)),
                "$select": "id,subject,receivedDateTime,isRead",
                "$orderby": "receivedDateTime desc",
            },
            timeout=30,
        )

        response.raise_for_status()

        messages = response.json().get("value", [])
        results = []

        for message in messages:
            message_id = message["id"]

            # Download the original email in MIME (.eml) format.
            mime_response = requests.get(
                f"{self.GRAPH_URL}/me/messages/{message_id}/$value",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "message/rfc822",
                },
                timeout=30,
            )

            mime_response.raise_for_status()

            # Return the Graph message ID and original email bytes.
            results.append((message_id, mime_response.content))

        return results