
# utils.py
import re
import random

def luhn_check(n):
    """Verifica si un número cumple con el algoritmo de Luhn."""
    r = [int(ch) for ch in str(n)][::-1]
    return (sum(r[0::2]) + sum(sum(divmod(d * 2, 10)) for d in r[1::2])) % 10 == 0

def generar_tarjetas(plantilla, cantidad=10):
    """Genera tarjetas basadas en una plantilla y las valida con Luhn."""
    partes = re.split(r'[|/]', plantilla)
    bin_limpio = re.sub(r'\D', '', partes[0].lower().replace('x', 'n'))
    
    # Visa/Mastercard (4/5) suelen ser 16, Amex (3) suele ser 15
    longitud_target = 15 if bin_limpio.startswith('3') else 16
    
    mes_in = partes[1] if len(partes) > 1 else "rnd"
    anio_in = partes[2] if len(partes) > 2 else "rnd"
    cvv_in = partes[3] if len(partes) > 3 else "rnd"

    ccs = []
    for _ in range(cantidad):
        num = bin_limpio
        # Rellenar hasta longitud_target - 1 para calcular el dígito de control
        while len(num) < (longitud_target - 1):
            num += str(random.randint(0, 9))
        
        # Encontrar el dígito exacto que hace que el número pase Luhn
        for i in range(10):
            test_num = num + str(i)
            if luhn_check(test_num):
                num = test_num
                break
        
        m = mes_in.zfill(2) if mes_in.isdigit() else str(random.randint(1, 12)).zfill(2)
        y = anio_in[-2:] if anio_in.isdigit() else str(random.randint(25, 30))
        # Amex usa 4 dígitos en CVV, el resto 3
        cv = cvv_in if cvv_in.isdigit() else (str(random.randint(1000, 9999)) if longitud_target == 15 else str(random.randint(100, 999)))
        
        ccs.append(f"{num}|{m}|{y}|{cv}")
    return ccs

def extraer_datos_dict(texto):
    """Busca y extrae patrones de tarjetas en un bloque de texto."""
    r = re.findall(r"(\d{15,16})[|/: ](\d{1,2})[|/: ](\d{2,4})[|/: ](\d{3,4})", texto)
    return {c[-10:]: f"{c}|{m}|{a[-2:]}|{cv}" for c, m, a, cv in r}