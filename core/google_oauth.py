import json
from pathlib import Path


def load_google_client_secret(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    config = data.get("web") or data.get("installed") or data
    required = [
        "client_id",
        "project_id",
        "auth_uri",
        "token_uri",
        "auth_provider_x509_cert_url",
        "client_secret",
        "redirect_uris",
    ]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Missing Google OAuth field(s): {', '.join(missing)}")
    placeholder_fields = [
        key for key in ("client_id", "project_id", "client_secret")
        if str(config[key]).startswith("PASTE_")
    ]
    if placeholder_fields:
        raise ValueError(
            "Replace placeholder value(s) before importing: "
            + ", ".join(placeholder_fields)
        )
    return config
