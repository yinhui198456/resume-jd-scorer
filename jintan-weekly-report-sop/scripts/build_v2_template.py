#!/usr/bin/env python3
"""Build v2 weekly report template by fixing row heights and header row split behavior.

Reads the legacy template, removes fixed row heights from content rows,
adds cantSplit to section header rows, and writes a v2 template.
"""
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

PROJECT_DIR = Path(__file__).parent.parent
LEGACY_TEMPLATE = PROJECT_DIR / 'templates' / '常州市金坛第一人民医院数据指挥中心二期项目-工作周报-20260420-0424.docx'
V2_TEMPLATE = PROJECT_DIR / 'templates' / '常州市金坛第一人民医院数据指挥中心二期项目-工作周报-v2-模板.docx'

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def qn(tag):
    return '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}' + tag


def lxml_qname(tag):
    return etree.QName('http://schemas.openxmlformats.org/wordprocessingml/2006/main', tag)


def build_v2_template():
    if not LEGACY_TEMPLATE.exists():
        raise FileNotFoundError(f'Legacy template not found: {LEGACY_TEMPLATE}')

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        extract_dir = tmpdir_path / 'extracted'

        with zipfile.ZipFile(LEGACY_TEMPLATE, 'r') as zf:
            zf.extractall(extract_dir)

        doc_xml_path = extract_dir / 'word' / 'document.xml'
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(str(doc_xml_path), parser)
        root = tree.getroot()
        table = root.find('.//w:tbl', NS)
        if table is None:
            raise ValueError('No table found in template')

        rows = table.findall('w:tr', NS)
        if len(rows) != 13:
            raise ValueError(f'Expected 13 rows, found {len(rows)}')

        header_rows = {5, 7, 9, 11}  # section headers
        content_rows = {4, 6, 8, 10, 12}  # rows that should auto-expand

        for i, row in enumerate(rows):
            trPr = row.find('w:trPr', NS)
            if trPr is None:
                trPr = etree.Element(lxml_qname('trPr'))
                row.insert(0, trPr)

            # Remove fixed row heights from content rows and headers
            # so the table can auto-expand.
            trHeight = trPr.find('w:trHeight', NS)
            if trHeight is not None:
                if i in content_rows or i in header_rows:
                    trPr.remove(trHeight)

            # Add cantSplit to section header rows so they don't orphan
            # from the content row below.
            if i in header_rows:
                cantSplit = trPr.find('w:cantSplit', NS)
                if cantSplit is None:
                    cantSplit = etree.Element(lxml_qname('cantSplit'))
                    trPr.append(cantSplit)

        tree.write(str(doc_xml_path), encoding='UTF-8', xml_declaration=True, standalone=True)

        # Repack preserving order and metadata
        with zipfile.ZipFile(V2_TEMPLATE, 'w', zipfile.ZIP_DEFLATED) as zf_out:
            for file_path in sorted(extract_dir.rglob('*')):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(extract_dir))
                    zf_out.write(file_path, arcname)

    print(f'v2 template saved to: {V2_TEMPLATE}')


if __name__ == '__main__':
    build_v2_template()
