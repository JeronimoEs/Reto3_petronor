import cv2
import sys
import matplotlib.pyplot as plt
import pandas as pd
from analysis import DataCorrelationExporter
from image_processing import ImageProcessor

def main():
    # Rutas
    csv_a = "/Users/adrio/Desktop/Petronor/Reto3_petronor/csv/TK 103_1.xlsx - Hoja1.csv"
    csv_b = "/Users/adrio/Desktop/Petronor/Reto3_petronor/csv/YTK103_datos.xlsx - Sheet1.csv"
    imagen_path = "/Users/adrio/Desktop/Petronor/Reto3_petronor/imagenes/3be67a8e-c5ad-4a99-b797-cd024b925999.jpg"

    # Procesamiento de datos
    exporter = DataCorrelationExporter(csv_a, csv_b)
    exporter.load()
    exporter.plot_levels()
    exporter.export_tableau_outputs("/Users/adrio/Desktop/Petronor/Reto3_petronor/csv")

    # Procesamiento de imágenes
    img_proc = ImageProcessor()
    img_proc.show_original_and_gray(imagen_path)

if __name__ == "__main__":
    main()