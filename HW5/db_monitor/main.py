import functions_framework
import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT = "enduring-trees-508117-p7"
INSTANCE = "cs528-hw5-mysql"

@functions_framework.http
def stop_idle_sql(request):
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)

    url = (
        f"https://sqladmin.googleapis.com/v1/"
        f"projects/{PROJECT}/instances/{INSTANCE}"
    )

    response = session.get(url, timeout=30)
    response.raise_for_status()
    instance = response.json()

    if instance.get("settings", {}).get("activationPolicy") == "NEVER":
        return "Cloud SQL already stopped", 200

    response = session.patch(
        url,
        json={"settings": {"activationPolicy": "NEVER"}},
        timeout=30,
    )
    response.raise_for_status()
    return "Cloud SQL stop requested", 200
