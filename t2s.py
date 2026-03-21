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


async def _generar_audio_con_subtitulos(texto, ruta_audio, ruta_subtitulos, voz):
    comunicador = edge_tts.Communicate(texto, voz)
    sub_maker   = edge_tts.SubMaker()

    with open(ruta_audio, "wb") as audio_file:
        async for chunk in comunicador.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                sub_maker.create_sub(
                    (chunk["offset"], chunk["duration"]),
                    chunk["text"]
                )

    # Guardamos el archivo VTT con 4 palabras por subtítulo
    with open(ruta_subtitulos, "w", encoding="utf-8") as sub_file:
        sub_file.write(sub_maker.generate_subs(words_in_cue=4))


def generar_audio(texto_boletin, carpeta="audios", voz=VOZ_DEFAULT):
    os.makedirs(carpeta, exist_ok=True)

    timestamp       = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_audio      = f"{carpeta}/audio_{timestamp}.mp3"
    ruta_subtitulos = f"{carpeta}/subtitulos_{timestamp}.vtt"

    print(f"Generando audio y subtitulos...")
    print(f"  Voz:         {voz}")
    print(f"  Chars:       {len(texto_boletin)}")
    print(f"  Audio:       {ruta_audio}")
    print(f"  Subtitulos:  {ruta_subtitulos}")

    asyncio.run(_generar_audio_con_subtitulos(
        texto_boletin, ruta_audio, ruta_subtitulos, voz
    ))

    tamanyo_mb = os.path.getsize(ruta_audio) / (1024 * 1024)
    print(f"Audio generado! ({tamanyo_mb:.2f} MB)")
    print(f"Subtitulos generados!")

    # Devolvemos ambas rutas como tupla
    return ruta_audio, ruta_subtitulos


def listar_voces():
    print("Voces disponibles en español:")
    for clave, descripcion in VOCES_DISPONIBLES.items():
        print(f"  {clave:<30} -> {descripcion}")
