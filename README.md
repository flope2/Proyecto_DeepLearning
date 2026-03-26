# *al DIA — Resumen de noticias objetivo y neutro en formato vídeo*

**al DIA** es un sistema automatizado que recopila noticias de diversos medios españoles, las contrasta, genera un resumen neutral usando IA y produce un vídeo listo para publicar en formato TikTok/Reels.

En la actualidad, los medios de comunicación suelen tener sesgos editoriales. Leer múltiples periódicos cada día para formarse una opinión objetiva requiere tiempo que la mayoría de personas no tiene. **al DIA** resuelve esto automatizando el contraste de fuentes y generando un resumen neutral en formato vídeo, consumible en minutos.

---

## Arquitectura

El sistema funciona en 4 pasos encadenados:

### Paso 1 — Recolección (`news_fetcher.py`)
- Lee los RSS oficiales de 9 medios españoles con `feedparser`
- Extrae el texto completo de cada artículo con `trafilatura`
- Para medios con paywall (El País, El Mundo) usa el resumen del RSS como fallback
- Para medios sin RSS propio (Antena 3, RTVE) usa Google News RSS
- Filtra artículos por período temporal (última hora, día o semana)

### Paso 2 — Resumen neutral (`summarizer.py`)
- **Gemini 2.5 Flash** realiza 3 llamadas:
  1. Agrupa los artículos por tema
  2. Para cada tema, genera un resumen contrastando las distintas fuentes
  3. Une todos los resúmenes en un boletín fluido con transiciones naturales
- **Filtro ideológico**: solo publica temas cubiertos por al menos 2 bloques ideológicos distintos (progresista, centro, conservador), garantizando neutralidad real
- El boletín se guarda automáticamente en `boletines/`

### Paso 3 — Síntesis de voz y subtítulos (`t2s.py`)
- **edge-tts**  convierte el texto a voz de alta calidad en español
- **Whisper** (OpenAI) transcribe el audio y genera subtítulos `.vtt` con timestamps precisos palabra a palabra
- Sistema de corrección de nombres propios (RTVE, ABC, al DIA...)

### Paso 4 — Generación de vídeo (`video_maker.py`)
- **Pexels API** busca una imagen fotográfica representativa por tema
- **PIL** dibuja el título del tema y las fuentes encima de la imagen
- **MoviePy** concatena los clips de cada tema y añade el audio narrado
- **ffmpeg** quema los subtítulos en el video
- Formato final: vídeo vertical 1080×1920 a 25fps

---
##  Garantía de neutralidad

El sistema implementa un **filtro ideológico explícito** basado en la clasificación de cada medio:

| Medio | Tendencia |
|-------|-----------|
| ElDiario | Izquierda |
| El País | Centro-izquierda |
| La Vanguardia | Centro |
| Europa Press | Centro |
| 20minutos | Centro |
| RTVE | Centro |
| Antena 3 | Centro-derecha |
| El Mundo | Centro-derecha |
| ABC | Derecha |

Un tema solo se publica si está cubierto por medios de **al menos 2 bloques ideológicos distintos**. Los temas cubiertos únicamente por medios del mismo bloque se descartan automáticamente.

---

##  Estructura del proyecto

```
Proyecto_DeepLearning/
├── Proyecto_DeepLearning.ipynb   ← notebook principal (pipeline completo)
├── news_fetcher.py               ← recolección de noticias vía RSS
├── summarizer.py                 ← resumen neutral con Gemini
├── t2s.py                        ← síntesis de voz y subtítulos
├── video_maker.py                ← generación del vídeo final
├── .env                          ← API keys (no incluido en el repo)
├── boletines/                    ← boletines generados (.txt)
├── audios/                       ← audios generados (.mp3, .vtt)
├── imagenes/                     ← imágenes descargadas de Pexels
└── videos/                       ← vídeos finales (.mp4)
```

---
## Instalación

### Requisitos previos
- Python 3.10+
- [ImageMagick](https://imagemagick.org/script/download.php#windows) (Windows: marcar "Install legacy utilities")
- [ffmpeg](https://ffmpeg.org/) instalado y en el PATH

### Instalar dependencias

```bash
pip install feedparser trafilatura google-generativeai
pip install edge-tts nest-asyncio openai-whisper
pip install moviepy==1.0.3 Pillow numpy
pip install requests python-dateutil
```
## APIs necesarias

| [Google AI Studio](https://aistudio.google.com) | Gemini 2.5 Flash (resumen) | 1.500 req/día |
| [Pexels](https://www.pexels.com/api/) | Imágenes por tema | 200 req/hora |

---
## Uso

Abrir `Proyecto_DeepLearning.ipynb` y ejecutar las celdas en orden:

```python
# Paso 1 — Recopilar noticias
articulos = get_all_news(num_per_source=3, periodo="dia")

# Paso 2 — Generar resumen neutral
boletin_final, resumenes = resumir_noticias(articulos, mi_modelo_gemini)

# Paso 3 — Sintetizar voz y subtítulos
ruta_audio, ruta_subtitulos = generar_audio(boletin_final)

# Paso 4 — Generar vídeo
ruta_video = generar_video(ruta_audio, ruta_subtitulos, resumenes, PEXELS_API_KEY)
```

---

## Tecnologías 

| Librería | Uso |
|----------|-----|
| `feedparser` | Lectura de RSS |
| `trafilatura` | Extracción de texto completo |
| `google-generativeai` | Gemini 2.5 Flash |
| `edge-tts` | Síntesis de voz |
| `openai-whisper` | Transcripción y subtítulos |
| `moviepy` | Montaje de vídeo |
| `Pillow` | Renderizado de texto en imágenes |
| `ffmpeg` | Exportación y quemado de subtítulos |

---

## Autores: Fabián Calvo y Florencia Pellegrini

Proyecto desarrollado para la asignatura de Deep Learning — Máster en Ciencia de Datos, Universitat de València.
