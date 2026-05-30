import os
import fitz

def clean_pdf_file(input_path, output_path, log_callback=None):
    """
    Surgically cleans Wuolah advertisements, watermarks, borders, and promotional text from a PDF.
    Also rescales the content of border-containing pages back to 100% scale ("que se coma la esquina")
    to ensure perfect visual dimensions and uniform page margins.
    
    :param input_path: Path to the input PDF file.
    :param output_path: Path to save the cleaned PDF file.
    :param log_callback: Optional function that accepts a string to stream logs in real-time.
    """
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)

    filename = os.path.basename(input_path)
    log(f"[INFO] Iniciando limpieza de alta precisión de: {filename}")
    
    try:
        src_doc = fitz.open(input_path)
    except Exception as e:
        log(f"[ERROR] No se pudo abrir el archivo PDF: {str(e)}")
        raise e
        
    initial_page_count = len(src_doc)
    log(f"[INFO] Páginas originales: {initial_page_count}")
    
    pages_to_keep = []
    
    # 1. Identify which pages to keep
    # Always delete first page (index 0)
    for i in range(initial_page_count):
        if i == 0:
            log(f"[AD] Página 1 identificada como portada promocional de Wuolah. Marcada para eliminación.")
            continue
            
        page = src_doc[i]
        text = page.get_text().strip()
        images = page.get_images()
        
        # If very little text (e.g. < 15 characters) and contains images, it is an ad page
        if len(text) < 15 and len(images) >= 1:
            log(f"[AD] Página {i + 1} identificada como anuncio a pantalla completa (texto mínimo: '{text}', imágenes: {len(images)}). Marcada para eliminación.")
            continue
            
        pages_to_keep.append(i)
        
    deleted_count = initial_page_count - len(pages_to_keep)
    log(f"[INFO] Páginas marcadas para eliminar: {deleted_count}. Páginas útiles: {len(pages_to_keep)}")
    
    # Create temporary doc to apply redactions first
    temp_doc = fitz.open()
    border_flags = []
    
    borders_removed = 0
    watermarks_removed = 0
    texts_redacted = 0
    
    # 2. Process useful pages, copy to temp_doc, and apply redaction masks
    for idx, original_p_idx in enumerate(pages_to_keep):
        src_page = src_doc[original_p_idx]
        width = src_page.rect.width
        height = src_page.rect.height
        
        temp_page = temp_doc.new_page(width=width, height=height)
        temp_page.show_pdf_page(fitz.Rect(0, 0, width, height), src_doc, original_p_idx)
        
        # Check if the page has borders/banners
        has_left_border = False
        has_top_border = False
        
        image_list = src_page.get_images(full=True)
        for img in image_list:
            xref = img[0]
            rects = src_page.get_image_rects(xref)
            for r in rects:
                # Left border banner: very close to left edge, width ~70pt, height > 500pt
                if r.x0 < 10 and r.x1 > 50 and r.height > 500:
                    has_left_border = True
                # Top header banner: very close to top edge, height ~100pt, width > 400pt
                if r.y0 < 10 and r.y1 > 80 and r.width > 400:
                    has_top_border = True
                    
        # Apply border/margin redactions on temp page if detected
        if has_left_border or has_top_border:
            log(f"[BORDER] Banners/Bordes detectados en pág. original {original_p_idx + 1}. Marcando para redacción de márgenes.")
            # Redact top header area
            temp_page.add_redact_annot(fitz.Rect(0, 0, width, 110))
            # Redact left sidebar area
            temp_page.add_redact_annot(fitz.Rect(0, 0, 80, height))
            
            border_flags.append(True)
            borders_removed += 1
        else:
            border_flags.append(False)
            
            # STRICT MARGIN SAFEGUARDS FOR STANDARD PAGES
            # Redact the narrow right edge (where vertical right-rotated texts live)
            temp_page.add_redact_annot(fitz.Rect(578, 0, width, height))
            # Redact bottom margin (where horizontal bottom rights/coins texts live)
            temp_page.add_redact_annot(fitz.Rect(0, 800, width, height))
            
        # Redact small watermark images (like bottom-right Wuolah logo)
        for img in image_list:
            xref = img[0]
            rects = src_page.get_image_rects(xref)
            for r in rects:
                if r.x0 > 400 and r.y0 > 750 and r.width < 120 and r.height < 40:
                    temp_page.add_redact_annot(r)
                    watermarks_removed += 1
                    
        # Search and redact other ad text queries (to be doubly sure)
        text_queries = [
            "Reservados todos los derechos",
            "No se permite la explotación económica",
            "La transformación de esta obra",
            "Queda permitida la impresión en su totalidad",
            "Las descargas sin publicidad",
            "se realizan con las coins"
        ]
        
        page_texts_redacted = 0
        for query in text_queries:
            matches = temp_page.search_for(query)
            for r in matches:
                padded_rect = fitz.Rect(r.x0 - 2, r.y0 - 2, r.x1 + 2, r.y1 + 2)
                temp_page.add_redact_annot(padded_rect)
                page_texts_redacted += 1
                
        if page_texts_redacted > 0:
            texts_redacted += page_texts_redacted
            
        # Apply the redactions to fully remove ad objects
        temp_page.apply_redactions(images=1, graphics=1)
        temp_page.clean_contents()

    # 3. Create the final document and reconstruct pages with scaling correction
    final_doc = fitz.open()
    
    for idx in range(len(temp_doc)):
        temp_page = temp_doc[idx]
        width = temp_page.rect.width
        height = temp_page.rect.height
        has_borders = border_flags[idx]
        
        final_page = final_doc.new_page(width=width, height=height)
        dest_rect = fitz.Rect(0, 0, width, height)
        
        if has_borders:
            # ASPECT RATIO CORRECTION ("QUE SE COMA LA ESQUINA")
            # We crop the page to bypass the borders, starting at (80, 110)
            clip_rect = fitz.Rect(80, 110, width, height)
            log(f"[INFO] Re-escalando contenido de pág. {idx + 1} para compensar el recorte de márgenes.")
            final_page.show_pdf_page(dest_rect, temp_doc, idx, clip=clip_rect)
        else:
            # For standard pages, copy the entire page at 100% scale
            final_page.show_pdf_page(dest_rect, temp_doc, idx)
            
    # Ensure parent directory of output exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save the final cleaned document with maximum optimization & garbage collection
    log(f"[INFO] Guardando y optimizando el documento final...")
    final_doc.save(output_path, garbage=3, deflate=True)
    
    src_doc.close()
    temp_doc.close()
    final_doc.close()
    
    log(f"[SUCCESS] ¡Limpieza finalizada! Guardado en: {os.path.basename(output_path)}")
    
    return {
        "initial_pages": initial_page_count,
        "cleaned_pages": len(pages_to_keep),
        "deleted_pages": deleted_count,
        "borders_removed": borders_removed,
        "watermarks_removed": watermarks_removed,
        "texts_redacted": texts_redacted
    }
