import google.generativeai as genai
import json
import os
from datetime import datetime, time


# ─────────────────────────────────────────
# PASO A — AGRUPAR POR TEMAS
# ─────────────────────────────────────────

def agrupar_por_temas(lista_articulos, modelo_ia):
    """
    Le pide a Gemini que agrupe los artículos por tema.
    Devuelve una lista de grupos, cada uno con su tema y artículos.
    """
    print("\n-> Agrupando artículos por temas...")

    # Preparamos un listado numerado para que Gemini pueda referenciarlos
    listado = ""
    for i, art in enumerate(lista_articulos):
        listado += f"{i}: [{art['fuente']}] {art['titulo']}\n"

    prompt = f"""
    Tienes esta lista de titulares de noticias numerados del 0 al {len(lista_articulos)-1}:

    {listado}

    Agrupa estos titulares por tema. Noticias que hablen del mismo asunto 
    o estén claramente relacionadas deben ir en el mismo grupo.
    Descarta grupos con un solo artículo salvo que sea un tema muy relevante.

    Responde ÚNICAMENTE con un JSON válido con este formato exacto, 
    sin texto adicional, sin bloques de código, sin explicaciones:
    [
        {{
            "tema": "Nombre del tema",
            "indices": [0, 3, 7]
        }},
        {{
            "tema": "Nombre del otro tema",
            "indices": [1, 5]
        }}
    ]
    """

    try:
        respuesta = modelo_ia.generate_content(prompt)
        texto     = respuesta.text.strip()

        # Limpiamos por si Gemini añade bloques de código
        texto = texto.replace("```json", "").replace("```", "").strip()

        grupos_indices = json.loads(texto)

        # Construimos los grupos con los artículos completos
        grupos = []
        for grupo in grupos_indices:
            articulos_grupo = [lista_articulos[i] for i in grupo["indices"]
                               if i < len(lista_articulos)]
            if articulos_grupo:
                grupos.append({
                    "tema":      grupo["tema"],
                    "articulos": articulos_grupo
                })

        print(f"   {len(grupos)} temas identificados:")
        for g in grupos:
            fuentes = [a["fuente"] for a in g["articulos"]]
            print(f"   - {g['tema']} ({len(g['articulos'])} fuentes: {', '.join(fuentes)})")

        return grupos

    except Exception as e:
        print(f"   Error agrupando temas: {e}")
        return None


# ─────────────────────────────────────────
# PASO B — RESUMIR POR TEMAS
# ─────────────────────────────────────────

def resumir_grupos(grupos, modelo_ia):
    """
    Por cada grupo temático genera un resumen neutral
    contrastando las distintas fuentes.
    Devuelve el boletín final como texto.
    """
    print("\n-> Generando resúmenes por tema...")
    resumenes = []

    for i, grupo in enumerate(grupos):
        tema      = grupo["tema"]
        articulos = grupo["articulos"]
        print(f"   [{i+1}/{len(grupos)}] {tema} ({len(articulos)} fuentes)...")

        bloque = ""
        for art in articulos:
            bloque += f"FUENTE: {art['fuente']}\n"
            bloque += f"TÍTULO: {art['titulo']}\n"
            bloque += f"TEXTO:  {art['texto_completo'][:1500]}\n\n"

        prompt = f"""
        Actúa como un periodista riguroso y neutral. Comienza el boletin saludado y dando la bienvenida a la plataforma "Al Dia".
        A continuación tienes {len(articulos)} fuentes distintas que cubren el mismo tema: "{tema}".
        {bloque}
        Redacta un párrafo informativo de 4-6 frases que:
        1. Explique claramente qué ha ocurrido
        2. Contraste los distintos enfoques o datos que aporta cada fuente
        3. Use únicamente hechos verificables, sin adjetivos valorativos
        4. Mencione las fuentes de forma natural
        5. Sea comprensible para alguien que no sabe nada del tema
        Escribe directamente el párrafo, sin títulos ni introducciones.
        """

        exito    = False
        intentos = 0

        while not exito and intentos < 3:
            try:
                respuesta = modelo_ia.generate_content(prompt)
                resumenes.append({
                    "tema":    tema,
                    "resumen": respuesta.text.strip(),
                    "fuentes": list(dict.fromkeys([a["fuente"] for a in articulos]))
                })
                print(f"      OK ({len(respuesta.text)} chars)")
                exito = True
                time.sleep(4)  # espera entre llamadas para no superar cuota

            except Exception as e:
                intentos += 1
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    espera = 60
                    print(f"      Límite de cuota, esperando {espera}s (intento {intentos}/3)...")
                    time.sleep(espera)
                else:
                    print(f"      Error: {e}")
                    break

        if not exito:
            print(f"      Saltando tema '{tema}' tras 3 intentos fallidos")

    return resumenes


# ─────────────────────────────────────────
# PASO C — MONTAR EL BOLETÍN
# ─────────────────────────────────────────

def montar_boletin(resumenes, modelo_ia):
    """
    Une todos los resúmenes en un boletín fluido con transiciones
    naturales estilo presentador de noticias.
    """
    print("\n-> Montando boletín final...")

    bloques = ""
    for i, r in enumerate(resumenes):
        bloques += f"TEMA {i+1}: {r['tema']}\n{r['resumen']}\n\n"

    prompt = f"""
    Eres un presentador de noticias profesional de "Al Dia".
    
    A continuación tienes {len(resumenes)} bloques informativos.
    Únelos en un único texto continuo añadiendo:
    - Una introducción breve al inicio
    - Transiciones naturales entre temas ("En otro orden de cosas...", 
      "Cambiando de tema...", "En el plano económico...", etc.)
    - Un cierre breve al final
    
    Mantén toda la información de cada bloque, no la recortes.
    Escribe directamente el texto del boletín sin etiquetas ni títulos.
    
    BLOQUES:
    {bloques}
    """

    try:
        respuesta = modelo_ia.generate_content(prompt)
        return respuesta.text.strip()
    except Exception as e:
        # Si falla el montaje, devolvemos los bloques concatenados directamente
        print(f"   Error montando boletín, concatenando directamente: {e}")
        return "\n\n".join([f"{r['tema']}:\n{r['resumen']}" for r in resumenes])


# ─────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────

def resumir_noticias(lista_articulos, modelo_ia):
    """
    Pipeline completo:
    1. Agrupa artículos por tema
    2. Resume cada tema contrastando fuentes
    3. Monta el boletín final con transiciones
    """
    print("\n" + "="*50)
    print(f"RESUMIENDO {len(lista_articulos)} ARTÍCULOS")
    print("="*50)

    # Paso A
    grupos = agrupar_por_temas(lista_articulos, modelo_ia)
    if not grupos:
        print("Error agrupando, abortando.")
        return None

    # Paso B
    resumenes = resumir_grupos(grupos, modelo_ia)
    if not resumenes:
        print("Error resumiendo, abortando.")
        return None

    # Paso C
    boletin = montar_boletin(resumenes, modelo_ia)

    print(f"\nBoletín generado: {len(boletin)} chars, {len(resumenes)} temas")
    return boletin, resumenes


def guardar_boletin(texto_boletin, carpeta="boletines"):
    os.makedirs(carpeta, exist_ok=True)
    timestamp      = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"{carpeta}/boletin_{timestamp}.txt"

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(f"BOLETÍN DE NOTICIAS\n")
        f.write(f"Generado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(texto_boletin)

    print(f"Boletín guardado en: {nombre_archivo}")
    return nombre_archivo

def generar_query_imagen(tema, modelo_ia):
    """
    Usa Gemini para generar una query en inglés optimizada
    para buscar una imagen fotográfica impactante en Pexels.
    """
    try:
        prompt = f"""Dame 2 palabras en inglés para buscar en Pexels una fotografía 
        RELACIONADA, periodística e impactante que represente este tema de noticias: '{tema}'.
        Responde SOLO con las palabras, sin explicación ni puntuación."""
        
        respuesta = modelo_ia.generate_content(prompt)
        query     = respuesta.text.strip()
        print(f"    Query imagen: '{query}'")
        return query
    except Exception:
        return tema  # fallback al tema original