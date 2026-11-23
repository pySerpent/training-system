"""Выгрузка протоколов тестирования в Word (.docx) и Excel (.xlsx)."""
import os
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from . import journal, settings, testing

COLUMNS = [("user", "Сотрудник"), ("department", "Подразделение"),
           ("course", "Курс"), ("date", "Дата"), ("score", "Баллы"),
           ("percent", "Процент"), ("status", "Итог"), ("comment", "Комментарий")]


def default_name(ext: str) -> str:
    """Имя файла по умолчанию с датой и временем."""
    return f"protokol_{datetime.now():%Y%m%d_%H%M}.{ext}"


def _title(rows: list) -> str:
    return (f"Протокол тестирования сотрудников по информационной безопасности "
            f"({len(rows)} попыт.)")


def export_docx(rows: list, path: str, actor_id: int,
                with_details: bool = False) -> str:
    """Формирует протокол в формате Word."""
    company = settings.get("company_name")
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name, style.font.size = "Times New Roman", Pt(12)
    head = doc.add_paragraph(company)
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title = doc.add_paragraph(_title(rows))
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True
    doc.add_paragraph(f"Дата формирования: {datetime.now():%d.%m.%Y %H:%M}")
    table = doc.add_table(rows=1, cols=len(COLUMNS))
    table.style = "Table Grid"
    for cell, (_key, caption) in zip(table.rows[0].cells, COLUMNS):
        cell.text = caption
        cell.paragraphs[0].runs[0].bold = True
    for row in rows:
        cells = table.add_row().cells
        for cell, (key, _caption) in zip(cells, COLUMNS):
            cell.text = str(row[key])
    passed = sum(1 for r in rows if r["status"] == "Сдан")
    doc.add_paragraph()
    doc.add_paragraph(f"Всего попыток: {len(rows)}; сдано: {passed}; "
                      f"не сдано: {len(rows) - passed}")
    if with_details:
        # подробные ответы по каждой попытке
        for row in rows:
            doc.add_paragraph(f"{row['user']}, «{row['course']}», {row['date']}",
                              style="Heading 3")
            for i, item in enumerate(testing.test_details(row["id"]), 1):
                mark = "верно" if item["ok"] else "неверно"
                doc.add_paragraph(f"{i}. {item['question']} Ответ: "
                                  f"{'; '.join(item['chosen']) or 'нет ответа'} "
                                  f"({mark})")
    doc.add_paragraph()
    doc.add_paragraph("Ответственный за обучение ____________ /____________/")
    doc.save(path)
    journal.write("export", f"docx {os.path.basename(path)}", actor_id)
    return path


def export_xlsx(rows: list, path: str, actor_id: int) -> str:
    """Формирует протокол в формате Excel с итоговой строкой."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Протокол"
    ws.append([_title(rows)])
    ws["A1"].font = Font(bold=True, size=12)
    ws.append([f"{settings.get('company_name')}, сформирован "
               f"{datetime.now():%d.%m.%Y %H:%M}"])
    ws.append([caption for _key, caption in COLUMNS])
    thin = Side(style="thin")
    for row in rows:
        ws.append([row[key] for key, _caption in COLUMNS])
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row):
        for cell in row:
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for cell in ws[3]:
        cell.font = Font(bold=True)
    widths = [32, 24, 34, 17, 12, 10, 10, 30]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    if rows:
        last = ws.max_row
        ws.append(["Средний процент", "", "", "", "",
                   f"=ROUND(AVERAGE(F4:F{last}),1)"])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.freeze_panes = "A4"
    wb.save(path)
    journal.write("export", f"xlsx {os.path.basename(path)}", actor_id)
    return path
