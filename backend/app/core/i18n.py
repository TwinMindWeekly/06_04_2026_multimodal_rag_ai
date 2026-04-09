import json
import os
from fastapi import Request

# Load language packs
def load_translations():
    # Construct absolute paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    locales_dir = os.path.join(base_dir, "locales")
    
    translations = {}
    if os.path.exists(locales_dir):
        for lang in ["en", "vi"]:
            file_path = os.path.join(locales_dir, f"{lang}.json")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    translations[lang] = json.load(f)
    return translations

TRANSLATIONS = load_translations()

def get_language(request: Request) -> str:
    """
    Dependency to extract 'Accept-Language' header.
    Defaults to 'en' if not found or unsupported.
    """
    accept_language = request.headers.get("accept-language", "en")
    
    # Parse standard Accept-Language values like 'vi-VN,vi;q=0.9,en-US...'
    primary_lang = accept_language.split(",")[0].split("-")[0].lower()
    
    if primary_lang in ["vi", "en"]:
        return primary_lang
    return "en"

def t(key: str, lang: str = "en") -> str:
    """
    Translate a given key (e.g. 'errors.folder_not_found') for the specified language.
    """
    keys = key.split('.')
    current = TRANSLATIONS.get(lang, {})
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, key)
        else:
            return key
            
    # Fallback to English if key missing in target lang
    if current == key and lang != "en":
        return t(key, "en")
        
    return current if isinstance(current, str) else key
