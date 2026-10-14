"""Render every manuscript page for visual inspection."""
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageDraw


def main():
    output = Path("tmp/pdfs/current_paper_review")
    output.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument("output/pdf/xai_ids_ieee_paper.pdf")
    thumbs = []
    for index in range(len(document)):
        page = document[index]
        bitmap = page.render(scale=1.8)
        image = bitmap.to_pil().copy()
        image.save(output / f"page-{index + 1}.png")
        thumbnail = ImageOps.contain(image, (540, 720))
        panel = Image.new("RGB", (560, 750), "#e8e8e8")
        panel.paste(thumbnail, ((560 - thumbnail.width) // 2, 20))
        ImageDraw.Draw(panel).text((12, 730), f"Page {index + 1}", fill="black")
        thumbs.append(panel)
        bitmap.close()
        page.close()
    grid = Image.new("RGB", (1120, 750 * ((len(thumbs) + 1) // 2)), "white")
    for index, panel in enumerate(thumbs):
        grid.paste(panel, ((index % 2) * 560, (index // 2) * 750))
    grid.save(output / "contact-sheet.png")
    document.close()
    print(f"Rendered {len(thumbs)} pages to {output.resolve()}")


if __name__ == "__main__":
    main()
