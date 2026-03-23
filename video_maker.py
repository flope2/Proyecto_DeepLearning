import os
import requests
import subprocess
from datetime import datetime
from moviepy.editor import (
    AudioFileClip, TextClip, ImageClip, ColorClip,
    CompositeVideoClip, concatenate_videoclips
)
from PIL import Image
import numpy as np


# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

ANCHO = 1080
ALTO  = 1920
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
# CLIPS POR TEMA
# ─────────────────────────────────────────

from PIL import ImageDraw, ImageFont

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


def _crear_clip_tema(tema, fuentes, duracion, ruta_imagen):
    if ruta_imagen and os.path.exists(ruta_imagen):
        arr_imagen = _preparar_imagen(ruta_imagen)
    else:
        arr_imagen = _imagen_fallback()

    img  = Image.fromarray(arr_imagen)
    draw = ImageDraw.Draw(img)

    try:
        fuente_titulo  = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 55)
        fuente_fuentes = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 38)
    except:
        fuente_titulo  = ImageFont.load_default()
        fuente_fuentes = ImageFont.load_default()

    # Texto del tema con wrap automático
    ancho_max = ANCHO - 120
    lineas    = _wrap_text(tema.upper(), fuente_titulo, ancho_max, draw)
    y_actual  = 150

    for linea in lineas:
        bbox       = draw.textbbox((0, 0), linea, font=fuente_titulo)
        ancho_text = bbox[2] - bbox[0]
        alto_text  = bbox[3] - bbox[1]
        x          = (ANCHO - ancho_text) // 2
        draw.text((x+2, y_actual+2), linea, font=fuente_titulo, fill=(0, 0, 0))
        draw.text((x,   y_actual),   linea, font=fuente_titulo, fill=(255, 255, 255))
        y_actual += alto_text + 10

    # Línea separadora debajo del título
    y_linea = y_actual + 10
    draw.rectangle([(190, y_linea), (890, y_linea + 3)], fill=(255, 255, 255))

    # Fuentes
    texto_fuentes = "Fuentes: " + " · ".join(fuentes)
    lineas_f      = _wrap_text(texto_fuentes, fuente_fuentes, ancho_max, draw)
    y_actual      = y_linea + 20

    for linea in lineas_f:
        bbox       = draw.textbbox((0, 0), linea, font=fuente_fuentes)
        ancho_text = bbox[2] - bbox[0]
        alto_text  = bbox[3] - bbox[1]
        x          = (ANCHO - ancho_text) // 2
        draw.text((x+2, y_actual+2), linea, font=fuente_fuentes, fill=(0, 0, 0))
        draw.text((x,   y_actual),   linea, font=fuente_fuentes, fill=(255, 255, 255))
        y_actual += alto_text + 8

    arr_final = np.array(img)
    return ImageClip(arr_final).set_duration(duracion)

# ─────────────────────────────────────────
# SUBTÍTULOS CON FFMPEG
# ─────────────────────────────────────────

def _añadir_subtitulos_ffmpeg(ruta_video, ruta_vtt, ruta_salida):
    """
    Quema los subtítulos usando ffmpeg directamente.
    Mucho más rápido que MoviePy TextClip.
    """
    # ffmpeg necesita la ruta con barras normales en el filtro
    ruta_vtt_ffmpeg = ruta_vtt.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", ruta_video,
        "-vf", f"subtitles={ruta_vtt_ffmpeg}:force_style='FontName=Arial,FontSize=16,PrimaryColour=&H00ffffff,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=80'",
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

def generar_video(ruta_audio, ruta_subtitulos, resumenes, pexels_api_key, carpeta="videos"):
    """
    Genera el vídeo final:
    - Un clip por tema con imagen de Pexels relacionada
    - Audio narrado de fondo
    - Subtítulos sincronizados via ffmpeg
    
    Parámetros:
    - resumenes: lista de dicts con 'tema', 'resumen' y 'fuentes'
                 (viene directamente de summarizer.resumir_noticias)
    """
    print("\n" + "="*50)
    print("GENERANDO VÍDEO")
    print("="*50)

    os.makedirs(carpeta, exist_ok=True)

    # Cargamos audio
    print("\n1. Cargando audio...")
    audio                = AudioFileClip(ruta_audio)
    duracion             = audio.duration
    n_temas              = len(resumenes)
    duracion_por_tema    = duracion / n_temas
    print(f"   Duración total:    {duracion:.1f}s")
    print(f"   Temas:             {n_temas}")
    print(f"   Duración por tema: {duracion_por_tema:.1f}s")

    # Buscamos imágenes por tema
    print("\n2. Buscando imágenes en Pexels...")
    for r in resumenes:
        print(f"  Tema: {r['tema'][:50]}...")
        r["imagen"] = buscar_imagen_pexels(r["tema"], pexels_api_key)

    # Creamos clips por tema
    print("\n3. Creando clips por tema...")
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

    # Concatenamos y añadimos audio
    print("\n4. Concatenando clips y añadiendo audio...")
    video_base      = concatenate_videoclips(clips, method="compose")
    video_con_audio = video_base.set_audio(audio)

    # Exportamos vídeo sin subtítulos
    timestamp     = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_sin_subs = f"{carpeta}/video_sin_subs_{timestamp}.mp4"

    print("\n5. Exportando vídeo base (sin subtítulos)...")
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

    # Añadimos subtítulos con ffmpeg
    print("\n6. Añadiendo subtítulos con ffmpeg...")
    ruta_final = f"{carpeta}/video_final_{timestamp}.mp4"
    resultado  = _añadir_subtitulos_ffmpeg(ruta_sin_subs, ruta_subtitulos, ruta_final)

    if not resultado:
        print("   ffmpeg falló, el vídeo sin subtítulos está en:", ruta_sin_subs)
        return ruta_sin_subs

    print(f"\n{'='*50}")
    print(f"VÍDEO FINAL LISTO: {ruta_final}")
    print(f"{'='*50}")

    return ruta_final