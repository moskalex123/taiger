import json
import os

class I18n:
    _cache = {}

    @classmethod
    def clear_cache(cls):
        cls._cache = {}

    @classmethod
    def get(cls, lang_code: str, key: str, **kwargs) -> str:
        lang = lang_code if lang_code in ['ru', 'en'] else 'en'
        if lang not in cls._cache:
            path = f"/opt/taiger/locales/{lang}.json"
            with open(path, 'r', encoding='utf-8') as f:
                cls._cache[lang] = json.load(f)

        keys = key.split('.')
        val = cls._cache[lang]
        for k in keys:
            val = val.get(k, key)
            if val == key: break

        if isinstance(val, str):
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"I18n debug: key='{key}', lang='{lang}', val={repr(val)}, kwargs={kwargs}")
            try:
                result = val.format(**kwargs)
                logger.info(f"I18n debug: format successful, result={repr(result)}")
                return result
            except (KeyError, ValueError) as e:
                # Log the error and return the raw string to prevent crashes
                logger.error(f"I18n format error for key '{key}' in lang '{lang}': {e}. Raw value: {val}")
                return val
        else:
            return val