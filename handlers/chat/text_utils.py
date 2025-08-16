import re

def extract_marked_words(text):
    """
    Извлекает слова, обёрнутые в тильды: ~слово~
    """
    return re.findall(r'\~([^|]{2,40})~', text)

def is_russian(word):
    """
    Проверяет, состоит ли слово из русских символов
    """
    return bool(re.match(r'^[А-Яа-яЁё\s\-]+$', word.strip()))
