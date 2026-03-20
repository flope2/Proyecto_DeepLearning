import feedparser
import trafilatura
import google.generativeai as genai

FUENTES_ABIERTAS = {
    "ABC":           "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml",
    "ElDiario":      "https://www.eldiario.es/rss/",
    "Europa Press":  "https://www.europapress.es/rss/rss.aspx",
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "20minutos":     "https://www.20minutos.es/rss/",
    "Antena 3":      "https://news.google.com/rss/search?q=site:antena3.com&hl=es&gl=ES&ceid=ES:es",
    "RTVE":          "https://news.google.com/rss/search?q=site:rtve.es&hl=es&gl=ES&ceid=ES:es",
}

FUENTES_PAYWALL = {
    "El Pais":  "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"
}

TODAS_LAS_FUENTES = {
    **{k: {"url": v, "tipo": "abierta"}  for k, v in FUENTES_ABIERTAS.items()},
    **{k: {"url": v, "tipo": "paywall"}  for k, v in FUENTES_PAYWALL.items()}
}


def fetch_rss(source_name, feed_config, num_articles=5):
    try:
        feed = feedparser.parse(feed_config["url"])
        articles = []
        for entry in feed.entries[:num_articles]:
            articles.append({
                "titulo":      entry.get("title", "").strip(),
                "descripcion": entry.get("summary", "").strip(),
                "url":         entry.get("link", ""),
                "fuente":      source_name,
                "tipo_fuente": feed_config["tipo"],
                "fecha":       entry.get("published", "")
            })
        print(f"  [{source_name}] {len(articles)} articulos en RSS")
        return articles
    except Exception as e:
        print(f"  [{source_name}] Error en RSS: {e}")
        return []


def extract_full_text(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False
        )
        if text and len(text) > 200:
            return text
        return None
    except Exception:
        return None


def process_article(article):
    print(f"  Procesando: {article['titulo'][:55]}...")
    full_text = extract_full_text(article["url"])

    if full_text:
        article["texto_completo"] = full_text
        article["texto_origen"]   = "completo"
        print(f"    -> Texto completo ({len(full_text)} chars)")
    else:
        fallback = f"{article['titulo']}. {article['descripcion']}"
        article["texto_completo"] = fallback
        article["texto_origen"]   = "resumen_rss"
        if article["tipo_fuente"] == "paywall":
            print(f"    -> Articulo de pago, usando resumen RSS ({len(fallback)} chars)")
        else:
            print(f"    -> Scraping fallido, usando resumen RSS ({len(fallback)} chars)")
    return article


def get_all_news(num_per_source=4):
    print("=" * 50)
    print("RECOPILANDO NOTICIAS")
    print("=" * 50)

    all_articles = []

    print("\n-> Leyendo RSS de todas las fuentes...")
    for source_name, feed_config in TODAS_LAS_FUENTES.items():
        articles = fetch_rss(source_name, feed_config, num_per_source)
        all_articles.extend(articles)

    print(f"\n-> Extrayendo texto completo ({len(all_articles)} articulos)...")
    all_articles = [process_article(a) for a in all_articles]

    completos = sum(1 for a in all_articles if a["texto_origen"] == "completo")
    resumenes = sum(1 for a in all_articles if a["texto_origen"] == "resumen_rss")

    print("\n" + "=" * 50)
    print(f"RESULTADO FINAL")
    print(f"  Total articulos:  {len(all_articles)}")
    print(f"  Texto completo:   {completos}")
    print(f"  Resumen RSS:      {resumenes}")
    print("=" * 50)

    return all_articles

def resumir_noticias(lista_articulos, modelo_ia):
    print("\n" + "="*50)
    print("INICIANDO RESUMEN CON Gemini")
    print("="*50)

    for i, art in enumerate(lista_articulos):
        print(f"\nProcesando artículo {i+1}/{len(lista_articulos)}: {art['titulo'][:50]}...")
        
        prompt = f"""
        Actúa como un periodista analítico y neutral. Haz un resumen breve, directo y totalmente objetivo de la siguiente noticia.
        Título: {art['titulo']}
        Fuente: {art['fuente']}
        Texto: {art['texto_completo']}
        """

        try:
            respuesta = modelo_ia.generate_content(prompt)
            art["resumen_ia"] = respuesta.text
            print(f"Resumen completado.")
        except Exception as e:
            print(f"Error al procesar con la IA: {e}")
            art["resumen_ia"] = "Error al generar el resumen con IA."

    return lista_articulos