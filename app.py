from flask import Flask, request, send_file
import os
import fitz  # PyMuPDF
import difflib
from io import BytesIO

app = Flask(__name__)

# Define the route to handle the PDF comparison
@app.route('/compare_pdfs', methods=['POST'])
def compare_pdfs():
    # Check if files were uploaded
    if 'pdf1' not in request.files or 'pdf2' not in request.files:
        return {'error': 'Please upload two PDF files.'}, 400

    # Retrieve the uploaded PDF files
    pdf1 = request.files['pdf1']
    pdf2 = request.files['pdf2']

    # Open the PDF files using PyMuPDF (fitz)
    doc1 = fitz.open(stream=pdf1.read(), filetype='pdf')
    doc2 = fitz.open(stream=pdf2.read(), filetype='pdf')

    # Create a new PDF document for output
    output_doc = fitz.open()

    # Determine the number of pages to process
    num_pages = max(len(doc1), len(doc2))

    # Iterate over the pages
    for page_num in range(num_pages):
        # Get pages from both documents, if available
        page1 = doc1[page_num] if page_num < len(doc1) else None
        page2 = doc2[page_num] if page_num < len(doc2) else None

        # Set the dimensions for the new page
        if page1 and page2:
            rect = page1.rect
        elif page1:
            rect = page1.rect
        elif page2:
            rect = page2.rect
        else:
            continue  # Skip if no pages are available

        # Create a new page with the combined width
        new_width = rect.width * 2
        new_height = rect.height
        new_page = output_doc.new_page(width=new_width, height=new_height)

        # Place page1 on the left side
        if page1:
            new_page.show_pdf_page(fitz.Rect(0, 0, rect.width, rect.height), doc1, page_num)

        # Place page2 on the right side
        if page2:
            new_page.show_pdf_page(fitz.Rect(rect.width, 0, new_width, rect.height), doc2, page_num)

        # Draw a vertical line in the middle
        shape = new_page.new_shape()
        shape.draw_line(fitz.Point(rect.width, 0), fitz.Point(rect.width, new_height))
        shape.finish(color=(0, 0, 0), width=1)
        shape.commit()

        # **Overlay blue color if the page is new in pdf2**
        if page1 is None and page2 is not None:
            # Create a semi-transparent blue rectangle over the right side
            blue_rect = fitz.Rect(rect.width, 0, new_width, new_height)
            shape = new_page.new_shape()
            shape.draw_rect(blue_rect)
            shape.finish(color=None, fill=(0, 0, 1), fill_opacity=0.3)  # Blue color with 30% opacity
            shape.commit()
            # Skip further processing since there's no page1 to compare
            continue

        if page1 and page2:
            # Extract words from both pages
            words1 = page1.get_text("words")
            words2 = page2.get_text("words")

            # Use difflib to compare word sequences
            word_texts1 = [w[4] for w in words1]
            word_texts2 = [w[4] for w in words2]

            matcher = difflib.SequenceMatcher(None, word_texts1, word_texts2)
            opcodes = matcher.get_opcodes()

            # Highlight text differences
            for tag, i1, i2, j1, j2 in opcodes:
                if tag == 'equal':
                    continue
                elif tag in ('delete', 'replace'):
                    for idx in range(i1, i2):
                        x0, y0, x1, y1 = words1[idx][:4]
                        highlight = fitz.Rect(x0, y0, x1, y1)
                        shape = new_page.new_shape()
                        shape.draw_rect(highlight)
                        shape.finish(color=None, fill=(1, 0, 0), fill_opacity=0.3)
                        shape.commit()

                if tag in ('insert', 'replace'):
                    for idx in range(j1, j2):
                        x0, y0, x1, y1 = words2[idx][:4]
                        x0 += rect.width
                        x1 += rect.width
                        highlight = fitz.Rect(x0, y0, x1, y1)
                        shape = new_page.new_shape()
                        shape.draw_rect(highlight)
                        shape.finish(color=None, fill=(0, 1, 0), fill_opacity=0.3)
                        shape.commit()

            # Compare and highlight image differences
            images1 = page1.get_images(full=True)
            images2 = page2.get_images(full=True)
            image_refs1 = {img[0]: img for img in images1}
            image_refs2 = {img[0]: img for img in images2}

            for img_ref in image_refs1:
                if img_ref not in image_refs2:
                    img_info = image_refs1[img_ref]
                    x0, y0, x1, y1 = page1.get_image_bbox(img_info)
                    highlight = fitz.Rect(x0, y0, x1, y1)
                    shape = new_page.new_shape()
                    shape.draw_rect(highlight)
                    shape.finish(color=None, fill=(1, 0, 0), fill_opacity=0.3)
                    shape.commit()

            for img_ref in image_refs2:
                if img_ref not in image_refs1:
                    img_info = image_refs2[img_ref]
                    x0, y0, x1, y1 = page2.get_image_bbox(img_info)
                    x0 += rect.width
                    x1 += rect.width
                    highlight = fitz.Rect(x0, y0, x1, y1)
                    shape = new_page.new_shape()
                    shape.draw_rect(highlight)
                    shape.finish(color=None, fill=(0, 1, 0), fill_opacity=0.3)
                    shape.commit()

    # Save the output PDF to a byte stream
    output_stream = BytesIO()
    output_doc.save(output_stream)
    output_stream.seek(0)

    # Return the output PDF as a file download
    return send_file(output_stream, as_attachment=True, download_name='diff_output.pdf', mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True,port=8080)