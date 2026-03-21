import edge_tts
import asyncio
import nest_asyncio
import os
from datetime import datetime

nest_asyncio.apply()

VOCES_DISPONIBLES = {
    "es-ES-AlvaroNeural":    "Español España - Alvaro (hombre)",
    "es-ES-ElviraNeural":    "Español España - Elvira (mujer)",
    "es-MX-JorgeNeural":     "Español México - Jorge (hombre)",
    "es-MX-DaliaNeural":     "Español México - Dalia (mujer)",
}

VOZ_DEFAULT = "es-ES-AlvaroNeural"


async def _generar_audio(texto, ruta_salida, voz):
    comunicador = edge_tts.Communicate(texto, voz)
    await comunicador.save(ruta_salida)


def generar_audio(texto_boletin, carpeta="audios", voz=VOZ_DEFAULT):
    os.makedirs(carpeta, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"{carpeta}/audio_{timestamp}.mp3"

    print(f"Generando audio...")
    print(f"  Voz:    {voz}")
    print(f"  Chars:  {len(texto_boletin)}")
    print(f"  Salida: {nombre_archivo}")

    asyncio.run(_generar_audio(texto_boletin, nombre_archivo, voz))

    tamanyo_mb = os.path.getsize(nombre_archivo) / (1024 * 1024)
    print(f"Audio generado correctamente! ({tamanyo_mb:.2f} MB)")

    return nombre_archivo


def listar_voces():
    print("Voces disponibles en español:")
    for clave, descripcion in VOCES_DISPONIBLES.items():
        print(f"  {clave:<30} → {descripcion}")