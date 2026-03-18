"""
fill_register_odt_nodep.py
--------------------------
Generates a register details ODT document from a registers.json file.
Zero external dependencies -- uses only Python standard library.

Usage:
    python fill_register_odt_nodep.py registers.json output.odt
    python fill_register_odt_nodep.py registers.json output.odt --section 8.2.1
"""

import json
import zipfile
import io
import argparse


def generate_odt(json_path, output_path, section="8.2.1"):
    with open(json_path, "r") as f:
        data = json.load(f)

    module    = data.get("module",       "Register Map")
    base_addr = data.get("base_address", "0x00")
    registers = data.get("registers",   [])

    # ── Build content.xml body ────────────────────────────────────────────────
    body = ""

    # Module heading
    body += f'<text:h text:outline-level="1">{section}  {module}  (Base {base_addr})</text:h>\n'

    for idx, reg in enumerate(registers, start=1):
        name   = reg.get("name",        "")
        offset = reg.get("offset",      "")
        desc   = reg.get("description", "")
        fields = reg.get("fields",      [])

        # Sub-heading
        body += f'<text:h text:outline-level="3">{section}.{idx}  {name}  ({offset})</text:h>\n'

        # Description paragraph
        if desc.strip():
            body += f'<text:p text:style-name="DescPar">{desc}</text:p>\n'

        # Table open
        body += '<table:table table:style-name="RegTable">\n'
        body += '<table:table-column table:style-name="ColBits"/>\n'
        body += '<table:table-column table:style-name="ColDesc"/>\n'
        body += '<table:table-column table:style-name="ColDef"/>\n'
        body += '<table:table-column table:style-name="ColAcc"/>\n'

        # Column header row
        body += '<table:table-row>\n'
        for label in ["Bits", "Description", "Settings/Default value", "Access"]:
            body += (
                f'<table:table-cell table:style-name="CellHdr">\n'
                f'  <text:p text:style-name="CellHdrTxt">{label}</text:p>\n'
                f'</table:table-cell>\n'
            )
        body += '</table:table-row>\n'

        # Field rows
        for field in fields:
            body += '<table:table-row>\n'
            for val in [field.get("bits",        ""),
                        field.get("description", ""),
                        field.get("default",     ""),
                        field.get("access",      "")]:
                body += (
                    f'<table:table-cell table:style-name="CellData">\n'
                    f'  <text:p text:style-name="CellDataTxt">{val}</text:p>\n'
                    f'</table:table-cell>\n'
                )
            body += '</table:table-row>\n'

        body += '</table:table>\n'
        body += '<text:p text:style-name="Spacer"/>\n'

    # ── Full content.xml ──────────────────────────────────────────────────────
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
  xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0">

<office:automatic-styles>

  <!-- Table container -->
  <style:style style:name="RegTable" style:family="table">
    <style:table-properties style:width="16cm" table:align="left" fo:margin-bottom="10pt"/>
  </style:style>

  <!-- Column widths -->
  <style:style style:name="ColBits" style:family="table-column">
    <style:table-column-properties style:column-width="2.2cm"/>
  </style:style>
  <style:style style:name="ColDesc" style:family="table-column">
    <style:table-column-properties style:column-width="8.0cm"/>
  </style:style>
  <style:style style:name="ColDef" style:family="table-column">
    <style:table-column-properties style:column-width="4.0cm"/>
  </style:style>
  <style:style style:name="ColAcc" style:family="table-column">
    <style:table-column-properties style:column-width="1.8cm"/>
  </style:style>

  <!-- Cell styles -->
  <style:style style:name="CellHdr" style:family="table-cell">
    <style:table-cell-properties
      fo:background-color="#BDD7EE"
      fo:border="0.05pt solid #000000"
      fo:padding="0.10cm"/>
  </style:style>
  <style:style style:name="CellData" style:family="table-cell">
    <style:table-cell-properties
      fo:background-color="#FFFFFF"
      fo:border="0.05pt solid #000000"
      fo:padding="0.10cm"/>
  </style:style>

  <!-- Paragraph styles inside cells -->
  <style:style style:name="CellHdrTxt" style:family="paragraph">
    <style:text-properties
      fo:font-size="9pt"
      fo:font-weight="bold"
      fo:font-family="Arial"/>
  </style:style>
  <style:style style:name="CellDataTxt" style:family="paragraph">
    <style:text-properties
      fo:font-size="9pt"
      fo:font-family="Arial"/>
  </style:style>

  <!-- Description paragraph below sub-heading -->
  <style:style style:name="DescPar" style:family="paragraph">
    <style:text-properties
      fo:font-size="10pt"
      fo:font-style="italic"
      fo:font-family="Arial"/>
    <style:paragraph-properties
      fo:margin-top="2pt"
      fo:margin-bottom="6pt"/>
  </style:style>

  <!-- Small spacer between registers -->
  <style:style style:name="Spacer" style:family="paragraph">
    <style:text-properties fo:font-size="4pt"/>
  </style:style>

</office:automatic-styles>

<office:body>
<office:text>
{body}
</office:text>
</office:body>
</office:document-content>'''

    # ── Manifest ──────────────────────────────────────────────────────────────
    manifest = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
  <manifest:file-entry manifest:media-type="application/vnd.oasis.opendocument.text" manifest:full-path="/"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="content.xml"/>
</manifest:manifest>'''

    # ── Pack into ODT (ZIP) ───────────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype MUST be first and uncompressed per ODF spec
        zf.writestr(zipfile.ZipInfo("mimetype"),
                    "application/vnd.oasis.opendocument.text")
        zf.writestr("content.xml",           content.encode("utf-8"))
        zf.writestr("META-INF/manifest.xml", manifest.encode("utf-8"))

    with open(output_path, "wb") as f:
        f.write(buf.getvalue())

    print(f"[OK]  {output_path}  ->  {len(registers)} register(s) written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate register ODT from JSON -- no dependencies required"
    )
    parser.add_argument("json_file",   help="Path to registers.json")
    parser.add_argument("output_file", help="Path for output .odt")
    parser.add_argument("--section",   default="8.2.1",
                        help="Section prefix e.g. 8.2.1  (default: 8.2.1)")
    args = parser.parse_args()
    generate_odt(args.json_file, args.output_file, args.section)
