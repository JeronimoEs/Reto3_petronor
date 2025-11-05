import cv2
import sys
import csv
from datetime import datetime
from typing import List, Dict, Optional, Tuple

def convertir_a_gris(ruta_imagen):
    """
    Carga una imagen desde una ruta y la convierte a escala de grises.
    """
    # Cargar la imagen en color
    img_color = cv2.imread(ruta_imagen)

    if img_color is None:
        print(f"Error: No se pudo cargar la imagen en la ruta: {ruta_imagen}")
        return None  

    # Convertir la imagen de BGR a GRAY 
    img_gris = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)

    return img_gris


def _parse_spanish_number(raw: str) -> Optional[float]:
    """
    Convierte números con posible coma decimal y separadores/undidades a float.
    Acepta formatos como: "3103,7 m3/h", "-231,7", "2 W/m2", "99%" (devolverá 99.0 si se usa aparte).
    Devuelve None si no se puede convertir.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.upper() == "#VALUE!":
        return None

    # Conservar solo dígitos, signos y separadores
    filtered = []
    for ch in s:
        if ch.isdigit() or ch in "+-.,":
            filtered.append(ch)
    num = "".join(filtered)
    if num == "" or num in {"+", "-", "+.", "-."}:
        return None

    # Si contiene punto y coma, asumimos punto como miles y coma como decimal
    if "," in num and "." in num:
        num = num.replace(".", "")
        num = num.replace(",", ".")
    elif "," in num and "." not in num:
        # Solo coma presente: tratar como decimal
        num = num.replace(",", ".")
    # else: solo punto o ninguno -> float estándar

    try:
        return float(num)
    except ValueError:
        return None


def _parse_percentage(raw: str) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip().replace("%", "")
    return _parse_spanish_number(s)


def _parse_datetime_mmddyy_hhmm(raw: str) -> Optional[datetime]:
    """
    Parsea fechas como "10/6/25 22:39" (MM/DD/YY HH:MM).
    Devuelve None si no coincide.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    # Algunos CSV pueden traer segundos; intentamos varias máscaras
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def read_csv_timeseries(csv_path: str) -> Tuple[List[datetime], List[Optional[float]], List[Optional[float]]]:
    """
    Lee un CSV con columnas tipo: "Día", "Nivel TK %", "Caudal" y devuelve series.
    - x_times: lista de datetime
    - niveles_pct: lista de float o None
    - caudales_m3h: lista de float o None
    Tolera encabezados con saltos de línea dentro de comillas.
    """
    times: List[datetime] = []
    niveles: List[Optional[float]] = []
    caudales: List[Optional[float]] = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        header: Optional[List[str]] = None
        for row in reader:
            if not row:
                continue
            # Detectar encabezado: suele contener "Día" y "Nivel TK %"
            if header is None:
                header = row
                # Si la primera fila no es encabezado (a veces ya es dato), validamos
                header_lower = [h.strip().lower() for h in header]
                if "día" not in header_lower and "dia" not in header_lower:
                    # No parece encabezado: tratamos fila como dato, y fabricamos índices por posición conocida
                    # Intentar índices por posición aproximada según muestra: Dia idx=3, Caudal idx=5, Nivel % idx=6
                    dia_idx, caudal_idx, nivel_idx = 3, 5, 6
                    # Procesar esta fila como dato
                    dia_val = row[dia_idx] if len(row) > dia_idx else None
                    nivel_val = row[nivel_idx] if len(row) > nivel_idx else None
                    caudal_val = row[caudal_idx] if len(row) > caudal_idx else None

                    dt = _parse_datetime_mmddyy_hhmm(dia_val)
                    if dt is not None:
                        times.append(dt)
                        niveles.append(_parse_percentage(nivel_val))
                        caudales.append(_parse_spanish_number(caudal_val))
                    # A partir de aquí leemos el resto de filas como datos
                    break
                else:
                    # Tenemos encabezado válido; seguimos leyendo datos
                    break

        # Si llegamos aquí, tenemos header detectado o ya añadimos primera fila de datos
        if header is not None and ("día" in [h.strip().lower() for h in header] or "dia" in [h.strip().lower() for h in header]):
            # Mapa de índices por nombre de columna, tolerando variaciones
            header_map = {h.strip().lower(): i for i, h in enumerate(header)}
            # Normalizaciones simples
            def find_idx(keys: List[str]) -> Optional[int]:
                for k in keys:
                    if k in header_map:
                        return header_map[k]
                return None

            dia_idx = find_idx(["día", "dia", "fecha", "fecha/hora"])  # principal: "Día"
            nivel_idx = find_idx(["nivel tk %", "nivel %", "nivel", "nivel%"])
            caudal_idx = find_idx(["caudal", "caudal m3/h", "caudal (m3/h)"])

            for row in reader:
                if not row:
                    continue
                dia_val = row[dia_idx] if dia_idx is not None and len(row) > dia_idx else None
                nivel_val = row[nivel_idx] if nivel_idx is not None and len(row) > nivel_idx else None
                caudal_val = row[caudal_idx] if caudal_idx is not None and len(row) > caudal_idx else None

                dt = _parse_datetime_mmddyy_hhmm(dia_val)
                if dt is None:
                    continue
                times.append(dt)
                niveles.append(_parse_percentage(nivel_val))
                caudales.append(_parse_spanish_number(caudal_val))

    return times, niveles, caudales


def filter_valid_pairs(xs: List[datetime], ys: List[Optional[float]]) -> Tuple[List[datetime], List[float]]:
    """Elimina puntos con y=None manteniendo correspondencia temporal."""
    fx: List[datetime] = []
    fy: List[float] = []
    for x, y in zip(xs, ys):
        if y is None:
            continue
        fx.append(x)
        fy.append(float(y))
    return fx, fy
