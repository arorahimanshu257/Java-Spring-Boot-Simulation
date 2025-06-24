import urllib.parse 
import re

def needs_encoding(text):
    return bool(text and re.search(r"[@:$#%&]", text))

def encode_db_uri(db_uri):
    if not db_uri:
        return db_uri

    try:
        db_uri = db_uri.replace("#", "%23")
        parsed = urllib.parse.urlparse(db_uri)

        if parsed.username or parsed.password:
            username = parsed.username if not needs_encoding(parsed.username) else urllib.parse.quote_plus(parsed.username)
            password = parsed.password if not needs_encoding(parsed.password) else urllib.parse.quote_plus(parsed.password)

            netloc = f"{username or ''}{f':{password}' if password else ''}@{parsed.hostname or ''}{f':{parsed.port}' if parsed.port else ''}"
            
            return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

        return db_uri

    except Exception as e:
        print(f"Encoding Error: {e}")
        return db_uri
