from __future__ import annotations

import re
from datetime import datetime
from typing import Any


_AMOUNT_TOKEN = r"(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)?\s*([0-9][0-9, ]*(?:\.[0-9]{1,2})?)"


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", value.replace(",", ""))
    try:
        number = float(cleaned)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number < 1_000_000_000 else None


def _find_label_amount(text: str, labels: list[str]) -> tuple[float | None, str | None]:
    # Require a semantic label on the same line and choose the final monetary value.
    # Percentage rates such as "IVA 21%" are explicitly excluded.
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    for label in labels:
        label_pattern = re.compile(rf"\b(?:{label})\b", re.IGNORECASE)
        for line in reversed(lines):
            match = label_pattern.search(line)
            if not match:
                continue
            tail = line[match.end():]
            candidates: list[tuple[float, str]] = []
            for amount_match in re.finditer(_AMOUNT_TOKEN, tail, re.IGNORECASE):
                # Ignore a rate token immediately followed by a percent sign.
                after = tail[amount_match.end(): amount_match.end() + 2]
                if "%" in after:
                    continue
                value = _number(amount_match.group(1))
                if value is not None and value > 0:
                    candidates.append((value, amount_match.group(0).strip()))
            if candidates:
                return candidates[-1][0], line
    return None, None


def _find_first(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" :#-\t")
    return None


def _normalise_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().replace(".", "/").replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def _detect_currency(text: str, fallback: str = "USD") -> str:
    upper = text.upper()
    if re.search(r"\b(?:INR|RS\.?)\b", upper) or re.search(r"₹\s*\d", text) or re.search(r"\b(?:GSTIN|CGST|SGST)\b", upper):
        return "INR"
    if re.search(r"\bEUR\b", upper) or re.search(r"€\s*\d", text):
        return "EUR"
    if re.search(r"\bGBP\b", upper) or re.search(r"£\s*\d", text):
        return "GBP"
    if re.search(r"\bUSD\b", upper) or re.search(r"\$\s*\d", text):
        return "USD"
    return fallback.upper()[:3]


def _detect_banking_currency(text: str) -> str:
    upper = text.upper()
    if re.search(r"\b(?:INR|RS\.?|RUPEES?)\b", upper) or re.search(r"₹", text):
        return "INR"
    if re.search(r"\bEUR\b", upper) or re.search(r"€", text):
        return "EUR"
    if re.search(r"\bGBP\b", upper) or re.search(r"£", text):
        return "GBP"
    if re.search(r"\bUSD\b", upper) or re.search(r"\$", text):
        return "USD"
    # Indian bank statement fallback — if the text contains an Indian bank name
    # or city names commonly found in Indian banking, assume INR
    if re.search(r"\b(?:SBI|HDFC|ICICI|AXIS|BANK\s+OF\s+BARODA|PUNJAB\s+NATIONAL|"
                 r"CANARA|UNION\s+BANK|INDIAN\s+BANK|IOB|IDBI|"
                 r"CO.OP|CO-OP|SAHAKARI|URBAN\s+CO.OP|URBAN\s+CO-OP|"
                 r"MUMBAI|DELHI|KOLKATA|CHENNAI|BANGALORE|PUNE|"
                 r"GSTIN|CGST|SGST|IGST)\b", upper):
        return "INR"
    return "INR"


def _vendor(text: str) -> str | None:
    explicit = _find_first(text, [
        r"^(?:vendor|supplier|seller|proveedor)\s*[:\-]\s*(.{2,100})$",
        r"^(?:from|issued by|emitido por)\s*[:\-]\s*(.{2,100})$",
        r"^(?:bill\s*from|sold\s*by)\s*[:\-]\s*(.{2,100})$",
    ])
    if explicit:
        return explicit
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    business = re.compile(
        r"\b(?:ENTERPRISES?|DISTRIBUTORS?|PHARMACEUTICAL|MEDIC(?:O|AL)?|SUPPLIES|SERVICES|"
        r"LIMITED|LTD\.?|PVT\.?|CORP(?:ORATION)?|COMPANY|INDUSTRIES|TRADING|AGENCY|"
        r"BROTHERS|ASSOCIATES|SOLUTIONS|TECHNOLOGIES|LOGISTICS|TRANSPORT|"
        r"CHEMICALS|LABORATORIES|MANUFACTURERS|WHOLESALERS|RETAILERS|PHARMA)\b", re.I)
    ignored = re.compile(
        r"COMPU[- ]?TAX|invoice|factura|referencia|reference|tax invoice|bill date|"
        r"gst no|customer|client|ship|deliver|to pay|total a pagar|grand total|"
        r"subtotal|taxable value|cgst|sgst|igst|round off|bank details", re.I)
    for line in lines[:120]:
        if ignored.search(line) or not business.search(line):
            continue
        cleaned = re.sub(r"^[^A-Za-z0-9]+", "", line)
        cleaned = re.sub(r"^(?:FOR|M/?S\.?)\s+", "", cleaned, flags=re.I)
        if 4 <= len(cleaned) <= 120:
            return cleaned
    for line in lines[:60]:
        if len(line) < 4 or len(line) > 100 or ignored.search(line) or re.fullmatch(r"[\W\d_]+", line):
            continue
        letters = [char for char in line if char.isalpha()]
        if len(letters) >= 4 and sum(char.isupper() for char in letters) / len(letters) >= 0.55:
            return line
    return None


_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_PATTERN = re.compile(r"(?:Ph(?:one)?|Mob(?:ile)?|Tel|Cell)\.?\s*:?\s*([0-9][0-9/,\-\s]{6,24}[0-9])", re.IGNORECASE)
_GSTIN_PATTERN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])\b")
_PAN_PATTERN = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
_PARTY_STOPWORDS = re.compile(
    r"\b(?:State\s*Code|GSTIN|PAN|D\.?L\.?No|Inv(?:oice)?\.?\s*(?:No|Number)|Date|Due\s*Date|Salesman|"
    r"Phone|Mob|E-?mail|Bill\s*To|Sold\s*To|Subtotal|Sub\s*Total|Total|Tax)\b",
    re.IGNORECASE,
)


def _extract_contact(block: str, *, name_hint: str | None = None) -> dict[str, str | None]:
    """Pull address/phone/email/GSTIN out of a free-text party block (the
    supplier or "bill to" cell of the invoice header). Mistral OCR collapses
    these into a single run-on line, so this works on substrings rather than
    per-line regexes."""
    email_match = _EMAIL_PATTERN.search(block)
    phone_match = _PHONE_PATTERN.search(block)
    gstin_match = _GSTIN_PATTERN.search(block)
    pan_match = _PAN_PATTERN.search(block)

    phone = phone_match.group(1).strip() if phone_match else None
    # Fallback: look for an unlabeled phone/mobile number
    if not phone:
        unlabeled_phone = re.search(r"\b(\+?\d{1,3}[-.\s]?\d{6,10})\b", block)
        if unlabeled_phone:
            phone = unlabeled_phone.group(1)

    address = None
    start = 0
    if name_hint:
        idx = block.find(name_hint)
        if idx != -1:
            start = idx + len(name_hint)
    if start == 0:
        # OCR sometimes mis-spells the printed name differently from the
        # name we matched elsewhere (e.g. "AMRIKA" vs "AMBIKA"), so an exact
        # substring lookup can fail. Addresses on these invoices reliably
        # start at a street number, so fall back to that as the split point.
        street_match = re.search(r"\d{1,5}\s*[,./-]?\s*[A-Z]\b|\d{1,5}\s+[A-Z]{2,}", block[:120])
        if street_match:
            start = street_match.start()
    remainder = block[start:].strip(" ,/-*")
    blank_line_match = re.search(r"\n\s*\n", remainder)
    if blank_line_match:
        remainder = remainder[: blank_line_match.start()]
    stop_match = _PARTY_STOPWORDS.search(remainder)
    address_text = remainder[: stop_match.start()] if stop_match else remainder[:160]
    address_text = re.sub(r"\s+", " ", address_text).strip(" ,/-")
    if 4 <= len(address_text) <= 160:
        address = address_text

    return {
        "address": address,
        "phone": phone,
        "email": email_match.group(0) if email_match else None,
        "gstin": gstin_match.group(1) if gstin_match else None,
        "pan": pan_match.group(1) if pan_match else None,
    }


def _customer_block(text: str) -> str | None:
    for cell in _document_header_cells(text):
        if re.search(r"^\s*(?:to\.?|bill\s*to|sold\s*to|buyer|customer|consignee)\b", cell, re.IGNORECASE):
            return cell
    match = re.search(
        r"(?:bill\s*to|sold\s*to|to\.|buyer|customer|consignee)\s*[:\-]?\s*(.{2,200})",
        text, re.IGNORECASE | re.MULTILINE,
    )
    if match:
        return match.group(0)
    # Indian invoice fallback: "To," or "M/s" on its own line
    match = re.search(r"^(?:To|M/?s)\s*[:\-–—]?\s*(.{2,200})", text, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(0)
    return None


def _customer_name(block: str | None) -> str | None:
    if not block:
        return None
    match = re.search(r"^\s*(?:to\.?|bill\s*to|sold\s*to|buyer|customer|consignee|m/?s)\s*[:\-]?\s*(.+)", block, re.IGNORECASE)
    rest = match.group(1) if match else block
    # Name typically ends at a slash (address follows) or a stopword.
    rest = re.split(r"\s*/\s*", rest, maxsplit=1)[0]
    stop_match = _PARTY_STOPWORDS.search(rest)
    name = rest[: stop_match.start()] if stop_match else rest
    name = name.strip(" ,/-")
    return name[:120] if 2 <= len(name) <= 120 else None


def _supplier_block(text: str, vendor_name: str | None) -> str:
    lines = text.splitlines()[:50]
    for i, line in enumerate(lines):
        if not _is_pipe_row(line):
            continue
        cells = [c for c in _split_table_row(line) if c.strip()]
        joined = " ".join(cells)
        if not (vendor_name and vendor_name.rstrip(".") in joined):
            if not re.search(r"\bGST(?:IN|NO)?\b", joined, re.IGNORECASE):
                continue
        # Found the supplier row — collect this row and any following pipe rows
        parts = [joined]
        j = i + 1
        while j < len(lines) and _is_pipe_row(lines[j]):
            next_cells = [c for c in _split_table_row(lines[j]) if c.strip()]
            parts.append(" ".join(next_cells))
            j += 1
        return " ".join(parts)
    return text[:600]


def _split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


_LINE_ITEM_HEADER_SYNONYMS: dict[str, tuple[str, ...]] = {
    "hsn_code": ("hsn", "hsn code", "hsn/sac", "sac", "sac code", "hsn sac"),
    "product_name": ("product name", "description", "particulars", "item", "item name", "item description", "product", "product details", "name of product", "article", "goods", "goods description", "details", "particular", "item particulars", "description of goods", "particulars of goods", "item details", "material", "material description"),
    "pack": ("pack", "pack size", "packing", "pkt", "packet"),
    "quantity": ("qty", "quantity", "quant", "no of", "no.", "serial", "qnt", "units", "uom", "unit of measure"),
    "batch_number": ("batch no", "batch", "batch number", "batch no.", "batch#", "lot no", "lot", "lot number"),
    "expiry_date": ("exp", "expiry", "exp date", "exp.date", "expiry date", "exp dt", "manf dt", "mfg", "mfg date", "manufacturing date"),
    "mrp": ("m.r.p.", "mrp", "m r p", "maximum retail price", "max retail price", "retail price", "mrp price"),
    "rate": ("rate", "price", "unit price", "unit", "unit rate", "per unit", "unit cost", "cost", "rate per unit"),
    "gst": ("gst", "gst%", "gst rate", "tax", "tax%", "tax rate", "gst %", "tax rate %", "gstrate", "taxrate", "gst %age", "tax %"),
    "cgst": ("cgst", "cgst%", "cgst rate", "cgst %"),
    "sgst": ("sgst", "sgst%", "sgst rate", "sgst %"),
    "igst": ("igst", "igst%", "igst rate", "igst %"),
    "taxable_value": ("taxable", "taxable value", "taxable amt", "taxable amount", "assessable value", "assessable amt"),
    "amount": ("amount", "net amt", "value", "total", "amt", "net amount", "gross", "sub total", "line total", "item total", "line amount", "item amount", "total amount", "extended", "extended amount", "value", "net value"),
}

_GST_SUMMARY_HEADER_NAMES: tuple[str, ...] = (
    "cgst%", "sgst%", "igst%", "cgst", "sgst", "igst", "taxable", "tax amt", "total gst", "total tax", "cash disc",
)


def _normalise_header(cell: str) -> str:
    return re.sub(r"[^a-z%]", "", cell.lower())


_ALL_HEADER_TOKENS: set[str] = {
    _normalise_header(name)
    for names in _LINE_ITEM_HEADER_SYNONYMS.values()
    for name in names
} | {_normalise_header(name) for name in _GST_SUMMARY_HEADER_NAMES}


def _is_header_row(cells: list[str]) -> bool:
    matches = sum(1 for cell in cells if _normalise_header(cell) in _ALL_HEADER_TOKENS)
    return matches >= 2


def _is_separator_row(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"\|?[\s:\-|]+\|?", stripped)) and "-" in stripped


def _is_pipe_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.count("|") >= 2


def _find_markdown_tables(text: str) -> list[list[list[str]]]:
    """Parse Mistral OCR's markdown output into structured tables.

    Mistral OCR renders detected tables as GitHub-flavoured markdown
    (`| cell | cell |` rows), but on multi-table pages it doesn't reliably
    emit blank lines or `| --- |` separators between adjacent tables (e.g. an
    item table immediately followed by a GST summary table) — earlier field
    extraction treated the whole run as unstructured text, or as one
    undifferentiated block, which silently dropped or mismatched almost every
    tabular field (line items, GST breakdown). A row only starts a new table
    here once it actually looks like a header (matches known column names),
    so adjacent tables without a blank-line gap are still split correctly.
    """
    lines = text.splitlines()
    n = len(lines)
    tables: list[list[list[str]]] = []
    i = 0
    while i < n:
        if not _is_pipe_row(lines[i]):
            i += 1
            continue
        cells = _split_table_row(lines[i])
        if not _is_header_row(cells):
            i += 1
            continue
        j = i + 1
        if j < n and _is_separator_row(lines[j]):
            j += 1
        rows: list[list[str]] = []
        while j < n and _is_pipe_row(lines[j]):
            if _is_separator_row(lines[j]):
                j += 1
                continue
            row_cells = _split_table_row(lines[j])
            if _is_header_row(row_cells):
                break
            rows.append(row_cells)
            j += 1
        if rows:
            tables.append([cells] + rows)
        i = j
    return tables


def _document_header_cells(text: str) -> list[str]:
    """Find the (non-tabular) header row holding supplier/customer/invoice-meta
    text — identified by content markers rather than by table position, since
    it doesn't have recognisable column names and so is never returned by
    `_find_markdown_tables`."""
    for line in text.splitlines()[:40]:
        if not _is_pipe_row(line):
            continue
        cells = [c for c in _split_table_row(line) if c.strip()]
        joined = " ".join(cells)
        if re.search(r"\bGST(?:IN|NO)\b", joined, re.IGNORECASE) or re.search(r"\bInv\.?\s*No\b", joined, re.IGNORECASE) or re.search(r"\bINVOICE\b", joined, re.IGNORECASE):
            return cells
    return []


def _match_table_header(cell: str, synonyms: dict[str, tuple[str, ...]]) -> str | None:
    norm = _normalise_header(cell)
    if not norm:
        return None
    for key, names in synonyms.items():
        if norm in {_normalise_header(name) for name in names}:
            return key
    return None


def _line_items_from_tables(tables: list[list[list[str]]]) -> list[dict[str, Any]]:
    for table in tables:
        header_row = table[0]
        col_map: dict[str, int] = {}
        for idx, cell in enumerate(header_row):
            key = _match_table_header(cell, _LINE_ITEM_HEADER_SYNONYMS)
            # Don't let a later "Com"/short-code column steal product_name once found.
            if key and not (key == "product_name" and "product_name" in col_map):
                col_map[key] = idx

        if "product_name" not in col_map or "amount" not in col_map:
            continue

        def cell_value(row: list[str], key: str) -> str | None:
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return None
            value = row[idx].strip()
            return value or None

        rows: list[dict[str, Any]] = []
        for data_row in table[1:]:
            product_name = cell_value(data_row, "product_name")
            amount = _number(cell_value(data_row, "amount"))
            if not product_name or amount is None or amount <= 0:
                continue
            # Skip total/summary rows
            if re.match(r"^(total|sub\s*total|grand\s*total|inv\s*amt)\b", product_name, re.IGNORECASE):
                continue
            rows.append({
                "description": product_name[:200],
                "hsn_code": cell_value(data_row, "hsn_code"),
                "pack": cell_value(data_row, "pack"),
                "batch_number": cell_value(data_row, "batch_number"),
                "expiry_date": cell_value(data_row, "expiry_date"),
                "quantity": _number(cell_value(data_row, "quantity")),
                "mrp": _number(cell_value(data_row, "mrp")),
                "rate": _number(cell_value(data_row, "rate")),
                "gst": _number(cell_value(data_row, "gst")),
                "cgst": _number(cell_value(data_row, "cgst")),
                "sgst": _number(cell_value(data_row, "sgst")),
                "igst": _number(cell_value(data_row, "igst")),
                "taxable_value": _number(cell_value(data_row, "taxable_value")),
                "line_total": amount,
            })
            if len(rows) >= 100:
                break
        if rows:
            return rows
    return []


def _line_items_loose(text: str) -> list[dict[str, Any]]:
    """Fallback for OCR/text output that isn't formatted as markdown tables."""
    rows: list[dict[str, Any]] = []
    ignored = re.compile(
        r"^\s*(?:subtotal|total|tax|gst|vat|iva|cgst|sgst|igst|invoice|bill|round|discount|"
        r"amount|to\s*pay|balance|due|payable|grand|net|taxable|"
        r"inv\s*amt|inv\s*amount)\b", re.I)
    seen_descriptions: set[str] = set()

    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if len(clean) < 8 or ignored.search(clean):
            continue

        # Pattern 1: description + amount at end (original)
        match = re.search(r"^(.+?)\s+([0-9,]+\.\d{2})\s*$", clean)
        if not match:
            # Pattern 2: description with qty, rate, amount at end
            match = re.search(r"^(.+?)\s+(\d+(?:\.\d+)?)\s+([0-9,]+\.\d{2})\s*$", clean)
            if match:
                # Use the last amount as line_total
                amount = _number(match.group(3))
                prefix = match.group(1).strip(" |-:")
            else:
                # Pattern 3: any amount in the line (take the last one)
                amounts = re.findall(r"([0-9,]+\.\d{2})", clean)
                if not amounts:
                    continue
                amount = _number(amounts[-1])
                # Remove the amount from the end to get description
                prefix = clean.rsplit(amounts[-1], 1)[0].strip(" |-:")
        else:
            amount = _number(match.group(2))
            prefix = match.group(1).strip(" |-:")

        if amount is None or amount <= 0:
            continue
        if not re.search(r"[A-Za-z]", prefix):
            continue
        # Deduplicate
        prefix_clean = re.sub(r"\s+", " ", prefix).lower()[:60]
        if prefix_clean in seen_descriptions:
            continue
        seen_descriptions.add(prefix_clean)

        # Try to extract HSN code (4-8 digit number) and rate from prefix
        hsn = None
        rate = None
        qty = None
        numbers_in_prefix = re.findall(r"(\d+(?:\.\d+)?)", prefix)
        # Walk backwards: the numbers before the amount are likely rate, qty, hsn
        if len(numbers_in_prefix) >= 3:
            # Last number before amount is likely the rate
            rate_candidate = _number(numbers_in_prefix[-1])
            if rate_candidate and rate_candidate > 0:
                rate = rate_candidate
            # Second to last could be qty
            qty_candidate = _number(numbers_in_prefix[-2])
            if qty_candidate and qty_candidate > 0:
                qty = qty_candidate
            # Look for a 4-8 digit HSN code
            for n in numbers_in_prefix:
                if 4 <= len(n.replace(".", "")) <= 8 and "." not in n:
                    hsn = n
                    break
        elif len(numbers_in_prefix) >= 2:
            rate_candidate = _number(numbers_in_prefix[-1])
            if rate_candidate and rate_candidate > 0:
                rate = rate_candidate
            qty_candidate = _number(numbers_in_prefix[-2])
            if qty_candidate and qty_candidate > 0:
                qty = qty_candidate
            for n in numbers_in_prefix:
                if 4 <= len(n.replace(".", "")) <= 8 and "." not in n:
                    hsn = n
                    break

        # Fallback: try to extract HSN from description
        if not hsn:
            hsn_match = re.search(r"\b(\d{4,8})\b", prefix)
            if hsn_match:
                hsn = hsn_match.group(1)

        # Parse leading quantity if not found via numbers
        if qty is None:
            quantity_match = re.match(r"^(\d+(?:\.\d+)?)\s+(.+)$", prefix)
            if quantity_match:
                qty = _number(quantity_match.group(1))

        rows.append({
            "description": prefix[:200],
            "quantity": qty,
            "rate": rate,
            "hsn_code": hsn,
            "line_total": amount,
            "mrp": None,
            "gst": None,
            "cgst": None,
            "sgst": None,
            "igst": None,
            "taxable_value": None,
            "pack": None,
            "batch_number": None,
            "expiry_date": None,
        })
        if len(rows) >= 100:
            break

    return rows


def _line_items(text: str, tables: list[list[list[str]]] | None = None) -> list[dict[str, Any]]:
    tables = _find_markdown_tables(text) if tables is None else tables
    table_rows = _line_items_from_tables(tables)
    if table_rows:
        return table_rows
    return _line_items_loose(text)


_GST_SUMMARY_HEADER_TOKENS = ("cgst", "sgst", "igst", "taxable")


def _extract_gst_summary(tables: list[list[list[str]]], text: str = "") -> dict[str, Any]:
    """Read the CGST/SGST/IGST breakdown table that Indian GST invoices place
    below the line items. Mistral OCR renders the rate% and the Taxable/Tax Amt
    pair as adjacent columns immediately following each rate column, so the
    values can be read positionally even though the same labels ("Taxable",
    "Tax Amt") repeat for each tax type."""
    result: dict[str, Any] = {}
    for table in tables:
        header_cells = [_normalise_header(c) for c in table[0]]
        # Check if this is a GST summary table
        if not any(token in cell for cell in header_cells for token in _GST_SUMMARY_HEADER_TOKENS):
            continue

        def rate_col(token: str) -> int | None:
            for i, cell in enumerate(header_cells):
                if token in cell and ("%" in cell or "rate" in cell or "pct" in cell):
                    return i
            # Fallback: just look for the token
            for i, cell in enumerate(header_cells):
                if token in cell:
                    return i
            return None

        # Also check for column headers that explicitly mention taxable value and tax amount
        taxable_cols = [i for i, cell in enumerate(header_cells) if "taxable" in cell or "assessable" in cell]
        tax_amt_cols = [i for i, cell in enumerate(header_cells) if "taxamt" in cell or "taxamount" in cell or "tax_amt" in cell]

        cgst_idx = rate_col("cgst")
        sgst_idx = rate_col("sgst")
        igst_idx = rate_col("igst")
        total_gst_idx = next((i for i, c in enumerate(header_cells) if "totalgst" in c or "totaltax" in c), None)

        for row in table[1:]:
            values = [_number(c) for c in row]
            if all(v is None for v in values):
                continue

            def at(idx: int | None) -> float | None:
                return values[idx] if idx is not None and idx < len(values) else None

            # Try to get taxable value from explicit column first
            taxable_val = None
            for tc in taxable_cols:
                tv = at(tc)
                if tv is not None:
                    taxable_val = tv
                    break

            cgst_taxable, cgst_tax = at(cgst_idx + 1) if cgst_idx is not None else None, at(cgst_idx + 2) if cgst_idx is not None else None
            sgst_taxable, sgst_tax = at(sgst_idx + 1) if sgst_idx is not None else None, at(sgst_idx + 2) if sgst_idx is not None else None
            igst_taxable, igst_tax = at(igst_idx + 1) if igst_idx is not None else None, at(igst_idx + 2) if igst_idx is not None else None
            total_gst = at(total_gst_idx)

            # Also check explicit tax amount columns
            tax_amt_val = None
            for tac in tax_amt_cols:
                tav = at(tac)
                if tav is not None:
                    tax_amt_val = tav
                    break

            if cgst_tax is None and sgst_tax is None and igst_tax is None and total_gst is None and tax_amt_val is None:
                continue

            result["cgstAmount"] = cgst_tax
            result["sgstAmount"] = sgst_tax
            result["igstAmount"] = igst_tax
            result["taxableValue"] = taxable_val or cgst_taxable or sgst_taxable or igst_taxable
            result["taxAmount"] = tax_amt_val or total_gst if total_gst is not None else round(
                (cgst_tax or 0) + (sgst_tax or 0) + (igst_tax or 0), 2
            ) or None
            return result

    # Text-based fallback: look for "CGST" / "SGST" / "IGST" followed by amount
    if not result and text:
        for label, key in [("cgst", "cgstAmount"), ("sgst", "sgstAmount"), ("igst", "igstAmount")]:
            m = re.search(rf"\b{label}\s*:?\s*₹?\s*([0-9,]+\.\d{{2}})", text, re.IGNORECASE)
            if m:
                val = _number(m.group(1))
                if val is not None:
                    result[key] = val
        # Taxable value
        m = re.search(r"\bTaxable\s*(?:Amount|Value)?\s*:?\s*₹?\s*([0-9,]+\.\d{2})", text, re.IGNORECASE)
        if m:
            val = _number(m.group(1))
            if val is not None:
                result["taxableValue"] = val
        # Total GST
        if result.get("cgstAmount") is not None or result.get("sgstAmount") is not None or result.get("igstAmount") is not None:
            result["taxAmount"] = round(
                (result.get("cgstAmount") or 0) + (result.get("sgstAmount") or 0) + (result.get("igstAmount") or 0), 2
            ) or None

    return result


def _extract_gross_breakdown(text: str) -> dict[str, Any]:
    """Indian distributor invoices commonly print a compact summary line like
    'Gross 465.84 Less 18.63 Add 53.66' followed by a bold 'NET 501.00' total —
    a layout the generic label/amount scanner below does not recognise."""
    result: dict[str, Any] = {}
    gross_match = re.search(
        r"\bGross\s+([0-9][0-9,]*\.\d{2})\s+Less\s+([0-9][0-9,]*\.\d{2})\s+Add\s+([0-9][0-9,]*\.\d{2})",
        text, re.IGNORECASE,
    )
    if gross_match:
        result["grossAmount"] = _number(gross_match.group(1))
        result["discountAmount"] = _number(gross_match.group(2))

    # Additional discount patterns
    if not result.get("discountAmount"):
        discount_match = re.search(
            r"\b(?:Discount|Less|Rebate)\s*:?\s*₹?\s*([0-9,]+\.\d{2})",
            text, re.IGNORECASE,
        )
        if discount_match:
            result["discountAmount"] = _number(discount_match.group(1))

    net_match = re.search(r"\*{0,2}\bNET\b\*{0,2}\s+([0-9][0-9,]*\.\d{2})", text, re.IGNORECASE)
    if net_match:
        result["total"] = _number(net_match.group(1))
    return result


def _extract_tax_rates_from_tables(tables: list[list[list[str]]]) -> list[float]:
    """Extract GST tax rates from line item tables or GST summary tables."""
    rates: set[float] = set()
    for table in tables:
        header_cells = [_normalise_header(c) for c in table[0]]
        # Check for GST% or rate% columns
        gst_pct_cols = [i for i, cell in enumerate(header_cells) if "gst" in cell and "%" in cell]
        rate_pct_cols = [i for i, cell in enumerate(header_cells) if "rate" in cell and "%" in cell]
        tax_pct_cols = [i for i, cell in enumerate(header_cells) if "tax" in cell and "%" in cell]
        
        all_pct_cols = set(gst_pct_cols + rate_pct_cols + tax_pct_cols)
        for row in table[1:]:
            values = [_number(c) for c in row]
            for col_idx in all_pct_cols:
                if col_idx < len(values) and values[col_idx] is not None:
                    val = values[col_idx]
                    if 0 < val <= 100:
                        rates.add(round(val, 2))
    return sorted(rates)


def extract_financial_fields(text: str, *, fallback_currency: str = "USD", tables: list[list[list[str]]] | None = None) -> dict[str, Any]:
    total, total_evidence = _find_label_amount(text, [
        r"grand\s*total", r"invoice\s*(?:amount|amt)", r"inv\s*(?:amount|amt)",
        r"bill\s*(?:amount|amt)", r"bill\s*amt", r"total\s*(?:amount|amt)",
        r"total\s*to\s*pay", r"to\s*pay", r"amount\s*due", r"balance\s*due",
        r"net\s*payable", r"importe\s*total", r"total\s*a\s*pagar",
    ])
    subtotal, subtotal_evidence = _find_label_amount(text, [r"sub\s*total", r"taxable\s*(?:amount|amt|value)", r"base\s*imponible", r"net\s*amount"])
    tax_amount, tax_evidence = _find_label_amount(text, [
        r"total\s*(?:tax|gst|vat)", r"tax\s*(?:amount|amt)", r"gst\s*(?:amount|amt)", r"vat\s*(?:amount|amt)",
        r"cgst\s*(?:amount|amt)", r"sgst\s*(?:amount|amt)", r"iva",
    ])
    # Many Indian invoices show CGST and SGST separately. Sum the final labelled values
    # only when an explicit total-tax line was not found.
    if tax_amount is None:
        cgst, _ = _find_label_amount(text, [r"cgst\s*(?:amount|amt)", r"cgst"])
        sgst, _ = _find_label_amount(text, [r"sgst\s*(?:amount|amt)", r"sgst"])
        if cgst is not None or sgst is not None:
            tax_amount = round((cgst or 0) + (sgst or 0), 2)
            tax_evidence = "CGST + SGST"
    # Column-header OCR can accidentally associate the invoice total with a CGST/SGST
    # label. Reject implausible tax values rather than returning a false valid result.
    if total is not None and tax_amount is not None and tax_amount >= total * 0.50:
        tax_amount = None
        tax_evidence = None
    if total is None and subtotal is not None and tax_amount is not None:
        total = round(subtotal + tax_amount, 2)
        total_evidence = "Computed as subtotal plus tax"
    if subtotal is None and total is not None and tax_amount is not None and total >= tax_amount:
        subtotal = round(total - tax_amount, 2)
        subtotal_evidence = "Computed as total minus tax"

    # Extract tax rates from both tables and text
    table_rates = _extract_tax_rates_from_tables(tables) if tables else []
    text_rates = sorted({float(value) for value in re.findall(r"(?<!\d)(\d{1,2}(?:\.\d+)?)\s*%", text) if float(value) <= 100})
    # Combine and deduplicate
    rates = sorted(set(table_rates + text_rates))
    invoice_number = _find_first(text, [
        r"(?:gst\s*)?(?:tax\s*)?(?:invoice|inv|bill)\s*\.?\s*(?:no|number|#)\s*[\.,:*= _\-–—]*\s*([A-Z0-9$][A-Z0-9$./\-–—]{2,})",
        r"(?:n[uú]mero\s+de\s+factura|factura\s+n[uú]m\.?|factura\s*#)\s*[:_\-–—]?\s*([A-Z0-9$][A-Z0-9$/\-–—]{2,})",
        r"\b(?:INV|INVOICE|BILL)\s*[.\-#/_]*\s*([A-Z0-9]{2,}/[0-9]{2,}(?:/[A-Z0-9]+)?)",
        r"\b([A-Z]{1,3}[/\-][0-9]{2,6}(?:[/\-][0-9]{2,4})?)\b",
    ])
    if invoice_number:
        invoice_number = invoice_number.replace("–", "-").replace("—", "-").replace("$", "S").rstrip(".")
        # Reject clearly wrong matches
        if len(invoice_number) < 2 or invoice_number in ("0", "-"):
            invoice_number = None
        # Reject common label words captured as invoice number (e.g. "Date")
        if invoice_number and re.match(r"^(Date|Due|Total|Sub\s*Total|Amount|Inv(?:oice)?|Bill|Tax|GST|NET)\b", invoice_number, re.IGNORECASE):
            invoice_number = None
        # Reject pure dates
        if invoice_number and re.match(r"^\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4}$", invoice_number):
            invoice_number = None
    gst_vat = _find_first(text, [
        r"\bGST(?:IN|\s*NO\.?)\s*[:\-]?\s*([0-9A-Z]{15})\b",
        r"\b(?:VAT|IVA)\s*(?:NO|NUMBER|ID|NIF)?\s*[:\-]?\s*([A-Z0-9\-]{6,20})\b",
        r"\b(?:TAX\s*ID|NIF|CIF)\s*[:\-]?\s*([A-Z0-9\-]{6,20})\b",
    ])
    if not gst_vat:
        # Fallback: find any 15-char alphanumeric sequence matching GSTIN pattern standalone
        gstin_standalone = re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])\b", text)
        if gstin_standalone:
            gst_vat = gstin_standalone.group(1)
    invoice_date = _normalise_date(_find_first(text, [
        r"(?:invoice|inv|bill)\s*date\s*[:\-]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
        r"(?:fecha\s+de\s+factura|fecha)\s*[:\-]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
        r"(?:date)\s*[:\-]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
        r"\b(\d{2}[./\-]\d{2}[./\-]\d{4})\b",
    ]))
    due_date = _normalise_date(_find_first(text, [
        r"(?:due\s*date|payment\s*due|fecha\s+de\s+vencimiento)\s*[:\-]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
    ]))
    reference = _find_first(text, [
        r"^(?:referencia|pedido)\s*[:\-#]?\s*([A-Z0-9][A-Z0-9/\-]{2,})",
        r"^(?:reference|reference\s*number|ref\.?|po\s*(?:no|number)|purchase\s*order)\s*[:\-#]?\s*([A-Z0-9][A-Z0-9/\-]{2,})",
    ])
    vendor = _vendor(text)
    if tables is None:
        tables = _find_markdown_tables(text)
    line_items = _line_items(text, tables)

    customer_block = _customer_block(text)
    customer = _customer_name(customer_block) or _find_first(text, [
        r"(?:bill\s*to|sold\s*to|customer|client|cliente|consignee|buyer)\s*[:\-]\s*(.{2,100})",
        r"^(?:to|for)\s*[:\-]\s*(.{2,100})$",
        r"^(?:m/?s)\s*[:\-]?\s*(.{2,100})$",
    ])
    customer_contact = _extract_contact(customer_block, name_hint=customer) if customer_block else {}
    # Fallback: search the entire text for a GSTIN near the customer name
    if not customer_contact.get("gstin") and customer:
        cust_gstin_match = re.search(
            rf"(?:{re.escape(customer[:30])}.*?)?\b(\d{{2}}[A-Z]{{5}}\d{{4}}[A-Z][A-Z\d]Z[A-Z\d])\b",
            text, re.IGNORECASE,
        )
        if cust_gstin_match:
            customer_contact["gstin"] = cust_gstin_match.group(1)

    supplier_block = _supplier_block(text, vendor)
    supplier_contact = _extract_contact(supplier_block, name_hint=vendor)
    if not gst_vat and supplier_contact.get("gstin"):
        gst_vat = supplier_contact["gstin"]

    # Place of Supply
    place_of_supply = _find_first(text, [
        r"(?:Place\s*of\s*Supply|Place\s*of\s*Delivery|Supply\s*State|State\s*of\s*Supply)\s*[:\-–—]\s*(.{2,60})$",
    ])

    # Reverse Charge
    reverse_charge = None
    rc_match = re.search(r"\b(?:Reverse\s*Charge|RCM)\s*[:\-–—]?\s*(Yes|No|Y|N|Applicable|Not\s*Applicable)",
                         text, re.IGNORECASE)
    if rc_match:
        rc_val = rc_match.group(1).strip().lower()
        reverse_charge = rc_val in ("yes", "y", "applicable")
    else:
        reverse_charge = bool(re.search(r"\bReverse\s*Charge\s*(?:Yes|Applicable)\b", text, re.IGNORECASE))

    # Table-derived figures are read from actual table columns rather than
    # guessed from raw text, so prefer them over the label/amount text scan
    # whenever the document includes a recognisable GST or gross/net summary.
    gst_summary = _extract_gst_summary(tables, text)
    gross_breakdown = _extract_gross_breakdown(text)
    if gst_summary.get("taxAmount") is not None:
        tax_amount = gst_summary["taxAmount"]
        tax_evidence = "GST summary table"
    if gross_breakdown.get("total") is not None:
        total = gross_breakdown["total"]
        total_evidence = "NET total line"
    if gst_summary.get("taxableValue") is not None and subtotal is None:
        subtotal = gst_summary["taxableValue"]
        subtotal_evidence = "GST summary table (taxable value)"

    return {
        "invoiceNumber": invoice_number,
        "vendor": vendor,
        "vendorAddress": supplier_contact.get("address"),
        "vendorPhone": supplier_contact.get("phone"),
        "vendorEmail": supplier_contact.get("email"),
        "vendorPan": supplier_contact.get("pan"),
        "customer": customer,
        "customerGstin": customer_contact.get("gstin"),
        "customerAddress": customer_contact.get("address"),
        "customerPhone": customer_contact.get("phone"),
        "customerEmail": customer_contact.get("email"),
        "customerPan": customer_contact.get("pan"),
        "gstVatNumber": gst_vat,
        "placeOfSupply": place_of_supply,
        "reverseCharge": reverse_charge,
        "taxRates": rates,
        "taxRate": rates[0] if len(rates) == 1 else None,
        "taxAmount": tax_amount,
        "cgstAmount": gst_summary.get("cgstAmount"),
        "sgstAmount": gst_summary.get("sgstAmount"),
        "igstAmount": gst_summary.get("igstAmount"),
        "taxableValue": gst_summary.get("taxableValue"),
        "grossAmount": gross_breakdown.get("grossAmount"),
        "discountAmount": gross_breakdown.get("discountAmount"),
        "invoiceDate": invoice_date,
        "dueDate": due_date,
        "currency": _detect_currency(text, fallback_currency),
        "subtotal": subtotal,
        "total": total,
        "referenceNumber": reference,
        "lineItems": line_items,
        "evidence": {
            "total": total_evidence, "subtotal": subtotal_evidence, "tax": tax_evidence,
        },
    }


def extract_trade_fields(text: str) -> dict[str, Any]:
    """Extract international trade / shipping fields from invoice or
    shipping-document text returned by Mistral OCR.

    Returns a dict that can be merged into the pipeline's structured fields.
    """
    result: dict[str, Any] = {}

    # Incoterms — standard 3-letter codes often after a keyword
    incoterm_match = re.search(
        r"\b(?:Incoterms?|Terms?\s*of\s*(?:Delivery|Sale|Shipment)|Trade\s*Terms?|Delivery\s*Terms?)\s*[:\-–—]\s*(\w{3})",
        text, re.IGNORECASE,
    )
    if incoterm_match:
        code = incoterm_match.group(1).strip().upper()
        if code in ("EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DPU", "DAP", "DDP"):
            result["incoterms"] = code

    # Country of Origin
    origin = _find_first(text, [
        r"(?:Country|Nation)\s*(?:of\s*)?Origin\s*[:\-–—]\s*(.{2,40})$",
        r"(?:Made\s*in|Manufactured\s*in|Produced\s*in)\s+([A-Za-z\s]{2,40})(?:\s*[.:]|\n)",
        r"\bOrigin\s*[:\-–—]\s*([A-Za-z\s]{2,40})$",
    ])
    if origin:
        result["countryOfOrigin"] = origin.strip()[:40]

    # Country of Destination / Final Destination
    destination = _find_first(text, [
        r"(?:Country\s*(?:of\s*)?(?:Dest|Final|Destination)|Port\s*(?:of\s*)?Discharge|Place\s*of\s*Delivery)\s*[:\-–—]\s*(.{2,60})$",
        r"(?:Consignee|Notify|Final\s*Dest)\s*[:\-–—]\s*(.{2,60})$",
    ])
    if destination:
        result["countryOfDestination"] = destination.strip()[:60]

    # Port of Loading
    pol = _find_first(text, [
        r"(?:Port\s*(?:of\s*)?Loading|Loading\s*Port|POL)\s*[:\-–—]\s*(.{2,60})$",
        r"(?:From|Shipped\s*from)\s+([A-Za-z\s,]{2,60})(?:\s*To|\s*Port|\s*Via|\s*\n)",
    ])
    if pol:
        result["portOfLoading"] = pol.strip()[:60]

    # Port of Discharge
    pod = _find_first(text, [
        r"(?:Port\s*(?:of\s*)?(?:Discharge|Unloading|Destination)|Discharge\s*Port|POD)\s*[:\-–—]\s*(.{2,60})$",
        r"(?:To|Destination)\s+([A-Za-z\s,]{2,60})(?:\s*$|\s*\n)",
    ])
    if pod:
        result["portOfDischarge"] = pod.strip()[:60]

    # Exporter / Shipper
    exporter = _find_first(text, [
        r"^(?:Exporter|Shipper|Exportador)\s*[:\-–—]\s*(.{2,120})$",
        r"(?:Exporter|Shipper|Exportador)\s*[:\-–—]\s*(.{2,120})",
    ])
    if exporter:
        result["exporter"] = exporter.strip()[:120]

    # Importer / Consignee
    importer = _find_first(text, [
        r"^(?:Importer|Consignee|Importador)\s*[:\-–—]\s*(.{2,120})$",
        r"(?:Importer|Consignee|Importador)\s*[:\-–—]\s*(.{2,120})",
    ])
    if importer:
        result["importer"] = importer.strip()[:120]

    # Buyer (may be same as customer)
    buyer = _find_first(text, [
        r"^(?:Buyer|Buyer\s*\(if\s*other\s*than\s*consignee\))\s*[:\-–—]\s*(.{2,120})$",
        r"\bBuyer\s*[:\-–—]\s*(.{2,120})",
    ])
    if buyer:
        result["buyer"] = buyer.strip()[:120]

    # Seller (may be same as vendor)
    seller = _find_first(text, [
        r"^(?:Seller|Seller\s*\(if\s*other\s*than\s*exporter\))\s*[:\-–—]\s*(.{2,120})$",
        r"\bSeller\s*[:\-–—]\s*(.{2,120})",
    ])
    if seller:
        result["seller"] = seller.strip()[:120]

    # Gross Weight
    gross_wt = _find_first(text, [
        r"(?:Gross\s*Weight|G\.?\s*Weight|G\.?W\.?|Gross\s*Wt\.?)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:KGS?|KG|K\.?G\.?|LBS?|TONS?)",
        r"\b(Gross|G\.?W\.?)\s+([0-9,]+(?:\.[0-9]+)?)\s*(?:KGS?|KG)",
    ])
    if gross_wt:
        result["grossWeight"] = _number(gross_wt)

    # Net Weight
    net_wt = _find_first(text, [
        r"(?:Net\s*Weight|N\.?\s*Weight|N\.?W\.?|Net\s*Wt\.?)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:KGS?|KG|K\.?G\.?|LBS?|TONS?)",
        r"\b(Net|N\.?W\.?)\s+([0-9,]+(?:\.[0-9]+)?)\s*(?:KGS?|KG)",
    ])
    if net_wt:
        result["netWeight"] = _number(net_wt)

    # Payment Terms
    payment_terms = _find_first(text, [
        r"(?:Payment\s*Terms?|Terms?\s*of\s*Payment|Pay\s*Terms?)\s*[:\-–—]\s*(.{2,80})$",
        r"\b(?:LC|L\/?C|Letter\s+of\s+Credit|TT|T\/?T|Telegraphic\s+Transfer|CAD|Cash\s+Against\s+Docs|"
        r"DP|D\/?P|Documents\s+Against\s+Payment|DA|D\/?A|Documents\s+Against\s+Acceptance|"
        r"Open\s+Account|Net\s+\d+|Due\s+on\s+Receipt|COD|Cash\s+on\s+Delivery)\b",
    ])
    if payment_terms:
        result["paymentTerms"] = payment_terms.strip()[:80]

    # Invoice Value (same as total but may be labelled separately on trade docs)
    inv_value = _find_first(text, [
        r"(?:Invoice\s*(?:Value|Amount)|Total\s*Invoice\s*(?:Value|Amount)|FOB\s*Value)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)",
    ])
    if inv_value:
        result["invoiceValue"] = _number(inv_value)

    # Additional line-item level fields for trade docs
    # HS Code at line-item level is already handled in _line_items
    # Add unit_price and total_amount per line item using enhanced parsing
    return result


def extract_banking_statement_fields(text: str) -> dict[str, Any]:
    """Extract structured fields from bank statement text returned by
    Mistral OCR. Returns a dict suitable for merging into the pipeline's
    structured fields, including a ``transactions`` list."""
    result: dict[str, Any] = {}

    # Common Indian bank names — match against full text when labelled patterns fail
    _KNOWN_BANKS = [
        "State Bank of India", "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank",
        "Kotak Mahindra", "Yes Bank", "Bank of Baroda", "BOB", "Punjab National Bank",
        "PNB", "Canara Bank", "Union Bank of India", "Indian Bank", "Indian Overseas Bank",
        "IOB", "IDBI Bank", "Bank of India", "Central Bank of India", "UCO Bank",
        "Federal Bank", "IDFC First Bank", "South Indian Bank", "Dhanlaxmi Bank",
        "Bandhan Bank", "Jammu & Kashmir Bank", "Karnataka Bank", "Karur Vysya Bank",
        "City Union Bank", "Standard Chartered", "Citi Bank", "HSBC",
        "PUNE URBAN CO-OP BANK LTD", "PUNE URBAN CO-OP BANK",
        "Abhyudaya Co-op Bank", "Ahmedabad Mercantile Co-op Bank",
        "Apna Sahakari Bank", "Bharat Co-op Bank", "Bombay Mercantile Co-op Bank",
        "Citizen Credit Co-op Bank", "Cosmos Co-op Bank", "Dombivli Nagari Sahakari Bank",
        "Gopinath Patil Parsik Janata Sahakari Bank", "Greater Bombay Co-op Bank",
        "Janakalyan Sahakari Bank", "Janata Sahakari Bank", "Kalyan Janata Sahakari Bank",
        "Kapol Co-op Bank", "Mahanagar Co-op Bank", "Mumbai District Central Co-op Bank",
        "NKGSB Co-op Bank", "Nagar Urban Co-op Bank", "Nasik Merchants Co-op Bank",
        "New India Co-op Bank", "Nutun Nagpur Sahakari Bank", "Pravara Sahakari Bank",
        "Rajgurunagar Sahakari Bank", "Rajkot Nagrik Co-op Bank", "Rupee Co-op Bank",
        "Saraswat Co-op Bank", "Shamrao Vithal Co-op Bank", "Solapur Janata Sahakari Bank",
        "Surat Nagarik Sahakari Bank", "Thane Bharat Sahakari Bank", "Thane Janata Sahakari Bank",
        "Zoroastrian Co-op Bank", "Tamilnadu Mercantile Bank", "TMB",
        "Kerala Gramin Bank", "Pragathi Krishna Gramin Bank",
    ]

    # Bank Name — try labelled patterns first, then fallback to known names
    bank_result = _find_first(text, [
        r"(?:Name\s*(?:of\s*)?(?:Bank|the\s*Bank)|Bank\s*(?:Name|Branch))\s*[:\-–—]\s*(.{2,80})$",
        r"(?:Bank|Branch)\s*(?::|–|—|\-)\s*(.{2,80})$",
        r"^([A-Z][A-Za-z0-9\s&.,\-'_\/()]{5,70}(?:LTD\.?|LIMITED|BANK))\b",
        r"\b([A-Z][A-Za-z0-9\s&.,\-'_\/()]{3,60}(?:BANK|BANQUE|BANCO|Bank|Banque|Banco))\b",
    ])
    if not bank_result:
        # Try matching entire lines that look like a bank name
        for line in text.splitlines():
            stripped = line.strip().upper()
            if re.search(r"(?:CO.OP|CO-OP|URBAN|BANK\s+LTD|SAHAKARI)", stripped):
                if len(stripped) > 5 and len(stripped) < 80:
                    bank_result = line.strip()
                    break
    if not bank_result:
        for bank in _KNOWN_BANKS:
            if bank.lower() in text.lower():
                bank_result = bank
                break
    if bank_result:
        result["bankName"] = bank_result.strip()[:80]

    # Branch Name
    branch = _find_first(text, [
        r"Branch\s*(?:Name|Code)?\s*[:\-–—]\s*(.{2,60})$",
        r"(?:Branch|Branch\s*Office|Local\s*Office)\s*[:\-–—]\s*(.{2,60})",
        r"\b(?:AT\s+|PO\s+|AT\s+PO\s+|BRANCH\s+OFFICE\s+AT)\s*(.{2,60})$",
    ])
    if not branch:
        # Try extracting from address-like line below the bank name
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            upper = line.upper()
            if re.search(r"(?:CO\.OP|CO-OP|URBAN|BANK\s+LTD)", upper):
                # Look at next non-empty line(s) for address/branch info
                for j in range(i + 1, min(i + 3, len(lines))):
                    nxt = lines[j].strip()
                    if not nxt:
                        continue
                    # Skip lines containing account numbers, dates, statement periods
                    if re.search(r"(?:[Aa]\/?[Cc]|ACCOUNT|NO\.?\s*\d{6,}|"
                                 r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|STATEMENT|PERIOD|FROM|TO)", nxt):
                        continue
                    if 5 <= len(nxt) <= 80:
                        branch = nxt
                        break
                break
    if branch:
        result["branchName"] = branch.strip()[:60]

    # Account Holder Name — also try broad "Name:" or text between account header lines
    holder = _find_first(text, [
        r"(?:Account\s*(?:Holder|Name)|Customer\s*Name|Name\s*(?:of\s*)?(?:Account|A/?c))\s*[:\-–—]\s*(.{2,100})$",
        r"(?:In\s+Favour\s+of|Payee|Beneficiary)\s*[:\-–—]\s*(.{2,100})",
    ])
    if not holder:
        # Some statements put the holder name near the account number
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            if re.search(r"(?:Account|A/?c)\s*(?:No|Number)", line, re.I):
                # Check previous line
                if i > 0:
                    prev = lines[i-1]
                    if (len(prev) > 3 and not re.search(r"(?:bank|branch|address|road|street|nagar|"
                                                        r"pune|mumbai|delhi|kolkata|chennai|bangal|"
                                                        r"current|savings|fixed|recurring|"
                                                        r"account|type|statement|period|date|"
                                                        r"opening|closing|balance)", prev, re.I)):
                        holder = prev
                # Check next line if prev didn't match
                if not holder and i + 1 < len(lines):
                    nxt = lines[i+1]
                    if (len(nxt) > 3 and not re.search(r"(?:bank|branch|address|road|street|nagar|"
                                                        r"pune|mumbai|delhi|kolkata|chennai|bangal|"
                                                        r"current|savings|fixed|recurring|"
                                                        r"account|type|statement|period|date|"
                                                        r"opening|closing|balance)", nxt, re.I)):
                        holder = nxt
                break
    if holder:
        holder = re.sub(r"\s+", " ", holder).strip()
        holder = re.sub(r"^[:\-–—\s]+", "", holder)
        result["accountHolderName"] = holder[:100]

    # Account Number
    acct = _find_first(text, [
        r"(?:Account|A/?c|A\/C)\s*(?:No|Number|#)\s*[:\-–—]\s*([0-9X*]{6,24})\b",
        r"(?:A/?c\s*No\.?)[:\-–—]\s*([0-9X*]{6,24})",
        r"\b([0-9]{8,20})\b",
    ])
    if acct:
        result["accountNumber"] = acct.strip()

    # Account Type — also scan for common account type phrases in the full text
    acct_type = _find_first(text, [
        r"(?:Account\s*Type|Type\s*(?:of\s*)?Account|A/?c\s*Type)\s*[:\-–—]\s*(.{3,30})$",
        r"(\b(?:Savings?|Current|Checking|Fixed\s*Deposit|Recurring\s*Deposit|NRI|NRE|NRO)\s*(?:Account|A/?c))",
    ])
    if not acct_type:
        for pat in [r"\b(Savings?\s+Account)\b", r"\b(Current\s+Account)\b", r"\b(Fixed\s+Deposit\s+Account)\b"]:
            m = re.search(pat, text, re.I)
            if m:
                acct_type = m.group(1)
                break
    if acct_type:
        result["accountType"] = acct_type.strip()[:30]

    # Statement Period
    period_from = _find_first(text, [
        r"(?:Statement\s*Period|Period|For\s*the\s*Period|From)\s*[:\-–—]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
        r"From\s+(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})\s*(?:To|Till|Up\s*To|-|–|—)",
    ])
    if period_from:
        result["statementPeriodFrom"] = _normalise_date(period_from)

    period_to = _find_first(text, [
        r"(?:To|Till|Up\s*To)\s+(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
        r"(?:Statement\s*Period|Period)\s*[:\-–—]?\s*\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4}\s*(?:-|–|—|to)\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})",
        r"\b(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})\s*$",
    ])
    if period_to:
        result["statementPeriodTo"] = _normalise_date(period_to)

    # Currency — override for Indian bank statements
    result["currency"] = _detect_banking_currency(text)

    # Opening / Closing balances — broader patterns
    opening = _find_first(text, [
        r"(?:Opening\s*Balance|Balance\s*(?:B\/?F|brought\s*forward)|Op\.?\s*Balance)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)",
        r"(?:Balance\s*Brought\s*Forward|Brought\s*Forward)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)",
    ])
    if opening:
        result["openingBalance"] = _number(opening)

    closing = _find_first(text, [
        r"(?:Closing\s*Balance|Balance\s*(?:C\/?F|carried\s*forward)|Cl\.?\s*Balance)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)",
        r"(?:Balance\s*Carried\s*Forward|Carried\s*Forward)\s*[:\-–—]?\s*([0-9,]+(?:\.[0-9]+)?)",
    ])
    if closing:
        result["closingBalance"] = _number(closing)

    # — Parse transactions —

    transactions: list[dict[str, Any]] = []

    # Strategy A: markdown pipe tables (from _find_markdown_tables)
    tables = _find_markdown_tables(text)
    for table in tables:
        headers = [_normalise_header(c) for c in table[0]]
        date_col = _find_col(headers, ("date", "transaction date", "txn date", "posting date"))
        particulars_col = _find_col(headers, ("particulars", "description", "narration", "details", "transaction", "remarks", "reference"))
        debit_col = _find_col(headers, ("debit", "withdrawal", "dr", "dr amount", "amount dr", "issue"))
        credit_col = _find_col(headers, ("credit", "deposit", "cr", "cr amount", "amount cr", "payment", "deposit"))
        balance_col = _find_col(headers, ("balance", "running balance", "available", "closing balance"))
        chq_col = _find_col(headers, ("cheque", "chq", "check", "cheque no", "cheque number"))
        ref_col = _find_col(headers, ("ref", "reference", "transaction code", "txn code", "code"))
        txn_code_col = _find_col(headers, ("txn code", "transaction code", "code", "type"))
        if date_col is None and particulars_col is None:
            continue
        for row in table[1:]:
            cells = [c.strip() if c else "" for c in row]
            if any(c.lower() in ("", "carried forward", "brought forward", "total", "opening balance", "closing balance") for c in cells[:3]):
                continue
            txn: dict[str, Any] = {}
            if date_col is not None and date_col < len(cells):
                txn["transaction_date"] = _normalise_date(cells[date_col])
            if ref_col is not None and ref_col < len(cells) and cells[ref_col]:
                txn["reference_date"] = _normalise_date(cells[ref_col])
            if txn_code_col is not None and txn_code_col < len(cells) and cells[txn_code_col]:
                txn["transaction_code"] = cells[txn_code_col][:30]
            if particulars_col is not None and particulars_col < len(cells) and cells[particulars_col]:
                txn["particulars"] = cells[particulars_col][:200]
            if chq_col is not None and chq_col < len(cells) and cells[chq_col]:
                txn["cheque_number"] = cells[chq_col][:30]
            if debit_col is not None and debit_col < len(cells) and cells[debit_col]:
                d_v = _number(cells[debit_col])
                if d_v is not None:
                    txn["debit_amount"] = d_v
            if credit_col is not None and credit_col < len(cells) and cells[credit_col]:
                c_v = _number(cells[credit_col])
                if c_v is not None:
                    txn["credit_amount"] = c_v
            if balance_col is not None and balance_col < len(cells) and cells[balance_col]:
                b_v = _number(cells[balance_col])
                if b_v is not None:
                    txn["running_balance"] = b_v
                bal_raw = cells[balance_col]
                if re.search(r"(?:Dr|Debit)\b", bal_raw, re.I):
                    txn["balance_type"] = "Dr"
                elif re.search(r"(?:Cr|Credit)\b", bal_raw, re.I):
                    txn["balance_type"] = "Cr"
        if transactions:
            break

    # Strategy B: fallback text-based parser for space-aligned/csv formats
    if not transactions:
        transactions = _parse_bank_statement_text(text)

    result["transactions"] = transactions if transactions else []

    # Fallback: use first/last transaction balance as opening/closing
    if not result.get("openingBalance") or not result.get("closingBalance"):
        op, cl = _extract_balances_from_transactions(transactions)
        if not result.get("openingBalance") and op is not None:
            result["openingBalance"] = op
        if not result.get("closingBalance") and cl is not None:
            result["closingBalance"] = cl

    return result


def _parse_bank_statement_text(text: str) -> list[dict[str, Any]]:
    """Parse transaction lines from a bank statement that was NOT rendered as
    a markdown pipe table.  Handles space-aligned columns and CSV-like output.

    Uses three strategies in order:
      1. Block-based: lines with a date + amounts, grouped by consecutive descriptions
      2. Line-based: any line with a date and at least one amount (no grouping)
      3. Regex-scan: find all date/amount sequences anywhere in text
    """
    lines = text.splitlines()
    _DATE_RE = re.compile(r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b")
    _AMT_RE = re.compile(r"([\-–—]?[0-9,]+\.\d{2})")

    transactions: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _extract_amounts(block: str) -> list[float]:
        amts = []
        for a in _AMT_RE.findall(block):
            a = a.strip()
            try:
                amts.append(float(re.sub(r"[^\d.\-]", "", a.replace(",", ""))))
            except ValueError:
                continue
        return amts

    def _make_txn(date_str: str, description: str, amounts: list[float]) -> dict[str, Any] | None:
        if not date_str or not amounts:
            return None
        txn: dict[str, Any] = {}
        txn["transaction_date"] = _normalise_date(date_str)

        # Try to find reference dates in the description
        ref_dates = _DATE_RE.findall(description)
        if len(ref_dates) > 1:
            txn["reference_date"] = _normalise_date(ref_dates[1])

        # Filter zero amounts and classify
        meaningful = [(i, a) for i, a in enumerate(amounts) if abs(a) > 0.001]

        if not meaningful and amounts:
            txn["running_balance"] = abs(amounts[-1])
            return txn

        # Last meaningful value is always the running balance
        last_idx, bal_val = meaningful[-1]
        txn["running_balance"] = abs(bal_val)

        # Determine balance type from the line after the balance amount
        if re.search(r"\bDr\b", description, re.I) and not re.search(r"\bCr\b", description, re.I):
            txn["balance_type"] = "Dr"
        elif re.search(r"\bCr\b", description, re.I):
            txn["balance_type"] = "Cr"

        # If there's a transaction amount, classify it
        if len(meaningful) >= 2:
            trans_idx, trans_val = meaningful[-2]
            has_cheque = bool(re.search(r"\b(\d{5,8})\b", description))
            if trans_val < 0:
                txn["debit_amount"] = abs(trans_val)
            elif has_cheque:
                txn["debit_amount"] = trans_val
            elif re.search(r"\b(?:CHQ|CHEQUE|PAID|BY|DEBIT|WITHDRAWAL|DR\b)\s", description, re.I):
                txn["debit_amount"] = trans_val
            elif re.search(r"\b(?:DEPOSIT|CREDIT|BY|RECEIVED|INWARD|TRANSFER\s+TO)\s", description, re.I):
                txn["credit_amount"] = trans_val
            else:
                txn["credit_amount"] = trans_val

        # Extract cheque number
        chq_match = re.search(r"\b(\d{5,8})\b", description)
        if chq_match:
            txn["cheque_number"] = chq_match.group(1)

        # Clean description: remove amounts, dates, Dr/Cr markers, standalone cheque numbers
        desc = _DATE_RE.sub("", description)
        desc = _AMT_RE.sub("", desc)
        desc = re.sub(r"\b\d{5,8}\b", "", desc)
        desc = re.sub(r"\b(?:Dr|Cr|Cr\.?|Dr\.?)\b", "", desc)
        desc = re.sub(r"\s+", " ", desc).strip(" ,-–—")
        if desc:
            txn["particulars"] = desc[:200]

        return txn

    # Strategy 1: Block-based parsing (original approach)
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        date_match = _DATE_RE.search(line)
        if not date_match:
            i += 1
            continue

        date_str = date_match.group(1)
        block_lines = [line]

        # Collect following lines as description (until next date line)
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                break
            # If this line starts with a date, it's a new transaction
            if re.match(r"\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}", nxt):
                break
            # If this line is purely numbers/punctuation, it's likely a separator
            if re.match(r"^[\s\-=_*]+$", nxt):
                i += 1
                break
            # Skip header-like lines
            if re.match(r"(?:date|particulars|description|chq|cheque|debit|credit|withdrawal|deposit|"
                        r"balance|opening|closing|brought|carried|total|page|statement|period|sno)",
                        nxt, re.I):
                i += 1
                break
            block_lines.append(nxt)
            i += 1

        block = " ".join(block_lines)
        amounts = _extract_amounts(block)
        if not amounts:
            continue

        txn = _make_txn(date_str, block, amounts)
        if txn:
            dedup_key = f"{txn.get('transaction_date')}_{txn.get('particulars', '')[:50]}_{txn.get('running_balance')}"
            if dedup_key not in seen:
                seen.add(dedup_key)
                transactions.append(txn)

    # Strategy 2: Line-based (if block parser found nothing or very few)
    if len(transactions) < 2:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            date_match = _DATE_RE.search(line)
            if not date_match:
                continue
            amounts = _extract_amounts(line)
            if not amounts:
                continue
            txn = _make_txn(date_match.group(1), line, amounts)
            if txn:
                dedup_key = f"{txn.get('transaction_date')}_{txn.get('particulars', '')[:50]}_{txn.get('running_balance')}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    transactions.append(txn)
                    if len(transactions) >= 500:
                        break

    return transactions[:1000]


def _extract_balances_from_transactions(
    transactions: list[dict[str, Any]],
) -> tuple[float | None, float | None]:
    """Extract opening and closing balances from first/last transaction rows,
    as a fallback when labelled balance fields are absent."""
    opening = None
    closing = None
    if transactions:
        first = transactions[0]
        last = transactions[-1]
        if first.get("running_balance") is not None:
            opening = float(first["running_balance"])
        if last.get("running_balance") is not None:
            closing = float(last["running_balance"])
    return opening, closing


def _find_col(headers: list[str], synonyms: tuple[str, ...]) -> int | None:
    """Find column index matching any of the given normalized synonyms."""
    norm = {_normalise_header(h): i for i, h in enumerate(headers)}
    for syn in synonyms:
        key = _normalise_header(syn)
        if key in norm:
            return norm[key]
    return None


def processing_validation_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
    fields = record.get("structuredFields") or {}
    issues: list[dict[str, Any]] = []

    def add(code: str, message: str, field: str, severity: str = "error") -> None:
        issues.append({"code": code, "severity": severity, "message": message, "field": field})

    if record.get("ocrStatus") != "completed":
        add("OCR_INCOMPLETE", "OCR/document parsing must complete successfully.", "ocrStatus")
    if record.get("extractionStatus") != "completed":
        add("EXTRACTION_INCOMPLETE", "Structured financial extraction must complete successfully.", "extractionStatus")
    required = [
        ("invoiceNumber", "INVOICE_NUMBER_MISSING", "Invoice number was not extracted."),
        ("vendor", "VENDOR_MISSING", "Vendor/supplier was not extracted."),
        ("invoiceDate", "INVOICE_DATE_MISSING", "Invoice date was not extracted."),
        ("currency", "CURRENCY_MISSING", "Currency was not detected."),
        ("total", "TOTAL_MISSING", "Invoice total was not extracted from a labelled total field."),
    ]
    for field, code, message in required:
        if fields.get(field) in {None, "", 0}:
            add(code, message, field, "warning")
    upper = str(record.get("extractedText") or "").upper()
    tax_document = any(token in upper for token in ("GST", "VAT", "IVA", "CGST", "SGST", "TAX"))
    if tax_document and fields.get("taxAmount") is None:
        add("TAX_AMOUNT_MISSING", "Tax is present in the document but the tax amount was not reliably extracted.", "taxAmount", "warning")
    if tax_document and not fields.get("gstVatNumber"):
        add("TAX_ID_MISSING", "GST/VAT/Tax identifier was not extracted.", "gstVatNumber", "warning")
    if fields.get("total") is not None and fields.get("subtotal") is not None and fields.get("taxAmount") is not None:
        expected = round(float(fields["subtotal"]) + float(fields["taxAmount"]), 2)
        if abs(expected - float(fields["total"])) >= 0.05:
            add("TOTAL_RECONCILIATION_FAILED", f"Subtotal plus tax ({expected:.2f}) does not equal total ({float(fields['total']):.2f}).", "total", "warning")
    return issues


def _coerce_number(value: Any) -> float | None:
    """Like `_number`, but also accepts values Gemini may return as native
    JSON numbers (not just strings)."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value) if 0 <= float(value) < 1_000_000_000 else None
    return _number(str(value))


_GEMINI_FIELD_KEY_MAP: dict[str, str] = {
    "invoice_number": "invoiceNumber",
    "reference_number": "referenceNumber",
    "purchase_order": "referenceNumber",
    "vendor_name": "vendor",
    "vendor_address": "vendorAddress",
    "vendor_phone": "vendorPhone",
    "vendor_email": "vendorEmail",
    "vendor_tax_id": "gstVatNumber",
    "customer_name": "customer",
    "customer_address": "customerAddress",
    "customer_phone": "customerPhone",
    "customer_tax_id": "customerGstin",
    "currency": "currency",
    "gross_amount": "grossAmount",
    "discount_amount": "discountAmount",
    "subtotal": "subtotal",
    "taxable_value": "taxableValue",
    "tax_total": "taxAmount",
    "cgst_amount": "cgstAmount",
    "sgst_amount": "sgstAmount",
    "igst_amount": "igstAmount",
    "total_amount": "total",
}

_GEMINI_DATE_KEYS = {"invoice_date": "invoiceDate", "due_date": "dueDate"}


def map_gemini_fields(
    extracted_fields: dict[str, Any],
    field_confidence: dict[str, Any],
    *,
    fallback_currency: str = "USD",
    field_pages: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map Gemini 2.5 Pro's `extracted_fields`/`field_confidence` output onto
    the same field-dict shape the rest of the pipeline (validation, JSON
    export, SAP mapping) already expects from `extract_financial_fields`."""
    fields: dict[str, Any] = {}
    for gemini_key, internal_key in _GEMINI_FIELD_KEY_MAP.items():
        value = extracted_fields.get(gemini_key)
        if internal_key in (
            "grossAmount", "discountAmount", "subtotal", "taxableValue",
            "taxAmount", "cgstAmount", "sgstAmount", "igstAmount", "total",
        ):
            value = _coerce_number(value)
        if value is not None or internal_key not in fields:
            fields[internal_key] = value

    for gemini_key, internal_key in _GEMINI_DATE_KEYS.items():
        fields[internal_key] = _normalise_date(extracted_fields.get(gemini_key))

    fields["currency"] = fields.get("currency") or fallback_currency

    tax_amount = fields.get("taxAmount")
    taxable_value = fields.get("taxableValue") or fields.get("subtotal")
    rates: list[float] = []
    if tax_amount and taxable_value:
        rates = [round(tax_amount / taxable_value * 100, 2)]
    fields["taxRates"] = rates
    fields["taxRate"] = rates[0] if len(rates) == 1 else None

    line_items_raw = extracted_fields.get("line_items") or []
    line_items: list[dict[str, Any]] = []
    if isinstance(line_items_raw, list):
        for item in line_items_raw:
            if not isinstance(item, dict):
                continue
            description = item.get("description")
            line_total = _coerce_number(item.get("total"))
            if not description or line_total is None:
                continue
            line_items.append({
                "description": str(description)[:200],
                "hsn_code": item.get("hsn_code"),
                "batch_number": item.get("batch_number"),
                "expiry_date": item.get("expiry_date"),
                "quantity": _coerce_number(item.get("quantity")),
                "mrp": _coerce_number(item.get("mrp")),
                "rate": _coerce_number(item.get("unit_price")),
                "line_total": line_total,
            })
    fields["lineItems"] = line_items

    fields["evidence"] = {
        "total": "Gemini 2.5 Pro" if fields.get("total") is not None else None,
        "subtotal": "Gemini 2.5 Pro" if fields.get("subtotal") is not None else None,
        "tax": "Gemini 2.5 Pro" if fields.get("taxAmount") is not None else None,
    }

    # Per-field confidence, keyed by our internal field names so downstream
    # consumers (confidence_details, the extracted-fields UI) don't need to
    # know about Gemini's schema at all.
    confidence_internal: dict[str, float] = {}
    for gemini_key, internal_key in {**_GEMINI_FIELD_KEY_MAP, **_GEMINI_DATE_KEYS}.items():
        score = field_confidence.get(gemini_key)
        if isinstance(score, (int, float)):
            confidence_internal[internal_key] = max(0.0, min(1.0, float(score)))
    fields["_geminiFieldConfidence"] = confidence_internal

    pages_internal: dict[str, int] = {}
    for gemini_key, internal_key in {**_GEMINI_FIELD_KEY_MAP, **_GEMINI_DATE_KEYS}.items():
        page = (field_pages or {}).get(gemini_key)
        if isinstance(page, (int, float)):
            pages_internal[internal_key] = int(page)
    fields["_geminiFieldPages"] = pages_internal
    fields["_geminiAdditionalFields"] = extracted_fields.get("additional_fields") or {}
    fields["_geminiBankDetails"] = extracted_fields.get("bank_details") or {}
    fields["_geminiCustomsDeclaration"] = extracted_fields.get("customs_declaration") or {}

    return fields
