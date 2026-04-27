import asyncio

# ================= CONFIG =================
API_URL = "http://127.0.0.1:5000"
PP_API_URL = "http://127.0.0.1:8000/check"
TELEGRAM_TOKEN = "8779255190:AAGAuKFA3Nc93NpC2aDpk2ouWitLJs8uYug"
ADMINS = [5651880136, 5133617831]
KEYS_FILE = "keys.json"

GATES_STATUS = {
    "pp": True, 
    "gt": True,
    "pfw": True
}

# --- MAPEOS ADICIONALES PARA BINS.SU ---
V_MAP = {
    "VISA": "Visa", "MC": "MASTERCARD", "MASTERCARD": "MASTERCARD", 
    "AMEX": "AMERICAN EXPRESS", "AMERICAN": "AMERICAN EXPRESS",
    "MAESTRO": "Maestro", "DISCOVER": "Discover", "DCI": "DCI", 
    "JCB": "JCB", "UNIONPAY": "CHINA UNION PAY"
}

L_MAP = {
    "CLASSIC": "Classic/Standard", "STANDARD" "ENHANCED": "Classic/Standard",
    "GOLD": "Gold/Prem", "PREM": "Gold/Prem", "PLATINUM": "Platinum", 
    "SIGNATURE": "Signature", "ELECTRON": "Electron", "PREPAID": "Prepaid",
    "BUSINESS": "Business", "CORPORATE": "Corporate", "INFINITE": "Infinite",
    "CASH": "Cash", "PURCHASING": "Purchasing", "VIRTUAL": "Virtual"
}

T_MAP = {"CREDIT": "Credit", "DEBIT": "Debit", "CHARGE": "CHARGE CARD"}