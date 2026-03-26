import os
import requests
import subprocess
from datetime import datetime
from moviepy.editor import (
    AudioFileClip, ImageClip, ColorClip,
    CompositeVideoClip, concatenate_videoclips
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

ANCHO = 540
ALTO  = 960
FPS   = 25

from moviepy.config import change_settings
change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
})


# ─────────────────────────────────────────
# PEXELS
# ─────────────────────────────────────────

def _extraer_keywords(titulo):
    palabras_vacias = {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "de", "del", "en", "y", "a", "por", "para", "con", "sin",
        "que", "se", "su", "sus", "al", "es", "son", "ha", "han",
        "no", "si", "pero", "más", "ya", "le", "lo", "como", "este",
        "esta", "estos", "estas", "ese", "esa", "tras", "ante", "sobre"
    }
    palabras = titulo.lower().replace(":", "").replace(",", "").replace("«", "").replace("»", "").split()
    keywords = [p for p in palabras if p not in palabras_vacias and len(p) > 3]
    return " ".join(keywords[:4])


def buscar_imagen_pexels(query, api_key, carpeta="imagenes"):
    os.makedirs(carpeta, exist_ok=True)

    keywords = _extraer_keywords(query)
    print(f"    Keywords: '{keywords}'")

    headers = {"Authorization": api_key}
    params  = {
        "query":       keywords,
        "per_page":    1,
        "orientation": "portrait",
        "size":        "large"
    }

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers, params=params, timeout=10
        )
        fotos = response.json().get("photos", [])

        if not fotos:
            print(f"    Sin resultados, usando búsqueda genérica...")
            params["query"] = "noticias periodico"
            response = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers, params=params, timeout=10
            )
            fotos = response.json().get("photos", [])

        if not fotos:
            return None

        url_imagen = fotos[0]["src"]["large"]
        nombre     = f"{carpeta}/img_{abs(hash(query))}.jpg"

        if not os.path.exists(nombre):
            img_response = requests.get(url_imagen, timeout=15)
            with open(nombre, "wb") as f:
                f.write(img_response.content)

        print(f"    Imagen guardada: {nombre}")
        return nombre

    except Exception as e:
        print(f"    Error Pexels: {e}")
        return None


# ─────────────────────────────────────────
# PROCESADO DE IMAGEN
# ─────────────────────────────────────────

def _preparar_imagen(ruta_imagen):
    img = Image.open(ruta_imagen).convert("RGB")

    ratio_objetivo = ANCHO / ALTO
    ratio_imagen   = img.width / img.height

    if ratio_imagen > ratio_objetivo:
        nuevo_alto  = ALTO
        nuevo_ancho = int(ALTO * ratio_imagen)
    else:
        nuevo_ancho = ANCHO
        nuevo_alto  = int(ANCHO / ratio_imagen)

    img  = img.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    left = (nuevo_ancho - ANCHO) // 2
    top  = (nuevo_alto  - ALTO)  // 2
    img  = img.crop((left, top, left + ANCHO, top + ALTO))

    arr       = np.array(img, dtype=np.float32)
    gradiente = np.linspace(0, 1, ALTO)[:, np.newaxis, np.newaxis]
    arr       = arr * (1 - gradiente * 0.7)
    arr       = np.clip(arr, 0, 255).astype(np.uint8)

    return arr


def _imagen_fallback():
    return np.full((ALTO, ANCHO, 3), 30, dtype=np.uint8)


# ─────────────────────────────────────────
# UTILIDAD — WRAP DE TEXTO
# ─────────────────────────────────────────

def _wrap_text(texto, fuente, ancho_max, draw):
    """Divide el texto en líneas para que no se salga del ancho."""
    palabras = texto.split()
    lineas   = []
    linea    = ""

    for palabra in palabras:
        prueba = linea + " " + palabra if linea else palabra
        bbox   = draw.textbbox((0, 0), prueba, font=fuente)
        if bbox[2] - bbox[0] <= ancho_max:
            linea = prueba
        else:
            if linea:
                lineas.append(linea)
            linea = palabra

    if linea:
        lineas.append(linea)

    return lineas

# ─────────────────────────────────────────
# CLIP POR TEMA — versión TikTok
# ─────────────────────────────────────────

def _crear_clip_tema(tema, fuentes, duracion, ruta_imagen):
    
    if ruta_imagen and os.path.exists(ruta_imagen):
        arr_imagen = _preparar_imagen(ruta_imagen)
    else:
        arr_imagen = _imagen_fallback()

    clip_fondo = ImageClip(arr_imagen).set_duration(duracion)

    # Fondo semitransparente detrás del texto
    alto_caja = 320
    arr_caja  = np.zeros((alto_caja, ANCHO, 3), dtype=np.uint8)
    clip_caja = (
        ImageClip(arr_caja)
        .set_duration(duracion)
        .set_position((0, 100))
        .set_opacity(0.5)
    )

    # Texto con PIL
    img_texto = Image.fromarray(arr_imagen.copy())
    draw      = ImageDraw.Draw(img_texto)

    try:
        fuente_tema    = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 62)
        fuente_fuentes = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf",  27)
    except:
        fuente_tema    = ImageFont.load_default()
        fuente_fuentes = ImageFont.load_default()

    # Tema con wrap
    lineas = _wrap_text(tema.upper(), fuente_tema, ANCHO - 80, draw)
    y_actual = 120

    for linea in lineas:
        bbox  = draw.textbbox((0, 0), linea, font=fuente_tema)
        ancho = bbox[2] - bbox[0]
        alto  = bbox[3] - bbox[1]
        x     = (ANCHO - ancho) // 2
        draw.text((x+3, y_actual+3), linea, font=fuente_tema, fill=(0, 0, 0))
        draw.text((x,   y_actual),   linea, font=fuente_tema, fill=(255, 255, 255))
        y_actual += alto + 12

    # Línea separadora
    y_linea = y_actual + 8
    draw.rectangle([(80, y_linea), (ANCHO - 80, y_linea + 4)], fill=(255, 255, 255))

    # Fuentes
    texto_fuentes = "  ·  ".join(list(dict.fromkeys(fuentes)))
    lineas_f      = _wrap_text(texto_fuentes, fuente_fuentes, ANCHO - 80, draw)
    y_actual      = y_linea + 18

    for linea in lineas_f:
        bbox  = draw.textbbox((0, 0), linea, font=fuente_fuentes)
        ancho = bbox[2] - bbox[0]
        alto  = bbox[3] - bbox[1]
        x     = (ANCHO - ancho) // 2
        draw.text((x+2, y_actual+2), linea, font=fuente_fuentes, fill=(0, 0, 0))
        draw.text((x,   y_actual),   linea, font=fuente_fuentes, fill=(200, 200, 200))
        y_actual += alto + 8

    # Clip de texto con fade in
    clip_texto = (
        ImageClip(np.array(img_texto))
        .set_duration(duracion)
        .fadein(0.4)
    )

    return CompositeVideoClip([clip_fondo, clip_caja, clip_texto])


# ─────────────────────────────────────────
# SUBTÍTULOS CON FFMPEG
# ─────────────────────────────────────────

def _añadir_subtitulos_ffmpeg(ruta_video, ruta_vtt, ruta_salida):
    ruta_vtt_ffmpeg = ruta_vtt.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", ruta_video,
        "-vf", f"subtitles={ruta_vtt_ffmpeg}:force_style='FontName=Arial,FontSize=12,PrimaryColour=&H00ffffff,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=80'",
        "-c:a", "copy",
        ruta_salida
    ]

    print(f"   Ejecutando ffmpeg...")
    resultado = subprocess.run(cmd, capture_output=True, text=True)

    if resultado.returncode != 0:
        print(f"   Error ffmpeg: {resultado.stderr[-500:]}")
        return None

    print(f"   Subtítulos añadidos!")
    return ruta_salida


# ─────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────

def generar_video(ruta_audio, ruta_subtitulos, resumenes,
                  pexels_api_key, modelo_ia=None, carpeta="videos"):
    print("\n" + "="*50)
    print("GENERANDO VÍDEO")
    print("="*50)

    os.makedirs(carpeta, exist_ok=True)

    print("\n1. Cargando audio...")
    audio             = AudioFileClip(ruta_audio)
    duracion          = audio.duration
    n_temas           = len(resumenes)
    duracion_por_tema = duracion / n_temas
    print(f"   Duración total:    {duracion:.1f}s")
    print(f"   Temas:             {n_temas}")
    print(f"   Duración por tema: {duracion_por_tema:.1f}s")

    print("\n2. Buscando imágenes en Pexels...")
    for r in resumenes:
        print(f"  Tema: {r['tema'][:50]}...")
        if modelo_ia:
            from summarizer import generar_query_imagen
            query = generar_query_imagen(r["tema"], modelo_ia)
        else:
            query = r["tema"]
        r["imagen"] = buscar_imagen_pexels(query, pexels_api_key)

    print("\n3. Creando clips...")
    clips = []
    for i, r in enumerate(resumenes):
        print(f"   [{i+1}/{n_temas}] {r['tema'][:40]}...")
        clip = _crear_clip_tema(
            tema        = r["tema"],
            fuentes     = r["fuentes"],
            duracion    = duracion_por_tema,
            ruta_imagen = r.get("imagen")
        )
        clips.append(clip)

    print("\n4. Concatenando clips y añadiendo audio...")
    video_base      = concatenate_videoclips(clips, method="compose")
    video_con_audio = video_base.set_audio(audio)

    timestamp     = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_sin_subs = f"{carpeta}/video_sin_subs_{timestamp}.mp4"

    print("\n5. Exportando vídeo base...")
    video_con_audio.write_videofile(
        ruta_sin_subs,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )

    audio.close()
    video_base.close()
    video_con_audio.close()

    # Escalamos a resolución completa con ffmpeg
    print("\n5b. Escalando a resolución completa...")
    ruta_escalado = f"{carpeta}/video_hd_{timestamp}.mp4"
    cmd_scale = [
        "ffmpeg", "-y",
        "-i", ruta_sin_subs,
        "-vf", "scale=1080:1920",
        "-c:a", "copy",
        ruta_escalado
    ]
    subprocess.run(cmd_scale, capture_output=True)
    ruta_sin_subs = ruta_escalado  # usamos el escalado para los subtítulos

    print("\n6. Añadiendo subtítulos con ffmpeg...")
    ruta_final = f"{carpeta}/video_final_{timestamp}.mp4"
    resultado  = _añadir_subtitulos_ffmpeg(ruta_sin_subs, ruta_subtitulos, ruta_final)

    if not resultado:
        print("   ffmpeg falló, vídeo sin subtítulos en:", ruta_sin_subs)
        return ruta_sin_subs

    print(f"\n{'='*50}")
    print(f"VÍDEO FINAL LISTO: {ruta_final}")
    print(f"{'='*50}")

    return ruta_final