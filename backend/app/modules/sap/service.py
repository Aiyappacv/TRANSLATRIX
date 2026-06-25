"""
SAP Service
Business logic for SAP S/4HANA integration
"""
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog
from cryptography.fernet import Fernet
import time

from app.modules.sap.models import (
    SAPConnectionConfig,
    SAPPostingPayload,
    SAPPostingResult,
    SAPStatus
)
from app.modules.sap.schemas import (
    SAPConnectionConfigCreate,
    SAPConnectionConfigUpdate,
    SAPPostingRequest,
    SAPPostingStatistics
)
from app.modules.sap.client import SAPClient
from app.modules.sap.adapters.journal_entry import JournalEntryAdapter
from app.modules.sap.adapters.supplier_invoice import SupplierInvoiceAdapter
from app.modules.sap.adapters.customer_invoice import CustomerInvoiceAdapter
from app.modules.entries.models import FinancialEntry
from app.exceptions import NotFoundError, ValidationError, ExternalServiceError
from app.config import settings

logger = structlog.get_logger(__name__)


class SAPService:
    """Service for SAP integration"""

    # Encryption key (in production, this should come from environment/secrets manager)
    ENCRYPTION_KEY = settings.SECRET_KEY[:32].encode().ljust(32, b'0')

    @staticmethod
    def _encrypt_password(password: str) -> str:
        """Encrypt SAP password"""
        cipher = Fernet(Fernet.generate_key())  # In production, use fixed key from secrets
        return cipher.encrypt(password.encode()).decode()

    @staticmethod
    def _decrypt_password(encrypted_password: str) -> str:
        """Decrypt SAP password"""
        # In production, use actual decryption
        # cipher = Fernet(SAPService.ENCRYPTION_KEY)
        # return cipher.decrypt(encrypted_password.encode()).decode()
        return encrypted_password  # Placeholder

    @staticmethod
    def create_sap_config(
        db: Session,
        tenant_id: UUID,
        data: SAPConnectionConfigCreate
    ) -> SAPConnectionConfig:
        """Create SAP connection configuration"""
        # Check if config already exists
        existing_config = db.query(SAPConnectionConfig).filter(
            SAPConnectionConfig.tenant_id == tenant_id
        ).first()

        if existing_config:
            raise ValidationError("SAP configuration already exists for this tenant")

        # Encrypt password
        encrypted_password = SAPService._encrypt_password(data.password)

        # Create configuration
        config = SAPConnectionConfig(
            tenant_id=tenant_id,
            base_url=data.base_url,
            client=data.client,
            username=data.username,
            password_encrypted=encrypted_password,
            environment=data.environment
        )

        db.add(config)
        db.commit()
        db.refresh(config)

        logger.info(
            "sap_config_created",
            config_id=str(config.id),
            tenant_id=str(tenant_id),
            environment=data.environment
        )

        return config

    @staticmethod
    def update_sap_config(
        db: Session,
        tenant_id: UUID,
        data: SAPConnectionConfigUpdate
    ) -> SAPConnectionConfig:
        """Update SAP connection configuration"""
        config = db.query(SAPConnectionConfig).filter(
            SAPConnectionConfig.tenant_id == tenant_id
        ).first()

        if not config:
            raise NotFoundError("SAP configuration not found")

        # Update fields
        if data.base_url:
            config.base_url = data.base_url
        if data.client:
            config.client = data.client
        if data.username:
            config.username = data.username
        if data.password:
            config.password_encrypted = SAPService._encrypt_password(data.password)
        if data.environment:
            config.environment = data.environment
        if data.is_active is not None:
            config.is_active = data.is_active

        db.commit()
        db.refresh(config)

        logger.info("sap_config_updated", config_id=str(config.id), tenant_id=str(tenant_id))

        return config

    @staticmethod
    def get_sap_config(db: Session, tenant_id: UUID) -> SAPConnectionConfig:
        """Get SAP connection configuration"""
        config = db.query(SAPConnectionConfig).filter(
            SAPConnectionConfig.tenant_id == tenant_id
        ).first()

        if not config:
            raise NotFoundError("SAP configuration not found")

        return config

    @staticmethod
    def test_sap_connection(
        db: Session,
        tenant_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """Test SAP connection"""
        config = SAPService.get_sap_config(db, tenant_id)

        # Decrypt password
        password = SAPService._decrypt_password(config.password_encrypted)

        # Create client
        client = SAPClient({
            "base_url": config.base_url,
            "client": config.client,
            "username": config.username,
            "password": password
        })

        # Test connection
        is_connected, error_message = client.test_connection()

        # Update last tested timestamp
        if is_connected:
            config.last_tested_at = datetime.utcnow()
            db.commit()

        logger.info(
            "sap_connection_tested",
            tenant_id=str(tenant_id),
            connected=is_connected,
            error=error_message
        )

        return is_connected, error_message

    @staticmethod
    def post_entry_to_sap(
        db: Session,
        tenant_id: UUID,
        entry_id: UUID,
        user_id: UUID,
        document_type: str = "SA",
        force_repost: bool = False
    ) -> SAPPostingResult:
        """
        Post financial entry to SAP with retry logic and idempotency

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_id: Entry ID to post
            user_id: User ID posting
            document_type: SAP document type
            force_repost: Force repost even if already posted

        Returns:
            SAP posting result
        """
        # Get SAP configuration
        config = SAPService.get_sap_config(db, tenant_id)

        if not config.is_active:
            raise ValidationError("SAP integration is not active")

        # Get financial entry
        entry = db.query(FinancialEntry).filter(
            and_(
                FinancialEntry.id == entry_id,
                FinancialEntry.tenant_id == tenant_id
            )
        ).first()

        if not entry:
            raise NotFoundError(f"Financial entry {entry_id} not found")

        # Check if already posted
        existing_result = db.query(SAPPostingResult).filter(
            and_(
                SAPPostingResult.entry_id == entry_id,
                SAPPostingResult.status == SAPStatus.POSTED
            )
        ).first()

        if existing_result and not force_repost:
            logger.info("entry_already_posted", entry_id=str(entry_id))
            return existing_result

        # Generate idempotency key
        client = SAPClient({
            "base_url": config.base_url,
            "client": config.client,
            "username": config.username,
            "password": SAPService._decrypt_password(config.password_encrypted)
        })

        idempotency_key = client.generate_idempotency_key(
            str(entry_id),
            str(tenant_id)
        )

        # Check if payload already exists
        existing_payload = db.query(SAPPostingPayload).filter(
            SAPPostingPayload.idempotency_key == idempotency_key
        ).first()

        if existing_payload and not force_repost:
            # Return existing result
            existing_result = db.query(SAPPostingResult).filter(
                SAPPostingResult.payload_id == existing_payload.id
            ).first()
            if existing_result:
                return existing_result

        # Select adapter based on document type
        adapter = SAPService._get_adapter(config, document_type)

        # Build payload from entry
        entry_data = SAPService._build_entry_data(entry)
        payload = adapter.build_payload(entry_data)

        # Validate payload
        is_valid, error_message = adapter.validate_payload(payload)
        if not is_valid:
            raise ValidationError(f"Invalid SAP payload: {error_message}")

        # Save payload
        if not existing_payload:
            sap_payload = SAPPostingPayload(
                tenant_id=tenant_id,
                entry_id=entry_id,
                idempotency_key=idempotency_key,
                payload=payload
            )
            db.add(sap_payload)
            db.commit()
            db.refresh(sap_payload)
        else:
            sap_payload = existing_payload

        # Create posting result record
        posting_result = SAPPostingResult(
            tenant_id=tenant_id,
            entry_id=entry_id,
            payload_id=sap_payload.id,
            status=SAPStatus.POSTING,
            posted_by=user_id
        )
        db.add(posting_result)
        db.commit()
        db.refresh(posting_result)

        # Post to SAP with retry logic
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(
                    "posting_to_sap",
                    entry_id=str(entry_id),
                    attempt=attempt + 1,
                    max_retries=max_retries
                )

                # Post to SAP
                sap_response = adapter.post_to_sap(payload)

                # Parse response
                parsed_response = adapter.parse_response(sap_response)

                # Update result
                posting_result.status = SAPStatus.POSTED
                posting_result.sap_document_number = parsed_response.get("document_number")
                posting_result.fiscal_year = str(parsed_response.get("fiscal_year"))
                posting_result.company_code = parsed_response.get("company_code")
                posting_result.sap_response = sap_response
                posting_result.posted_at = datetime.utcnow()

                db.commit()
                db.refresh(posting_result)

                logger.info(
                    "sap_posting_successful",
                    entry_id=str(entry_id),
                    document_number=posting_result.sap_document_number
                )

                return posting_result

            except Exception as e:
                logger.error(
                    "sap_posting_failed",
                    entry_id=str(entry_id),
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    # Final failure
                    posting_result.status = SAPStatus.FAILED
                    posting_result.error_code = "POSTING_FAILED"
                    posting_result.error_message = str(e)
                    db.commit()
                    db.refresh(posting_result)

                    raise ExternalServiceError(f"SAP posting failed after {max_retries} attempts: {str(e)}")

    @staticmethod
    def batch_post_entries(
        db: Session,
        tenant_id: UUID,
        entry_ids: List[UUID],
        user_id: UUID,
        document_type: str = "SA"
    ) -> Dict[str, Any]:
        """Batch post multiple entries to SAP"""
        results = {
            "total": len(entry_ids),
            "successful": 0,
            "failed": 0,
            "results": []
        }

        for entry_id in entry_ids:
            try:
                result = SAPService.post_entry_to_sap(
                    db=db,
                    tenant_id=tenant_id,
                    entry_id=entry_id,
                    user_id=user_id,
                    document_type=document_type
                )
                results["successful"] += 1
                results["results"].append(result)

            except Exception as e:
                logger.error("batch_posting_failed", entry_id=str(entry_id), error=str(e))
                results["failed"] += 1

        return results

    @staticmethod
    def get_posting_result(
        db: Session,
        tenant_id: UUID,
        result_id: UUID
    ) -> SAPPostingResult:
        """Get SAP posting result"""
        result = db.query(SAPPostingResult).filter(
            and_(
                SAPPostingResult.id == result_id,
                SAPPostingResult.tenant_id == tenant_id
            )
        ).first()

        if not result:
            raise NotFoundError(f"SAP posting result {result_id} not found")

        return result

    @staticmethod
    def get_posting_statistics(
        db: Session,
        tenant_id: UUID
    ) -> SAPPostingStatistics:
        """Get SAP posting statistics"""
        query = db.query(SAPPostingResult).filter(SAPPostingResult.tenant_id == tenant_id)

        total_postings = query.count()
        pending = query.filter(SAPPostingResult.status == SAPStatus.PENDING).count()
        posting = query.filter(SAPPostingResult.status == SAPStatus.POSTING).count()
        posted = query.filter(SAPPostingResult.status == SAPStatus.POSTED).count()
        failed = query.filter(SAPPostingResult.status == SAPStatus.FAILED).count()

        success_rate = (posted / total_postings * 100) if total_postings > 0 else 0

        return SAPPostingStatistics(
            total_postings=total_postings,
            pending=pending,
            posting=posting,
            posted=posted,
            failed=failed,
            success_rate=round(success_rate, 2)
        )

    @staticmethod
    def _get_adapter(config: SAPConnectionConfig, document_type: str):
        """Get appropriate SAP adapter based on document type"""
        password = SAPService._decrypt_password(config.password_encrypted)

        adapter_config = {
            "base_url": config.base_url,
            "client": config.client,
            "username": config.username,
            "password": password
        }

        if document_type in ["SA", "JE"]:
            return JournalEntryAdapter(adapter_config)
        elif document_type == "KR":  # Supplier invoice
            return SupplierInvoiceAdapter(adapter_config)
        elif document_type == "DR":  # Customer invoice
            return CustomerInvoiceAdapter(adapter_config)
        else:
            return JournalEntryAdapter(adapter_config)

    @staticmethod
    def _build_entry_data(entry: FinancialEntry) -> Dict[str, Any]:
        """Build entry data for SAP posting"""
        # This would extract data from FinancialEntry model
        # For now, return placeholder structure
        return {
            "header": {
                "company_code": "1000",  # Would come from entry or config
                "document_date": entry.created_at,
                "posting_date": datetime.utcnow(),
                "document_type": "SA",
                "header_text": f"Auto-posted from TRANSLATRIX - Entry {entry.id}",
                "reference_id": str(entry.id)
            },
            "line_items": entry.extracted_data.get("line_items", [])
        }
