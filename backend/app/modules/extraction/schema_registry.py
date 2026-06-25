"""
Schema registry for document-type-driven extraction.

Instead of asking Gemini to "extract everything", each document type maps
to a strict field schema. The canonical field namespace matches the keys
`map_gemini_fields` (app.modules.frontend_api.document_intelligence) already
understands — invoice_number, vendor_name, total_amount, etc. — so every
document type's extraction still flows through the same downstream mapping,
validation, and JSON export pipeline. Type-specific fields that fall outside
that namespace (packing list / bill of lading specifics) are carried in
`additional_fields`, which is already a free-form bucket in that mapping.
"""
from __future__ import annotations

DOCUMENT_TYPES = (
    "invoice",
    "receipt",
    "purchase_order",
    "packing_list",
    "bill_of_lading",
    "customs_form",
    "contract",
    "banking_document",
    "other",
)

# Per-type guidance appended to the base prompt telling Gemini which fields
# in `extracted_fields` actually matter for this document type, plus any
# type-specific keys to populate under `additional_fields`.
_SCHEMA_GUIDANCE: dict[str, str] = {
    "invoice": (
        "This is an INVOICE. Focus on: invoice_number, invoice_date, due_date, "
        "vendor_name, vendor_address, vendor_tax_id, customer_name, customer_address, "
        "customer_tax_id, currency, subtotal, tax_total, cgst_amount, sgst_amount, "
        "igst_amount, total_amount, line_items, bank_details."
    ),
    "receipt": (
        "This is a RECEIPT. Focus on: invoice_number (receipt number), invoice_date, "
        "vendor_name, currency, total_amount, tax_total, line_items."
    ),
    "purchase_order": (
        "This is a PURCHASE ORDER. Focus on: purchase_order, invoice_date (order date), "
        "vendor_name, customer_name, currency, total_amount, line_items."
    ),
    "packing_list": (
        "This is a PACKING LIST. Focus on extracted_fields.line_items for packed items, "
        "and populate extracted_fields.additional_fields with: packing_list_number, "
        "total_packages, gross_weight, net_weight, total_volume. Also populate "
        "vendor_name (shipper) and customer_name (consignee) if present."
    ),
    "bill_of_lading": (
        "This is a BILL OF LADING. Populate extracted_fields.additional_fields with: "
        "bl_number, shipper, consignee, vessel, voyage_number, port_of_loading, "
        "port_of_discharge, container_number. Also populate the matching "
        "customs_declaration fields (port_of_loading, port_of_discharge, "
        "container_number, bill_of_lading, gross_weight, net_weight) and "
        "vendor_name/customer_name with shipper/consignee."
    ),
    "customs_form": (
        "This is a CUSTOMS/TRADE document. Focus on extracted_fields.customs_declaration: "
        "hsn_codes, country_of_origin, country_of_destination, shipping_terms, "
        "port_of_loading, port_of_discharge, gross_weight, net_weight, container_number, "
        "bill_of_lading."
    ),
    "contract": (
        "This is a CONTRACT/AGREEMENT. Focus on: vendor_name (party A), customer_name "
        "(party B), invoice_date (effective date), reference_number, and populate "
        "extracted_fields.additional_fields with key contract terms found."
    ),
    "banking_document": (
        "This is a BANKING_DOCUMENT. Focus on: bank_name, branch_name, account_holder_name, account_number, ifsc_swift_code, iban, transaction_date, transaction_reference, beneficiary_name, beneficiary_bank, currency, amount, remittance_details, lc_number, banking_reference. Populate extracted_fields.bank_details where appropriate."
    ),
    "other": (
        "Document type is not a standard commercial document. Populate whichever "
        "extracted_fields keys are present in the document; do not fabricate fields "
        "that are not printed in the text."
    ),
}


def normalize_document_type(document_type: str | None) -> str:
    if not document_type:
        return "other"
    value = document_type.strip().lower().replace(" ", "_").replace("-", "_")
    if value in DOCUMENT_TYPES:
        return value
    aliases = {
        "invoice_or_receipt": "invoice",
        "tax_invoice": "invoice",
        "commercial_invoice": "invoice",
        "po": "purchase_order",
        "order": "purchase_order",
        "packing_slip": "packing_list",
        "delivery_note": "packing_list",
        "bol": "bill_of_lading",
        "bill_of_lading_bol": "bill_of_lading",
        "customs_declaration": "customs_form",
        "shipping_bill": "customs_form",
        "agreement": "contract",
    }
    return aliases.get(value, "other" if value not in DOCUMENT_TYPES else value)


def schema_guidance_for(document_type: str | None) -> str:
    normalized = normalize_document_type(document_type)
    return _SCHEMA_GUIDANCE.get(normalized, _SCHEMA_GUIDANCE["other"])
