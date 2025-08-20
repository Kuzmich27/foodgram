from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def render_shopping_list_pdf(ingredients):
    """
    Генерация PDF-файла со списком покупок.
    ingredients — queryset с аннотацией total_amount, например:
    [
        {"ingredient__name": "Соль", "ingredient__measurement_unit": "г", "total_amount": 5},
        {"ingredient__name": "Мука", "ingredient__measurement_unit": "кг", "total_amount": 1},
    ]
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 14)

    y = 800
    p.drawString(100, y, "Список покупок:")
    y -= 30

    for ing in ingredients:
        line = f"{ing['ingredient__name']} ({ing['ingredient__measurement_unit']}) — {ing['total_amount']}"
        p.drawString(100, y, line)
        y -= 20
        if y < 50:  # Переход на новую страницу
            p.showPage()
            p.setFont("Helvetica", 14)
            y = 800

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
