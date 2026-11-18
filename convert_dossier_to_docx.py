import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

COLOR_EMERALD_DARK = "064E3B"
COLOR_EMERALD = "047857"
COLOR_EMERALD_LIGHT = "059669"
COLOR_SLATE_DARK = "0F172A"
COLOR_SLATE_BODY = "1E293B"
COLOR_SLATE_MUTED = "475569"
COLOR_BG_SOFT = "F8FAFC"
COLOR_BG_CODE = "F1F5F9"
COLOR_BORDER = "CBD5E1"
COLOR_WHITE = "FFFFFF"

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tcPr = cell._tc.get_or_add_tcPr()
    borders_elm = '<w:tcBorders ' + nsdecls("w") + '>'
    for side, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        if val:
            borders_elm += f'<{side} w:val="{val.get("val","single")}" w:sz="{val.get("sz","4")}" w:space="0" w:color="{val.get("color","CBD5E1")}"/>'
        else:
            borders_elm += f'<{side} w:val="none"/>'
    borders_elm += '</w:tcBorders>'
    tcPr.append(parse_xml(borders_elm))

def set_table_borders(table, color="CBD5E1", sz="4"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_formatted_runs(paragraph, text, base_font="Arial", base_size=10, base_color=COLOR_SLATE_BODY, is_bold=False, is_italic=False):
    # Regex for bold-italic (***), bold (**), italic (*), code (`)
    pattern = re.compile(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`)')
    tokens = pattern.split(text)
    
    for token in tokens:
        if not token:
            continue
        run = paragraph.add_run()
        run.font.name = base_font
        run.font.size = Pt(base_size)
        run.font.color.rgb = hex_to_rgb(base_color)
        run.bold = is_bold
        run.italic = is_italic
        
        if token.startswith('***') and token.endswith('***') and len(token) >= 6:
            run.text = token[3:-3]
            run.bold = True
            run.italic = True
        elif token.startswith('**') and token.endswith('**') and len(token) >= 4:
            run.text = token[2:-2]
            run.bold = True
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            run.text = token[1:-1]
            run.italic = True
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            run.text = token[1:-1]
            run.font.name = 'Consolas'
            run.font.size = Pt(base_size * 0.92)
            run.font.color.rgb = hex_to_rgb("0F172A")
            # give code run a light background or subtle styling
        else:
            run.text = token

def create_document_from_md(md_path, docx_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    doc = docx.Document()

    # Set page margins to 2 cm (approx 0.79 in)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.79)
        section.bottom_margin = Inches(0.79)
        section.left_margin = Inches(0.79)
        section.right_margin = Inches(0.79)

    lines = md_text.splitlines()
    i = 0
    in_code_block = False
    code_lines = []
    code_lang = ""
    in_table = False
    table_lines = []

    def flush_table():
        nonlocal table_lines, in_table
        if not table_lines:
            return
        
        # Parse table lines
        parsed_rows = []
        for tl in table_lines:
            # Check if it's separator row
            if re.match(r'^\s*\|?\s*:?-+:?\s*\|', tl):
                continue
            cols = [c.strip() for c in tl.strip().strip('|').split('|')]
            if cols:
                parsed_rows.append(cols)

        if not parsed_rows:
            table_lines = []
            in_table = False
            return

        num_cols = max(len(r) for r in parsed_rows)
        # normalize
        for r in parsed_rows:
            while len(r) < num_cols:
                r.append("")

        table = doc.add_table(rows=len(parsed_rows), cols=num_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(table, color="CBD5E1", sz="4")

        # Set column widths proportionally
        for row_idx, row in enumerate(parsed_rows):
            is_header = (row_idx == 0)
            tr = table.rows[row_idx]._tr
            # cantSplit
            trPr = tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            if is_header:
                trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

            for col_idx, cell_text in enumerate(row):
                cell = table.cell(row_idx, col_idx)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
                
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.1

                if is_header:
                    set_cell_background(cell, COLOR_EMERALD)
                    add_formatted_runs(p, cell_text, base_font="Arial", base_size=9.5, base_color=COLOR_WHITE, is_bold=True)
                else:
                    bg = COLOR_WHITE if row_idx % 2 == 1 else COLOR_BG_SOFT
                    set_cell_background(cell, bg)
                    add_formatted_runs(p, cell_text, base_font="Arial", base_size=9, base_color=COLOR_SLATE_BODY)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        table_lines = []
        in_table = False

    def flush_code():
        nonlocal code_lines, code_lang, in_code_block
        if not code_lines:
            in_code_block = False
            return
        
        full_code = "\n".join(code_lines)
        is_mermaid = "mermaid" in code_lang.lower()

        # Framed box table for code/diagram
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        set_cell_background(cell, COLOR_BG_CODE)
        set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
        
        border_color = COLOR_EMERALD_LIGHT if is_mermaid else COLOR_BORDER
        set_cell_borders(cell, 
            top=dict(val="single", sz="4", color=border_color),
            bottom=dict(val="single", sz="4", color=border_color),
            left=dict(val="single", sz="24" if is_mermaid else "12", color=border_color),
            right=dict(val="single", sz="4", color=border_color)
        )

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        
        # Header banner inside cell
        header_text = f"DIAGRAMME UML (Syntaxe Mermaid)" if is_mermaid else f"CODE / SPÉCIFICATION ({code_lang.upper() if code_lang else 'TEXT'})"
        hrun = p.add_run(header_text + "\n")
        hrun.font.name = "Arial"
        hrun.font.size = Pt(8)
        hrun.font.bold = True
        hrun.font.color.rgb = hex_to_rgb(COLOR_EMERALD_DARK if is_mermaid else COLOR_SLATE_MUTED)

        # Code content
        crun = p.add_run(full_code)
        crun.font.name = "Consolas"
        crun.font.size = Pt(8.5)
        crun.font.color.rgb = hex_to_rgb(COLOR_SLATE_DARK)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        code_lines = []
        code_lang = ""
        in_code_block = False

    while i < len(lines):
        line = lines[i]

        # Check code fence
        if line.strip().startswith('```'):
            if in_table:
                flush_table()
            if in_code_block:
                flush_code()
            else:
                in_code_block = True
                code_lang = line.strip()[3:].strip()
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Check table line
        if line.strip().startswith('|') and line.strip().endswith('|'):
            in_table = True
            table_lines.append(line)
            i += 1
            continue
        elif in_table:
            flush_table()

        # Check Heading 1
        if line.startswith('# '):
            title_text = line[2:].strip()
            # If main doc title
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(4)
            add_formatted_runs(p, title_text, base_font="Arial", base_size=20, base_color=COLOR_EMERALD_DARK, is_bold=True)
            i += 1
            continue

        # Check Heading 2
        if line.startswith('## '):
            h2_text = line[3:].strip()
            # If major section (e.g. 1., 2., 3., 4., 5.), add page break before if not the very first
            if re.match(r'^\d+\.', h2_text) and int(h2_text.split('.')[0]) >= 2:
                doc.add_page_break()
            
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            add_formatted_runs(p, h2_text, base_font="Arial", base_size=14, base_color=COLOR_EMERALD, is_bold=True)
            i += 1
            continue

        # Check Heading 3
        if line.startswith('### '):
            h3_text = line[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            add_formatted_runs(p, h3_text, base_font="Arial", base_size=11.5, base_color=COLOR_SLATE_DARK, is_bold=True)
            i += 1
            continue

        # Check Heading 4
        if line.startswith('#### '):
            h4_text = line[5:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            add_formatted_runs(p, h4_text, base_font="Arial", base_size=10.5, base_color=COLOR_SLATE_MUTED, is_bold=True)
            i += 1
            continue

        # Check Blockquote
        if line.startswith('> '):
            # Gather consecutive blockquote lines
            quote_lines = [line[2:]]
            while i + 1 < len(lines) and lines[i + 1].startswith('> '):
                i += 1
                quote_lines.append(lines[i][2:])
            
            quote_text = "\n".join(quote_lines)
            
            # Styled callout table
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = table.cell(0, 0)
            set_cell_background(cell, COLOR_BG_SOFT)
            set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
            set_cell_borders(cell,
                top=dict(val="none"),
                bottom=dict(val="none"),
                left=dict(val="single", sz="28", color=COLOR_EMERALD_LIGHT),
                right=dict(val="none")
            )
            
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            for q_idx, q_line in enumerate(quote_lines):
                if q_idx > 0:
                    p = cell.add_paragraph()
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.line_spacing = 1.15
                add_formatted_runs(p, q_line, base_font="Arial", base_size=9.5, base_color=COLOR_SLATE_DARK)

            doc.add_paragraph().paragraph_format.space_after = Pt(6)
            i += 1
            continue

        # Check Horizontal Rule
        if line.strip() in ['---', '***', '___']:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            # Add subtle divider line or border
            pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="E2E8F0"/></w:pBdr>')
            p._p.get_or_add_pPr().append(pBdr)
            i += 1
            continue

        # Check bullet list item
        if line.strip().startswith(('- ', '* ')):
            bullet_text = line.strip()[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, bullet_text, base_font="Arial", base_size=10, base_color=COLOR_SLATE_BODY)
            i += 1
            continue

        # Check numbered list item
        m_num = re.match(r'^\s*(\d+)\.\s+(.*)', line)
        if m_num:
            num_text = m_num.group(2)
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, num_text, base_font="Arial", base_size=10, base_color=COLOR_SLATE_BODY)
            i += 1
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Normal paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        add_formatted_runs(p, line, base_font="Arial", base_size=10, base_color=COLOR_SLATE_BODY)
        i += 1

    if in_table:
        flush_table()
    if in_code_block:
        flush_code()

    # Save output docx
    doc.save(docx_path)
    print(f"Document successfully created at: {docx_path}")

if __name__ == '__main__':
    src = r'd:\Licence3\Framework_python\Projet_pharmacie\DOSSIER_CONCEPTION.md'
    dest = r'd:\Licence3\Framework_python\Projet_pharmacie\Dossier_de_Conception_PharmaGest.docx'
    create_document_from_md(src, dest)

