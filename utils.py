import cv2
import sys

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
