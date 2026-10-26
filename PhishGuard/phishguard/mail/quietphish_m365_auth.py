
from pathlib import Path
import os
import msal
import win32crypt  # Windows DPAPI; requires pywin32


SCOPES = ["Mail.Read", "User.Read"]


class M365Auth:
    def __init__(self, tenant_id, client_id):
        self.tenant_id = tenant_id
        self.client_id = client_id

        self.authority = (
            f"https://login.microsoftonline.com/{tenant_id}"
        )

        # Keep tokens outside the Git repository and separate from the live installation.
        cache_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SSSH" / "QuietPhish"
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_path = cache_dir / "m365_token_cache.bin"  # Never commit this file.

        self.cache = msal.SerializableTokenCache()

        if self.cache_path.exists():
            encrypted = self.cache_path.read_bytes()
            decrypted = win32crypt.CryptUnprotectData(
                encrypted, None, None, None, 0
            )[1]
            self.cache.deserialize(decrypted.decode("utf-8"))

        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self.cache,
        )

    def save_cache(self):
        if self.cache.has_state_changed:
            data = self.cache.serialize().encode("utf-8")
            encrypted = win32crypt.CryptProtectData(
                data, None, None, None, None, 0
            )
            self.cache_path.write_bytes(encrypted)

    def get_token(self):
        accounts = self.app.get_accounts()

        if accounts:
            result = self.app.acquire_token_silent(
                SCOPES, account=accounts[0]
            )

            if result and "access_token" in result:
                self.save_cache()
                return result["access_token"]

        result = self.app.acquire_token_interactive(
            scopes=SCOPES,
            port=0,
        )

        if "access_token" not in result:
            raise RuntimeError(
                result.get("error_description", "Microsoft authentication failed")
            )

        self.save_cache()
        return result["access_token"]