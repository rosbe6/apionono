# engines/bins_engine.py
import httpx
import re
from bs4 import BeautifulSoup
from paises import obtener_pais_formateado 
from config import V_MAP, T_MAP, L_MAP

async def get_bin_dict(cc_bin):
    """Devuelve diccionario para el formato HERMOSO con puntitos"""
    solo_bin = re.sub(r'\D', '', str(cc_bin))[:6]
    url = "https://bins.su/"
    payload = f"action=searchbins&bins={solo_bin}&bank=&country="
    headers = {'content-type': 'application/x-www-form-urlencoded', 'user-agent': 'Mozilla/5.0'}
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.post(url, content=payload, headers=headers)
            soup = BeautifulSoup(r.text, 'html.parser')
            result_div = soup.find('div', id='result')
            if result_div:
                table = result_div.find('table')
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        tds = rows[1].find_all('td')
                        return {
                            "bin": solo_bin,
                            "pais": obtener_pais_formateado(tds[1].text.strip()),
                            "brand": tds[2].text.strip().upper(),
                            "type": tds[3].text.strip().upper(),
                            "level": tds[4].text.strip().upper(),
                            "bank": tds[5].text.strip().upper()
                        }
    except: pass
    return None

async def get_bin_info(cc_bin):
    """Mantiene compatibilidad con el formato viejo (String)"""
    data = await get_bin_dict(cc_bin)
    if not data: return "EMPTY"
    return f"{data['type']} - {data['level']} - {data['brand']}, {data['bank']}, {data['pais']}"

async def fetch_bins_engine(country="", bank="", vendor="", card_type="", level="", limit=1000):
    """ESTA ES LA QUE FALTABA: El buscador de bancos/países"""
    url = "https://bins.su/"
    headers = {"content-type": "application/x-www-form-urlencoded", "user-agent": "Mozilla/5.0"}
    payload = {
        "action": "searchbins",
        "bins": "",
        "bank": bank,
        "country": country
    }
    # Esto es vital para que la web te haga caso
    if vendor: payload["vendor[]"] = vendor
    if card_type: payload["type[]"] = card_type
    if level: payload["level[]"] = level
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, data=payload, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            result_div = soup.find('div', {'id': 'result'})
            
            if not result_div or "Total found 0" in result_div.text:
                return "EMPTY"
            
            table = result_div.find('table')
            rows = table.find_all('tr')[1:]
            
            biblioteca = {}
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    bin_num = cols[0].text.strip()
                    vdr_val = cols[2].text.strip()
                    typ_val = cols[3].text.strip()
                    lvl_val = cols[4].text.strip()
                    banco_raw = cols[5].text.strip()
                    
                    b_key = re.sub(r'[^a-zA-Z0-9]', '', banco_raw).lower() or "indefinido"
                    cat_tipo = f"{vdr_val} {typ_val} ({lvl_val})"
                    
                    if b_key not in biblioteca:
                        biblioteca[b_key] = {"nombre": banco_raw, "sub": {}}
                    if cat_tipo not in biblioteca[b_key]["sub"]:
                        biblioteca[b_key]["sub"][cat_tipo] = []
                    
                    biblioteca[b_key]["sub"][cat_tipo].append(bin_num)
            return biblioteca
    except: return None