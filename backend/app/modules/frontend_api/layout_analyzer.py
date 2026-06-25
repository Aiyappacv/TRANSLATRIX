from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("translatrix.layout")


class LayoutRegion:
    """A detected region on a document page."""

    def __init__(
        self,
        region_type: str,
        bbox: tuple[float, float, float, float],
        text: str,
        confidence: float,
        page_number: int = 1,
    ):
        self.region_type = region_type
        self.bbox = bbox
        self.text = text
        self.confidence = confidence
        self.page_number = page_number

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.region_type,
            "bbox": list(self.bbox),
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "pageNumber": self.page_number,
        }


class DetectedTable:
    """A table extracted from a document page."""

    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        bbox: tuple[float, float, float, float],
        confidence: float,
        page_number: int = 1,
    ):
        self.headers = headers
        self.rows = rows
        self.bbox = bbox
        self.confidence = confidence
        self.page_number = page_number

    def to_dict(self) -> dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": [
                {f"col_{i}": cell for i, cell in enumerate(row)}
                for row in self.rows
            ],
            "bbox": list(self.bbox),
            "confidence": round(self.confidence, 4),
            "pageNumber": self.page_number,
        }

    def to_structured_rows(self) -> list[dict[str, Any]]:
        if not self.headers or not self.rows:
            return []
        results = []
        for row in self.rows:
            row_dict: dict[str, Any] = {}
            for i, header in enumerate(self.headers):
                if i < len(row):
                    row_dict[header.strip().lower().replace(" ", "_")] = row[i].strip()
                else:
                    row_dict[header.strip().lower().replace(" ", "_")] = ""
            results.append(row_dict)
        return results


class LayoutAnalyzer:
    """Analyse document layout using OCR bounding-box coordinates.

    Groups text blocks into logical regions (header, body, table, footer)
    and detects tabular structures from spatial arrangements.
    """

    HEADER_HEIGHT_FRACTION = 0.15
    FOOTER_HEIGHT_FRACTION = 0.10
    TABLE_COLUMN_OVERLAP_THRESHOLD = 0.6
    LINE_GAP_THRESHOLD_MULTIPLIER = 2.5

    @staticmethod
    def analyze_page(
        text_blocks: list[dict[str, Any]],
        page_width: float,
        page_height: float,
        page_number: int = 1,
    ) -> dict[str, Any]:
        regions: list[LayoutRegion] = []
        tables: list[DetectedTable] = []

        if not text_blocks:
            return {"regions": [], "tables": [], "pageNumber": page_number}

        header_boundary = page_height * LayoutAnalyzer.HEADER_HEIGHT_FRACTION
        footer_boundary = page_height * (1 - LayoutAnalyzer.FOOTER_HEIGHT_FRACTION)
        header_blocks: list[dict[str, Any]] = []
        body_blocks: list[dict[str, Any]] = []
        footer_blocks: list[dict[str, Any]] = []

        for block in text_blocks:
            bbox = block.get("bbox", [0, 0, page_width, page_height])
            y_center = (bbox[1] + bbox[3]) / 2
            if y_center < header_boundary:
                header_blocks.append(block)
            elif y_center > footer_boundary:
                footer_blocks.append(block)
            else:
                body_blocks.append(block)

        if header_blocks:
            text = " ".join(b.get("text", "") for b in header_blocks)
            conf = sum(b.get("confidence", 0) for b in header_blocks) / max(len(header_blocks), 1)
            regions.append(
                LayoutRegion("header", [0, 0, page_width, header_boundary], text, conf, page_number)
            )

        table_candidates = LayoutAnalyzer._find_tables(body_blocks, page_width, page_number)
        tables.extend(table_candidates)

        table_y_regions = set()
        for t in tables:
            for y in range(int(t.bbox[1]), int(t.bbox[3]) + 1, 5):
                table_y_regions.add(y)

        body_text_blocks = [
            b for b in body_blocks
            if not LayoutAnalyzer._block_in_table_region(b, table_y_regions)
        ]

        if body_text_blocks:
            text = " ".join(b.get("text", "") for b in body_text_blocks)
            conf = sum(b.get("confidence", 0) for b in body_text_blocks) / max(len(body_text_blocks), 1)
            bbox = LayoutAnalyzer._union_bbox(body_text_blocks)
            regions.append(LayoutRegion("body", bbox, text, conf, page_number))

        if footer_blocks:
            text = " ".join(b.get("text", "") for b in footer_blocks)
            conf = sum(b.get("confidence", 0) for b in footer_blocks) / max(len(footer_blocks), 1)
            regions.append(
                LayoutRegion("footer", [0, footer_boundary, page_width, page_height], text, conf, page_number)
            )

        return {
            "regions": [r.to_dict() for r in regions],
            "tables": [t.to_dict() for t in tables],
            "pageNumber": page_number,
        }

    @staticmethod
    def analyze_pages(
        pages_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results = []
        for page in pages_data:
            blocks = page.get("blocks", [])
            width = page.get("width", 800)
            height = page.get("height", 1000)
            page_num = page.get("pageNumber", 1)
            result = LayoutAnalyzer.analyze_page(blocks, width, height, page_num)
            results.append(result)
        return results

    @staticmethod
    def _find_tables(
        blocks: list[dict[str, Any]], page_width: float, page_number: int
    ) -> list[DetectedTable]:
        tables: list[DetectedTable] = []
        if len(blocks) < 3:
            return tables

        sorted_blocks = sorted(blocks, key=lambda b: (b.get("bbox", [0, 0, 0, 0])[1], b.get("bbox", [0, 0, 0, 0])[0]))

        lines: list[list[dict[str, Any]]] = []
        current_line = [sorted_blocks[0]]
        for block in sorted_blocks[1:]:
            prev = current_line[-1]
            prev_bbox = prev.get("bbox", [0, 0, 0, 0])
            curr_bbox = block.get("bbox", [0, 0, 0, 0])
            prev_bottom = prev_bbox[3]
            curr_top = curr_bbox[1]
            avg_height = (prev_bbox[3] - prev_bbox[1] + curr_bbox[3] - curr_bbox[1]) / 2
            if curr_top - prev_bottom < avg_height * LayoutAnalyzer.LINE_GAP_THRESHOLD_MULTIPLIER:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
        if current_line:
            lines.append(current_line)

        if len(lines) < 3:
            return tables

        column_positions = LayoutAnalyzer._detect_columns(sorted_blocks)
        if len(column_positions) < 3:
            return tables

        table_lines = []
        for line_blocks in lines:
            line_y = min(b.get("bbox", [0, 0, 0, 0])[1] for b in line_blocks)
            cols = []
            for col_left, col_right in column_positions:
                col_text = ""
                for b in line_blocks:
                    bx = b.get("bbox", [0, 0, 0, 0])
                    overlap = max(0, min(bx[2], col_right) - max(bx[0], col_left))
                    col_width = bx[2] - bx[0]
                    if col_width > 0 and overlap / col_width > 0.3:
                        col_text = (col_text + " " + b.get("text", "")).strip()
                cols.append(col_text)
            table_lines.append(cols)

        if len(table_lines) >= 3:
            headers = table_lines[0]
            data_rows = table_lines[1:]
            y1 = min(b.get("bbox", [0, 0, 0, 0])[1] for b in sorted_blocks)
            y2 = max(b.get("bbox", [0, 0, 0, 0])[3] for b in sorted_blocks)
            x1 = min(column_positions, key=lambda c: c[0])[0]
            x2 = max(column_positions, key=lambda c: c[1])[1]
            confidence = LayoutAnalyzer._table_confidence(lines, column_positions)
            table = DetectedTable(
                headers=headers,
                rows=data_rows,
                bbox=(x1, y1, x2, y2),
                confidence=confidence,
                page_number=page_number,
            )
            tables.append(table)

        return tables

    @staticmethod
    def _detect_columns(blocks: list[dict[str, Any]]) -> list[tuple[float, float]]:
        if not blocks:
            return []
        x_centers = []
        for b in blocks:
            bbox = b.get("bbox", [0, 0, 0, 0])
            center = (bbox[0] + bbox[2]) / 2
            x_centers.append(center)
        if not x_centers:
            return []
        x_centers.sort()
        clusters: list[list[float]] = []
        current = [x_centers[0]]
        gap = (x_centers[-1] - x_centers[0]) / max(len(x_centers), 1) * 1.5
        for x in x_centers[1:]:
            if x - current[-1] < gap:
                current.append(x)
            else:
                clusters.append(current)
                current = [x]
        if current:
            clusters.append(current)
        if len(clusters) < 3:
            page_width = max(x_centers) + 50
            num_cols = min(8, len(set(round(x / (page_width / 8)) for x in x_centers)))
            clusters = [[] for _ in range(num_cols)]
            for x in x_centers:
                idx = min(num_cols - 1, int(x / (page_width / num_cols)))
                clusters[idx].append(x)
            clusters = [c for c in clusters if c]
        columns = []
        for cluster in clusters:
            if cluster:
                avg = sum(cluster) / len(cluster)
                spread = max(cluster) - min(cluster) if len(cluster) > 1 else 30
                columns.append((avg - spread, avg + spread))
        return columns

    @staticmethod
    def _block_in_table_region(
        block: dict[str, Any], table_y_regions: set[int]
    ) -> bool:
        bbox = block.get("bbox", [0, 0, 0, 0])
        y_center = int((bbox[1] + bbox[3]) / 2)
        return y_center in table_y_regions

    @staticmethod
    def _union_bbox(blocks: list[dict[str, Any]]) -> tuple[float, float, float, float]:
        x1 = min(b.get("bbox", [0, 0, 0, 0])[0] for b in blocks)
        y1 = min(b.get("bbox", [0, 0, 0, 0])[1] for b in blocks)
        x2 = max(b.get("bbox", [0, 0, 0, 0])[2] for b in blocks)
        y2 = max(b.get("bbox", [0, 0, 0, 0])[3] for b in blocks)
        return (x1, y1, x2, y2)

    @staticmethod
    def _table_confidence(
        lines: list[list[dict[str, Any]]], columns: list[tuple[float, float]]
    ) -> float:
        if not lines or not columns:
            return 0.0
        block_confidences = []
        for line in lines:
            for b in line:
                block_confidences.append(b.get("confidence", 0.5))
        avg_conf = sum(block_confidences) / max(len(block_confidences), 1)
        regularity = min(1.0, len(columns) / 8)
        return round(avg_conf * (0.7 + 0.3 * regularity), 4)
