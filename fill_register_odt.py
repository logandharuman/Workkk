"""
fill_register_odt.py
--------------------
Generates a register details ODT document from a registers.json file.
Matches the standard template format:
  - Section heading  (module name + base address)
  - Per register: numbered sub-heading + italic description paragraph + table
    Table layout: [Bits | Description | Settings/Default value | Access]

Usage:
    python fill_register_odt.py registers.json output.odt
    python fill_register_odt.py registers.json output.odt --section 8.2.1

Install dependency (once, on the server):
    pip install odfpy
"""

import json
import sys
import argparse

from odf.opendocument import OpenDocumentText
from odf.style import (Style, TextProperties, ParagraphProperties,
                       TableColumnProperties, TableCellProperties,
                       TableProperties)
from odf.text import H, P
from odf.table import Table, TableColumn, TableRow, TableCell


# Colour palette
HEADER_BG = "#BDD7EE"
WHITE_BG  = "#FFFFFF"
BORDER    = "0.05pt solid #000000"


def make_styles(doc):
    s = Style(name="RegH1", family="paragraph")
    s.addElement(TextProperties(fontsize="13pt", fontweight="bold", fontfamily="Arial"))
    s.addElement(ParagraphProperties(margintop="8pt", marginbottom="4pt"))
    doc.automaticstyles.addElement(s)

    s = Style(name="RegH3", family="paragraph")
    s.addElement(TextProperties(fontsize="11pt", fontweight="bold", fontfamily="Arial"))
    s.addElement(ParagraphProperties(margintop="8pt", marginbottom="2pt"))
    doc.automaticstyles.addElement(s)

    s = Style(name="RegDesc", family="paragraph")
    s.addElement(TextProperties(fontsize="10pt", fontstyle="italic", fontfamily="Arial"))
    s.addElement(ParagraphProperties(margintop="2pt", marginbottom="6pt"))
    doc.automaticstyles.addElement(s)

    s = Style(name="RegTable", family="table")
    s.addElement(TableProperties(width="16cm", align="left"))
    doc.automaticstyles.addElement(s)

    for cname, cwidth in [("ColBits","2.2cm"),("ColDesc","8.0cm"),
                           ("ColDef","4.0cm"),("ColAcc","1.8cm")]:
        s = Style(name=cname, family="table-column")
        s.addElement(TableColumnProperties(columnwidth=cwidth))
        doc.automaticstyles.addElement(s)

    s = Style(name="CellHdr", family="table-cell")
    s.addElement(TableCellProperties(backgroundcolor=HEADER_BG, border=BORDER, padding="0.10cm"))
    doc.automaticstyles.addElement(s)

    s = Style(name="CellHdrTxt", family="paragraph")
    s.addElement(TextProperties(fontsize="9pt", fontweight="bold", fontfamily="Arial"))
    doc.automaticstyles.addElement(s)

    s = Style(name="CellData", family="table-cell")
    s.addElement(TableCellProperties(backgroundcolor=WHITE_BG, border=BORDER, padding="0.10cm"))
    doc.automaticstyles.addElement(s)

    s = Style(name="CellDataTxt", family="paragraph")
    s.addElement(TextProperties(fontsize="9pt", fontfamily="Arial"))
    doc.automaticstyles.addElement(s)

    s = Style(name="Spacer", family="paragraph")
    s.addElement(TextProperties(fontsize="4pt"))
    doc.automaticstyles.addElement(s)


def add_cell(row, text, cell_style, text_style):
    cell = TableCell(stylename=cell_style)
    p = P(stylename=text_style)
    p.addText(str(text))
    cell.addElement(p)
    row.addElement(cell)


def build_register_block(doc, reg_index, reg, section_prefix):
    offset = reg.get("offset", "0x??")
    name   = reg.get("name",   "Unknown Register")
    desc   = reg.get("description", "")
    fields = reg.get("fields", [])

    h = H(outlinelevel=3, stylename="RegH3")
    h.addText(f"{section_prefix}.{reg_index}  {name}  ({offset})")
    doc.text.addElement(h)

    if desc.strip():
        dp = P(stylename="RegDesc")
        dp.addText(desc)
        doc.text.addElement(dp)

    table = Table(stylename="RegTable")
    for col_style in ["ColBits", "ColDesc", "ColDef", "ColAcc"]:
        table.addElement(TableColumn(stylename=col_style))

    hdr = TableRow()
    for label in ["Bits", "Description", "Settings/Default value", "Access"]:
        add_cell(hdr, label, "CellHdr", "CellHdrTxt")
    table.addElement(hdr)

    for field in fields:
        frow = TableRow()
        add_cell(frow, field.get("bits",        ""), "CellData", "CellDataTxt")
        add_cell(frow, field.get("description", ""), "CellData", "CellDataTxt")
        add_cell(frow, field.get("default",     ""), "CellData", "CellDataTxt")
        add_cell(frow, field.get("access",      ""), "CellData", "CellDataTxt")
        table.addElement(frow)

    doc.text.addElement(table)
    doc.text.addElement(P(stylename="Spacer"))


def generate_odt(json_path, output_path, section_prefix):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc = OpenDocumentText()
    make_styles(doc)

    module    = data.get("module",       "Register Map")
    base_addr = data.get("base_address", "0x00")
    registers = data.get("registers",   [])

    h1 = H(outlinelevel=1, stylename="RegH1")
    h1.addText(f"{section_prefix}  {module}  (Base {base_addr})")
    doc.text.addElement(h1)

    for idx, reg in enumerate(registers, start=1):
        build_register_block(doc, idx, reg, section_prefix)

    doc.save(output_path)
    print(f"[OK]  {output_path}  ->  {len(registers)} register(s) written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate register ODT from JSON")
    parser.add_argument("json_file")
    parser.add_argument("output_file")
    parser.add_argument("--section", default="8.2.1")
    args = parser.parse_args()
    generate_odt(args.json_file, args.output_file, args.section)
