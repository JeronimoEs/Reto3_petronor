import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional, List
from utils import read_csv_timeseries, filter_valid_pairs


class DataCorrelationExporter:
    """
    Encapsula lectura de CSVs, gráficos y exportaciones para Tableau
    sin modificar el flujo existente de main.py.
    """

    def __init__(self, csv_a_path: str, csv_b_path: str) -> None:
        self.csv_a_path = csv_a_path
        self.csv_b_path = csv_b_path

        self.t1: List = []
        self.nivel1: List = []
        self.caudal1: List = []
        self.t2: List = []
        self.nivel2: List = []
        self.caudal2: List = []

    def load(self) -> None:
        self.t1, self.nivel1, self.caudal1 = read_csv_timeseries(self.csv_a_path)
        self.t2, self.nivel2, self.caudal2 = read_csv_timeseries(self.csv_b_path)

    def plot_levels(self) -> None:
        if not self.t1 and not self.t2:
            print("No se encontraron datos válidos para graficar.")
            return

        x1, y1 = filter_valid_pairs(self.t1, self.nivel1)
        x2, y2 = filter_valid_pairs(self.t2, self.nivel2)

        plt.figure(figsize=(12, 6))
        if x1:
            plt.plot(x1, y1, label="Nivel TK % - Archivo 1")
        if x2:
            plt.plot(x2, y2, label="Nivel TK % - Archivo 2")
        plt.xlabel("Fecha y hora")
        plt.ylabel("Nivel TK (%)")
        plt.title("Nivel de Tanque (%) - Comparación de CSVs")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def export_tableau_outputs(self, output_dir: str) -> None:
        """
        Genera merged_for_tableau.csv, correlation_matrix.csv y descriptive_stats.csv
        en el directorio indicado.
        """
        df1 = pd.DataFrame({
            "datetime": self.t1,
            "nivel_pct_1": self.nivel1,
            "caudal_m3h_1": self.caudal1,
        }).dropna(subset=["datetime"]).copy()

        df2 = pd.DataFrame({
            "datetime": self.t2,
            "nivel_pct_2": self.nivel2,
            "caudal_m3h_2": self.caudal2,
        }).dropna(subset=["datetime"]).copy()

        merged = pd.merge(df1, df2, on="datetime", how="outer").sort_values("datetime")

        # Columnas temporales
        merged["fecha"] = merged["datetime"].dt.date
        merged["hora"] = merged["datetime"].dt.hour
        merged["dia_semana"] = merged["datetime"].dt.day_name()
        merged["mes"] = merged["datetime"].dt.month
        merged["ano"] = merged["datetime"].dt.year

        # Columnas derivadas
        merged["diferencia_nivel"] = merged["nivel_pct_1"] - merged["nivel_pct_2"]
        merged["diferencia_caudal"] = merged["caudal_m3h_1"] - merged["caudal_m3h_2"]
        merged["promedio_nivel"] = merged[["nivel_pct_1", "nivel_pct_2"]].mean(axis=1)
        merged["promedio_caudal"] = merged[["caudal_m3h_1", "caudal_m3h_2"]].mean(axis=1)

        # Rolling features
        window_sizes = [3, 6, 12]
        for w in window_sizes:
            merged[f"nivel_pct_1_ma{w}"] = merged["nivel_pct_1"].rolling(window=w, min_periods=1).mean()
            merged[f"nivel_pct_2_ma{w}"] = merged["nivel_pct_2"].rolling(window=w, min_periods=1).mean()
            merged[f"caudal_m3h_1_ma{w}"] = merged["caudal_m3h_1"].rolling(window=w, min_periods=1).mean()
            merged[f"caudal_m3h_2_ma{w}"] = merged["caudal_m3h_2"].rolling(window=w, min_periods=1).mean()

            merged[f"rolling_corr_nivel_{w}"] = merged["nivel_pct_1"].rolling(window=w, min_periods=w).corr(merged["nivel_pct_2"])
            merged[f"rolling_corr_caudal_{w}"] = merged["caudal_m3h_1"].rolling(window=w, min_periods=w).corr(merged["caudal_m3h_2"])

        corr = merged.select_dtypes(include=["number"]).corr()
        stats = merged.select_dtypes(include=["number"]).describe()

        merged.to_csv(f"{output_dir}/merged_for_tableau.csv", index=False)
        corr.to_csv(f"{output_dir}/correlation_matrix.csv")
        stats.to_csv(f"{output_dir}/descriptive_stats.csv")

        print("Archivos exportados:")
        print("- merged_for_tableau.csv")
        print("- correlation_matrix.csv")
        print("- descriptive_stats.csv")


