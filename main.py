import cv2
import sys
from utils import convertir_a_gris 

def main():

    nombre_imagen_a_procesar = 'imagenes\\3be67a8e-c5ad-4a99-b797-cd024b925999.jpg'

    print(f"Procesando imagen: {nombre_imagen_a_procesar}")

    imagen_en_gris = convertir_a_gris(nombre_imagen_a_procesar)

    if imagen_en_gris is not None:
        print("¡Imagen convertida a gris exitosamente!")

        cv2.imshow('Imagen Original (Color)', cv2.imread(nombre_imagen_a_procesar))
        cv2.imshow('Resultado (Escala de Grises)', imagen_en_gris)

        print("\nPresiona cualquier tecla en la ventana de la imagen para cerrar.")
        cv2.waitKey(0) 
        cv2.destroyAllWindows() 
    else:
        print("La conversión a escala de grises falló.")

if __name__ == "__main__":
    main()