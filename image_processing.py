import cv2
from typing import Optional
from utils import convertir_a_gris


class ImageProcessor:
    """
    Encapsula operaciones de procesamiento de imágenes.
    """

    def __init__(self) -> None:
        pass

    def convert_to_gray(self, image_path: str):
        return convertir_a_gris(image_path)

    def show_original_and_gray(self, image_path: str) -> None:
        print(f"Procesando imagen: {image_path}")
        imagen_en_gris = self.convert_to_gray(image_path)
        if imagen_en_gris is not None:
            print("¡Imagen convertida a gris exitosamente!")
            cv2.imshow('Imagen Original (Color)', cv2.imread(image_path))
            cv2.imshow('Resultado (Escala de Grises)', imagen_en_gris)
            print("\nPresiona cualquier tecla en la ventana de la imagen para cerrar.")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("La conversión a escala de grises falló.")


