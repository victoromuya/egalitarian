from whitenoise.storage import CompressedManifestStaticFilesStorage


class TolerantManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Fall back to the unhashed URL for files missing from the manifest
    (e.g. images/logo.png, which templates reference with an onerror fallback
    until the client supplies the real asset) instead of raising a 500 on
    every page render in production.
    """

    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            # File doesn't exist on disk either — serve the plain URL and let
            # the browser 404 it (handled by the template's onerror).
            return name
