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


def _segundos_a_vtt(segundos):
    h  = int(segundos // 3600)
    m  = int((segundos % 3600) // 60)
    s  = int(segundos % 60)
    ms = int((segundos % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _generar_vtt(palabras, ruta_salida, words_in_cue=4):
    lineas = ["WEBVTT", ""]

    for i in range(0, len(palabras), words_in_cue):
        bloque = palabras[i : i + words_in_cue]
        inicio = bloque[0]["offset"]  / 10_000_000
        ultimo = bloque[-1]
        fin    = (ultimo["offset"] + ultimo["duration"]) / 10_000_000
        texto  = " ".join(p["text"] for p in bloque)

        lineas.append(f"{_segundos_a_vtt(inicio)} --> {_segundos_a_vtt(fin)}")
        lineas.append(texto)
        lineas.append("")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


async def _generar_audio_con_subtitulos(texto, ruta_audio, ruta_subtitulos, voz):
    comunicador = edge_tts.Communicate(texto, voz)
    palabras    = []

    with open(ruta_audio, "wb") as audio_file:
        async for chunk in comunicador.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                palabras.append({
                    "text":     chunk["text"],
                    "offset":   chunk["offset"],
                    "duration": chunk["duration"]
                })

    _generar_vtt(palabras, ruta_subtitulos, words_in_cue=4)


def generar_audio(texto_boletin, carpeta="audios", voz=VOZ_DEFAULT, max_chars=3000):
    # Truncamos el texto si es demasiado largo
    # 3000 chars ≈ 3-4 minutos de audio, dentro del límite de D-ID
    if len(texto_boletin) > max_chars:
        print(f"  Texto truncado de {len(texto_boletin)} a {max_chars} chars para respetar límite D-ID")
        texto_boletin = texto_boletin[:max_chars]
    os.makedirs(carpeta, exist_ok=True)

    timestamp       = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_audio      = f"{carpeta}/audio_{timestamp}.mp3"
    ruta_subtitulos = f"{carpeta}/subtitulos_{timestamp}.vtt"

    print(f"  Voz:         {voz}")
    print(f"  Chars:       {len(texto_boletin)}")
    print(f"  Audio:       {ruta_audio}")
    print(f"  Subtitulos:  {ruta_subtitulos}")

    asyncio.run(_generar_audio_con_subtitulos(
        texto_boletin, ruta_audio, ruta_subtitulos, voz
    ))

    tamanyo_mb = os.path.getsize(ruta_audio) / (1024 * 1024)

    return ruta_audio, ruta_subtitulos


def listar_voces():
    print("Voces disponibles en español:")
    for clave, descripcion in VOCES_DISPONIBLES.items():
        print(f"  {clave:<30} -> {descripcion}")