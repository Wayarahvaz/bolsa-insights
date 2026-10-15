"""
Executa o fluxo completo do Bolsa_Insights, na ordem,
e para no primeiro erro:

coleta.py -> calculos.py -> insights.py -> relatorio.py
"""
import subprocess
import sys

ETAPAS = ["coleta.py", "calculos.py", "insights.py", "relatorio.py"]


def main():
    for numero, etapa in enumerate(ETAPAS, start=1):
        print(f"\n{'=' * 60}\n[{numero}/{len(ETAPAS)}] {etapa}\n{'=' * 60}")
        resultado = subprocess.run([sys.executable, etapa])
        if resultado.returncode != 0:
            sys.exit(f"\nERRO em {etapa} - fluxo interrompido.")

    print("\nFluxo concluido: abra o relatorio_bolsa.xlsx.")


if __name__ == "__main__":
    main()