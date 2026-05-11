"""Test web scraping para cada FUENTE del asistente."""
import requests
from bs4 import BeautifulSoup

URLS = {
    'SENAMHI': 'https://senamhi.gob.bo/index.php/alertas',
    'ABC': 'https://www.abc.gob.bo/',
    'Unitel': 'https://unitel.bo/',
    'El Deber': 'https://eldeber.com.bo/',
    'Erbol': 'https://www.erbol.com.bo/',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

ok_count = 0
for nombre, url in URLS.items():
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script','style','nav','footer','header','meta','link','noscript','iframe','button','form']):
            tag.decompose()
        elementos = soup.find_all(['p','h1','h2','h3','article','li','span','div','td'])
        texto = ' '.join(e.get_text(separator=' ', strip=True) for e in elementos)
        texto = ' '.join(texto.split())
        umbral = 60 if 'SENAMHI' in nombre.upper() else 150
        good = len(texto) >= umbral
        if good:
            ok_count += 1
        status = 'OK' if good else 'FALLA'
        print(f'[{nombre}] HTTP={r.status_code} chars={len(texto)} umbral={umbral} -> {status}')
        if good:
            preview = texto[:250].encode('ascii','replace').decode('ascii')
            print(f'  preview: {preview}')
    except Exception as e:
        print(f'[{nombre}] ERROR: {str(e)[:120]}')

print()
print(f'Fuentes OK: {ok_count}/5')
print(f'Modo que usaria el servicio: {"REAL" if ok_count >= 2 else "RESPALDO"}')
