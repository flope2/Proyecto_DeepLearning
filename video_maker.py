import os
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


# ─────────────────────────────────────────
# SUBTÍTULOS
# ─────────────────────────────────────────

def vtt_tiempo_a_segundos(tiempo_str):
    """Convierte un timestamp VTT (HH:MM:SS.mmm) a segundos."""
    partes = tiempo_str.strip().replace(",", ".").split(":")
    if len(partes) == 3:
        return int(partes[0]) * 3600 + int(partes[1]) * 60 + float(partes[2])
    else:
        return int(partes[0]) * 60 + float(partes[1])


def parsear_vtt(ruta_vtt):
    """
    Parsea un archivo VTT y devuelve lista de (inicio, fin, texto).
    """
    subtitulos = []

    with open(ruta_vtt, "r", encoding="utf-8") as f:
        contenido = f.read()

    bloques = contenido.strip().split("\n\n")

    for bloque in bloques:
        lineas       = bloque.strip().split("\n")
        tiempo_linea = None
        texto_lineas = []

        for linea in lineas:
            if "-->" in linea:
                tiempo_linea = linea
            elif linea and not linea.startswith("WEBVTT") and not linea.isdigit():
                texto_lineas.append(linea)

        if not tiempo_linea or not texto_lineas:
            continue

        partes = tiempo_linea.split(" --> ")
        inicio = vtt_tiempo_a_segundos(partes[0])
        fin    = vtt_tiempo_a_segundos(partes[1])
        texto  = " ".join(texto_lineas)

        subtitulos.append((inicio, fin, texto))

    return subtitulos


def añadir_subtitulos(ruta_video, ruta_vtt, carpeta="videos"):
    """
    Quema los subtítulos encima del vídeo al estilo TikTok:
    texto centrado, blanco con borde negro.
    """
    print("  Cargando vídeo...")
    video      = VideoFileClip(ruta_video)
    subtitulos = parsear_vtt(ruta_vtt)

    print(f"  Procesando {len(subtitulos)} subtítulos...")
    clips_subs = []

    for inicio, fin, texto in subtitulos:
        fin = min(fin, video.duration)
        if inicio >= video.duration:
            continue

        sub_clip = (
            TextClip(
                texto,
                fontsize=50,
                color="white",
                stroke_color="black",
                stroke_width=2.5,
                font="Arial-Bold",
                method="caption",
                size=(int(video.w * 0.85), None)
            )
            .set_position("center")
            .set_start(inicio)
            .set_end(fin)
        )
        clips_subs.append(sub_clip)

    print("  Componiendo vídeo final...")
    video_final = CompositeVideoClip([video] + clips_subs)

    timestamp   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_salida = f"{carpeta}/video_final_{timestamp}.mp4"

    video_final.write_videofile(
        ruta_salida,
        fps=25,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )

    video.close()
    video_final.close()

    print(f"  Vídeo final guardado: {ruta_salida}")
    return ruta_salida
