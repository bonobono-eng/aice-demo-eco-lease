"""Test pipeline without LLM - Basic functionality test"""

import sys
from pathlib import Path
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

from pipelines.ingest import DocumentIngestor
from pipelines.normalize import FMTNormalizer
from pipelines.classify import Classifier
from pipelines.estimate import EstimateGenerator
from pipelines.export import EstimateExporter


def test_basic_pipeline():
    """Test the basic pipeline without LLM"""

    # Test file
    test_file = "test-files/仕様書【都立山崎高等学校仮設校舎等の借入れ】.pdf"

    if not Path(test_file).exists():
        logger.error(f"Test file not found: {test_file}")
        return False

    logger.info("=" * 60)
    logger.info("Testing Ecolease PoC Pipeline")
    logger.info("=" * 60)

    try:
        # Step 1: Ingest
        logger.info("\n[Step 1] Document Ingestion")
        ingestor = DocumentIngestor()
        ingested_data = ingestor.ingest(test_file)

        logger.info(f"✓ Pages: {len(ingested_data.get('pages', []))}")
        logger.info(f"✓ Tables: {len(ingested_data.get('tables', []))}")
        logger.info(f"✓ Images: {len(ingested_data.get('images', []))}")
        logger.info(f"✓ Text length: {len(ingested_data.get('text', ''))} chars")

        # Extract info
        project_info = ingestor.extract_project_info(ingested_data)
        building_specs_raw = ingestor.extract_building_specs(ingested_data)

        logger.info(f"✓ Project: {project_info.get('project_name', 'N/A')}")
        logger.info(f"✓ Building specs: {len(building_specs_raw)} items")

        # Step 2: Normalize
        logger.info("\n[Step 2] FMT Normalization")
        normalizer = FMTNormalizer()

        # Build building specs
        building_specs = [{
            'building_name': project_info.get('project_name', '建物'),
            'building_type': '仮設校舎',
            'rooms': building_specs_raw
        }] if building_specs_raw else []

        fmt_doc = normalizer.normalize(ingested_data, project_info, building_specs)
        fmt_doc = normalizer.update_fmt_with_requirements(fmt_doc)

        logger.info(f"✓ FMT version: {fmt_doc.fmt_version}")
        logger.info(f"✓ Project: {fmt_doc.project_info.project_name}")
        logger.info(f"✓ Facility type: {fmt_doc.facility_type.value}")
        logger.info(f"✓ Buildings: {len(fmt_doc.building_specs)}")

        # Step 3: Classify
        logger.info("\n[Step 3] Classification")
        classifier = Classifier()
        fmt_doc = classifier.classify(fmt_doc)

        logger.info(f"✓ Disciplines detected: {len(fmt_doc.disciplines)}")
        for discipline in fmt_doc.disciplines:
            logger.info(f"  - {discipline.value}")

        # Step 4: Generate estimate (without LLM)
        logger.info("\n[Step 4] Estimate Generation (Rule-based)")
        generator = EstimateGenerator(use_llm=False)
        fmt_doc = generator.generate(fmt_doc)

        logger.info(f"✓ Estimate items: {len(fmt_doc.estimate_items)}")

        # Calculate total
        total = sum(item.amount or 0 for item in fmt_doc.estimate_items if item.level == 0)
        logger.info(f"✓ Total amount: ¥{total:,.0f}")

        # Show sample items
        logger.info("\nSample items:")
        for item in fmt_doc.estimate_items[:10]:
            indent = "  " * item.level
            logger.info(f"{indent}{item.item_no}: {item.name} - ¥{item.amount:,.0f}" if item.amount else f"{indent}{item.item_no}: {item.name}")

        # Step 5: Export
        logger.info("\n[Step 5] Export to Excel")
        exporter = EstimateExporter()
        output_path = exporter.export_to_excel(fmt_doc, "test_output.xlsx")

        logger.info(f"✓ Exported to: {output_path}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ Test PASSED - All steps completed successfully")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"\n❌ Test FAILED: {str(e)}")
        logger.exception("Full traceback:")
        return False


if __name__ == "__main__":
    success = test_basic_pipeline()
    sys.exit(0 if success else 1)
