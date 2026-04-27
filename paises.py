
PAISES_DICT = {
    "AF": "AFGHANISTAN", "AL": "ALBANIA", "DE": "GERMANY", "AD": "ANDORRA",
    "AO": "ANGOLA", "AI": "ANGUILLA", "AQ": "ANTARCTICA", "AG": "ANTIGUA AND BARBUDA",
    "AN": "NETHERLANDS ANTILLES", "SA": "SAUDI ARABIA", "DZ": "ALGERIA",
    "AR": "ARGENTINA", "AM": "ARMENIA", "AW": "ARUBA", "AU": "AUSTRALIA",
    "AT": "AUSTRIA", "AZ": "AZERBAIJAN", "BS": "BAHAMAS", "BH": "BAHRAIN",
    "BD": "BANGLADESH", "BB": "BARBADOS", "BE": "BELGIUM", "BZ": "BELICE",
    "BJ": "BENIN", "BM": "BERMUDA", "BY": "BELARUS", "BO": "BOLIVIA",
    "BA": "BOSNIA AND HERZEGOVINA", "BW": "BOTSWANA", "BR": "BRAZIL", "BN": "BRUNEI",
    "BG": "BULGARIA", "BF": "BURKINA FASO", "BI": "BURUNDI", "BT": "BHUTAN",
    "CV": "CAPE VERDE", "KY": "CAYMAN ISLANDS", "KH": "CAMBODIA", "CM": "CAMEROON",
    "CA": "CANADA", "CF": "CENTRAL AFRICAN REPUBLIC", "CO": "COLOMBIA", "KM": "COMOROS",
    "CG": "CONGO", "CD": "CONGO (DRC)", "CR": "COSTA RICA", "HR": "CROATIA",
    "CU": "CUBA", "TD": "CHAD", "CZ": "CZECH REPUBLIC", "CL": "CHILE",
    "CN": "CHINA", "CY": "CHIPRE", "DK": "DENMARK", "DO": "DOMINICAN REPUBLIC",
    "EC": "ECUADOR", "EG": "EGYPT", "AE": "UNITED ARAB EMIRATES", "ES": "SPAIN",
    "US": "UNITED STATES OF AMERICA", "EE": "ESTONIA", "ET": "ETHIOPIA",
    "PH": "PHILIPPINES", "FI": "FINLAND", "FR": "FRANCE", "GA": "GABON",
    "GE": "GEORGIA", "GH": "GHANA", "GI": "GIBRALTAR", "GR": "GREECE",
    "GT": "GUATEMALA", "HN": "HONDURAS", "HK": "HONG KONG", "HU": "HUNGARY",
    "IN": "INDIA", "ID": "INDONESIA", "IR": "IRAN", "IQ": "IRAQ", "IE": "IRELAND",
    "IL": "ISRAEL", "IT": "ITALY", "JM": "JAMAICA", "JP": "JAPAN", "JO": "JORDAN",
    "KZ": "KAZAKHSTAN", "KE": "KENYA", "KW": "KUWAIT", "LB": "LEBANON", "LR": "LIBERIA",
    "LY": "LIBYA", "LT": "LITHUANIA", "LU": "LUXEMBOURG", "MA": "MOROCCO",
    "MX": "MEXICO", "NI": "NICARAGUA", "NG": "NIGERIA", "NO": "NORWAY",
    "NZ": "NEW ZEALAND", "PA": "PANAMA", "PY": "PARAGUAY", "PE": "PERU",
    "PL": "POLAND", "PT": "PORTUGAL", "PR": "PUERTO RICO", "GB": "UNITED KINGDOM",
    "RU": "RUSSIA", "SV": "EL SALVADOR", "SE": "SWEDEN", "CH": "SWITZERLAND",
    "TH": "THAILAND", "TW": "TAIWAN", "TR": "TURKEY", "UA": "UKRAINE",
    "UY": "URUGUAY", "VE": "VENEZUELA", "VN": "VIETNAM"
}

def obtener_pais_formateado(iso_raw):
    """Returns Country Name in English + Flag Emoji in UPPER CASE."""
    codigo = iso_raw.strip().upper()
    nombre = PAISES_DICT.get(codigo, codigo).upper()
    
    # Generate flag emoji automatically
    if len(codigo) == 2:
        bandera = "".join(chr(127397 + ord(c)) for c in codigo)
    else:
        bandera = "🌐"
        
    return f"{nombre} {bandera}"