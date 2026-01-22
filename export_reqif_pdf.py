#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import xml.etree.ElementTree as ET
import re
from pathlib import Path
from html import unescape

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader


class ReqIFExtractor:
    def __init__(self, reqif_file: str):
        self.reqif_file = Path(reqif_file).resolve()
        self.base_dir = self.reqif_file.parent

        self.namespaces = {
            "reqif": "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd",
            "xhtml": "http://www.w3.org/1999/xhtml",
        }

        self.tree = None
        self.root = None
        self.objects = {}
        self.hierarchy = []

    # ---------------------------------------------------------
    # PARSE
    # ---------------------------------------------------------
    def parse(self):
        print(f"Parseando: {self.reqif_file.name}")
        self.tree = ET.parse(self.reqif_file)
        self.root = self.tree.getroot()

    # ---------------------------------------------------------
    # XHTML → TEXTO / IMAGEM / OLE
    # ---------------------------------------------------------
    def extract_xhtml(self, element):
        """
        Retorna lista ordenada de conteúdo XHTML:
        ("text", str)
        ("image", Path)
        ("ole", Path)
        """
        content = []

        def walk(elem):
            if elem.text and elem.text.strip():
                txt = re.sub(r"\s+", " ", elem.text.strip())
                content.append(("text", unescape(txt)))

            for child in elem:
                tag = child.tag.split("}")[-1]

                if tag == "img":
                    src = child.attrib.get("src")
                    if src:
                        content.append(
                            ("image", (self.base_dir / src).resolve())
                        )

                elif tag == "object":
                    data = child.attrib.get("data")
                    if data:
                        content.append(
                            ("ole", (self.base_dir / data).resolve())
                        )

                walk(child)

                if child.tail and child.tail.strip():
                    tail = re.sub(r"\s+", " ", child.tail.strip())
                    content.append(("text", unescape(tail)))

        if element is not None:
            walk(element)

        return content

    # ---------------------------------------------------------
    # ATRIBUTOS XHTML
    # ---------------------------------------------------------
    def get_xhtml_attribute(self, spec_obj, name):
        values = spec_obj.find("reqif:VALUES", self.namespaces)
        if values is None:
            return []

        for val in values:
            ref = val.find(
                ".//reqif:ATTRIBUTE-DEFINITION-XHTML-REF",
                self.namespaces,
            )
            if ref is not None and name in ref.text:
                the_val = val.find(
                    ".//reqif:THE-VALUE",
                    self.namespaces,
                )
                return self.extract_xhtml(the_val)

        return []

    # ---------------------------------------------------------
    # SPEC OBJECTS
    # ---------------------------------------------------------
    def extract_objects(self):
        objs = self.root.find(".//reqif:SPEC-OBJECTS", self.namespaces)

        for obj in objs.findall("reqif:SPEC-OBJECT", self.namespaces):
            oid = obj.get("IDENTIFIER")

            num_elem = obj.find(
                ".//reqif:ATTRIBUTE-VALUE-INTEGER",
                self.namespaces,
            )
            number = num_elem.get("THE-VALUE") if num_elem is not None else ""

            heading = ""
            for t, v in self.get_xhtml_attribute(obj, "OBJECTHEADING"):
                if t == "text":
                    heading += v + " "

            content = self.get_xhtml_attribute(obj, "OBJECTTEXT")

            self.objects[oid] = {
                "req_id": f"REQ-{number.zfill(6)}"
                if number.isdigit()
                else oid,
                "heading": heading.strip(),
                "content": content,
                "level": 0,
                "hnum": "",
            }

    # ---------------------------------------------------------
    # HIERARQUIA + NUMERAÇÃO
    # ---------------------------------------------------------
    def extract_hierarchy(self):
        specs = self.root.find(".//reqif:SPECIFICATIONS", self.namespaces)

        for spec in specs.findall("reqif:SPECIFICATION", self.namespaces):
            children = spec.find("reqif:CHILDREN", self.namespaces)
            if children is not None:
                self._walk_hierarchy(children, [], 0)

    def _walk_hierarchy(self, parent, counters, level):
        index = 0

        for sh in parent.findall("reqif:SPEC-HIERARCHY", self.namespaces):
            index += 1
            current = counters[:level] + [index]
            hnum = ".".join(str(i) for i in current)

            ref = sh.find(
                "reqif:OBJECT/reqif:SPEC-OBJECT-REF",
                self.namespaces,
            )
            if ref is not None and ref.text in self.objects:
                obj = self.objects[ref.text]
                obj["level"] = level
                obj["hnum"] = hnum
                self.hierarchy.append(ref.text)

            children = sh.find("reqif:CHILDREN", self.namespaces)
            if children is not None:
                self._walk_hierarchy(children, current, level + 1)

    # ---------------------------------------------------------
    # PDF
    # ---------------------------------------------------------
    def generate_pdf(self, output_pdf):
        c = canvas.Canvas(output_pdf, pagesize=A4)
        width, height = A4
        margin = 20 * mm
        y = height - margin

        def new_page():
            nonlocal y
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - margin

        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, "DOCUMENTO DE REQUISITOS")
        y -= 20
        c.setFont("Helvetica", 10)

        for oid in self.hierarchy:
            obj = self.objects[oid]
            indent = margin + obj["level"] * 12

            if y < margin + 80:
                new_page()

            c.setFont("Helvetica-Bold", 10)
            title = f"{obj['hnum']} [{obj['req_id']}] {obj['heading']}"
            c.drawString(indent, y, title)
            y -= 14
            c.setFont("Helvetica", 10)

            for kind, val in obj["content"]:
                if y < margin + 80:
                    new_page()

                if kind == "text":
                    for line in self.wrap(val, 90):
                        c.drawString(indent + 10, y, line)
                        y -= 12

                elif kind == "image" and val.exists():
                    img = ImageReader(str(val))
                    iw, ih = img.getSize()
                    scale = min(
                        (width - indent - 20) / iw,
                        200 / ih,
                    )
                    c.drawImage(
                        img,
                        indent + 10,
                        y - ih * scale,
                        iw * scale,
                        ih * scale,
                    )
                    y -= ih * scale + 10

                elif kind == "ole":
                    label = f"📎 Abrir objeto OLE: {val.name}"
                    c.setFillColorRGB(0, 0, 1)
                    c.drawString(indent + 10, y, label)
                    c.linkURL(
                        val.name,
                        (indent + 10, y - 2, indent + 260, y + 10),
                        relative=1,
                    )
                    c.setFillColorRGB(0, 0, 0)
                    y -= 14

            y -= 10

        c.save()
        print(f"PDF gerado com sucesso: {output_pdf}")

    # ---------------------------------------------------------
    def wrap(self, text, max_len):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 <= max_len:
                cur = f"{cur} {w}".strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ---------------------------------------------------------
    def run(self, output_pdf):
        self.parse()
        self.extract_objects()
        self.extract_hierarchy()
        self.generate_pdf(output_pdf)


def main():
    import sys

    reqif = sys.argv[1] if len(sys.argv) > 1 else "_SRS_Export_Sprint_16.0.reqif"
    pdf = sys.argv[2] if len(sys.argv) > 2 else "SRS_Export_Sprint_16.0.pdf"

    extractor = ReqIFExtractor(reqif)
    extractor.run(pdf)


if __name__ == "__main__":
    main()
