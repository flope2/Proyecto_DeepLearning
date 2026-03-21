import requests
import time
import os
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


D_ID_API_URL = "https://api.d-id.com"


# ─────────────────────────────────────────
# AVATAR
# ─────────────────────────────────────────

def obtener_avatar():
    """
    Descarga una cara aleatoria de thispersondoesnotexist.com.
    Solo la descarga una vez — si ya existe la reutiliza.
    """
    os.makedirs("avatares", exist_ok=True)
    ruta = "avatares/avatar.jpg"

    if os.path.exists(ruta):
        print("  Usando avatar existente en avatares/avatar.jpg")
        return ruta

    print("  Descargando cara de thispersondoesnotexist.com...")
    response = requests.get(
        "https://thispersondoesnotexist.com",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with open(ruta, "wb") as f:
        f.write(response.content)
    print(f"  Avatar guardado!")
    return ruta


# ─────────────────────────────────────────
# D-ID API
# ─────────────────────────────────────────

def subir_imagen_did(ruta_imagen, api_key):
    """Sube la imagen del avatar a D-ID y devuelve su URL pública."""
    headers = {
        "Authorization": f"Basic {api_key}",
        "accept": "application/json"
    }
    with open(ruta_imagen, "rb") as f:
        files = {"image": ("avatar.jpg", f, "image/jpeg")}
        response = requests.post(f"{D_ID_API_URL}/images", headers=headers, files=files)

    if response.status_code not in [200, 201]:
        raise Exception(f"Error subiendo imagen a D-ID: {response.text}")

    return response.json()["url"]


def subir_audio_did(ruta_audio, api_key):
    """Sube el audio a D-ID y devuelve su URL pública."""
    headers = {
        "Authorization": f"Basic {api_key}",
        "accept": "application/json"
    }
    with open(ruta_audio, "rb") as f:
        files = {"audio": ("audio.mp3", f, "audio/mpeg")}
        response = requests.post(f"{D_ID_API_URL}/audios", headers=headers, files=files)

    if response.status_code not in [200, 201]:
        raise Exception(f"Error subiendo audio a D-ID: {response.text}")

    return response.json()["url"]


def crear_talk_did(imagen_url, audio_url, api_key):
    """
    Crea el vídeo en D-ID combinando imagen + audio.
    Devuelve el ID del talk para hacer polling después.
    """
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    body = {
        "source_url": imagen_url,
        "script": {
            "type":      "audio",
            "audio_url": audio_url
        },
        "config": {
            "fluent": True
        }
    }
    response = requests.post(f"{D_ID_API_URL}/talks", headers=headers, json=body)

    if response.status_code not in [200, 201]:
        raise Exception(f"Error creando talk en D-ID: {response.text}")

    return response.json()["id"]


def esperar_video_did(talk_id, api_key, max_intentos=30):
    """
    Hace polling hasta que D-ID termine de procesar el vídeo.
    Comprueba el estado cada 10 segundos.
    """
    headers = {
        "Authorization": f"Basic {api_key}",
        "accept": "application/json"
    }
    for intento in range(max_intentos):
        response = requests.get(f"{D_ID_API_URL}/talks/{talk_id}", headers=headers)
        data     = response.json()
        status   = data.get("status")

        print(f"  Estado D-ID: {status} (intento {intento+1}/{max_intentos})")

        if status == "done":
            return data["result_url"]
        elif status == "error":
            raise Exception(f"D-ID reportó error: {data}")

        time.sleep(10)

    raise Exception("Timeout esperando el vídeo de D-ID")


def descargar_video_did(url, carpeta="videos"):
    """Descarga el vídeo generado por D-ID."""
    os.makedirs(carpeta, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta      = f"{carpeta}/video_sin_subs_{timestamp}.mp4"

    response = requests.get(url)
    with open(ruta, "wb") as f:
        f.write(response.content)

    print(f"  Vídeo descargado: {ruta}")
    return ruta


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


# ─────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────

def generar_video(ruta_audio, ruta_subtitulos, api_key_did):
    print("\n" + "="*50)
    print("GENERANDO VÍDEO")
    print("="*50)

    print("\n1. Preparando avatar...")
    ruta_avatar = obtener_avatar()

    print("\n2. Subiendo archivos a D-ID...")
    imagen_url = subir_imagen_did(ruta_avatar, api_key_did)
    audio_url  = subir_audio_did(ruta_audio, api_key_did)

    print("\n3. Creando vídeo con avatar hablando...")
    talk_id = crear_talk_did(imagen_url, audio_url, api_key_did)
    print(f"  Talk ID: {talk_id}")

    print("\n4. Esperando que D-ID procese el vídeo (puede tardar unos minutos)...")
    result_url = esperar_video_did(talk_id, api_key_did)

    print("\n5. Descargando vídeo...")
    ruta_video_sin_subs = descargar_video_did(result_url)

    print("\n6. Añadiendo subtítulos estilo TikTok...")
    ruta_video_final = añadir_subtitulos(ruta_video_sin_subs, ruta_subtitulos)

    print("\n" + "="*50)
    print(f"VÍDEO FINAL LISTO: {ruta_video_final}")
    print("="*50)

    return ruta_video_final
