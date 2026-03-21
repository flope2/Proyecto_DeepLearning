import google.generativeai as genai
import time
import os
from datetime import datetime


def resumir_en_bloque(lista_articulos, modelo_ia):
    print("\n" + "="*50)
    print(f"INICIANDO RESUMEN EN BLOQUE ({len(lista_articulos)} noticias)")
    print("="*50)

    prompt = """
    Actúa como un presentador de noticias analítico y neutral conduciendo un boletín informativo.
    A continuación te proporciono una lista de noticias completas. Quiero que leas todas y redactes
    un texto continuo donde hagas un resumen breve, directo y totalmente objetivo de cada una.

    Utiliza transiciones naturales, fluidas y profesionales para pasar de una noticia a la otra,
    tal como se haría en un noticiero de radio o televisión.
    Es fundamental que, de manera orgánica durante estas transiciones o al inicio de cada tema,
    menciones explícitamente la fuente de la noticia.
    Evita usar asterísticos o cualquier formato que no sea el de un texto corrido, 
    como si lo estuvieras narrando en vivo. Tampoco hagas referencia a expresiones 
    faciales o corporales, ni al ambiente del estudio.

    AQUÍ TIENES LAS NOTICIAS:
    \n\n
    """

    for i, art in enumerate(lista_articulos):
        prompt += f"--- NOTICIA {i+1} ---\n"
        prompt += f"Título: {art['titulo']}\n"
        prompt += f"Fuente: {art['fuente']}\n"
        prompt += f"Texto completo: {art['texto_completo']}\n\n"

    print("Resumiendo noticias...")

    try:
        respuesta = modelo_ia.generate_content(prompt)
        print("Boletin generado con exito!")
        return respuesta.text
    except Exception as e:
        print(f"Error al procesar el bloque: {e}")
        return None


def guardar_boletin(texto_boletin, carpeta="boletines"):
    """
    Guarda el boletín en un archivo .txt con la fecha y hora en el nombre.
    Los archivos se guardan en una subcarpeta 'boletines/' para tenerlos ordenados.

    Ejemplo de archivo generado: boletines/boletin_2024-03-21_14-30-00.txt
    """
    # Creamos la carpeta si no existe
    os.makedirs(carpeta, exist_ok=True)

    # Nombre del archivo con fecha y hora para que cada boletín sea único
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"{carpeta}/boletin_{timestamp}.txt"

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        # Cabecera con metadata
        f.write(f"BOLETÍN DE NOTICIAS\n")
        f.write(f"Generado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(texto_boletin)

    print(f"Boletin guardado en: {nombre_archivo}")
    return nombre_archivo
