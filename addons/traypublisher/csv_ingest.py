import csv
import logging
from typing import Dict, List, Optional

from ayon_api import get_project
from ayon_core.pipeline import registered_host
from ayon_core.pipeline.create import CreateContext

log = logging.getLogger(__name__)


def ingest_csv(filepath: str, project_name: str, folder_path: str):
    """
    Ingest CSV file containing folder and product definitions.
    Expects columns: folder, folderType, folderDescription (optional),
                     product, productType, productVariants
    """
    host = registered_host()
    create_context = CreateContext(host)
    project = get_project(project_name)

    with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            folder_name = row.get('folder', '').strip()
            if not folder_name:
                continue
            folder_type = row.get('folderType', 'Folder').strip()
            folder_description = row.get('folderDescription', '').strip()
            product_name = row.get('product', '').strip()
            product_type = row.get('productType', '').strip()
            product_variants = row.get('productVariants', '').strip()

            # Create folder if not exists
            folder_entity = project.get_folder_by_name(folder_name)
            if not folder_entity:
                folder_entity = project.create_folder(
                    name=folder_name,
                    folder_type=folder_type,
                    description=folder_description,
                    parent_path=folder_path
                )
                log.info(f"Created folder: {folder_name}")
            else:
                # Update description if provided
                if folder_description:
                    folder_entity.set_attrib('description', folder_description)
                    log.info(f"Updated description for folder: {folder_name}")

            if product_name and product_type:
                # Create product
                variants = [v.strip() for v in product_variants.split(',') if v.strip()]
                for variant in variants:
                    create_context.create(
                        product_type=product_type,
                        product_name=product_name,
                        variant=variant,
                        folder_id=folder_entity.id,
                        task_name=None,
                        asset_data={}
                    )
                    log.info(f"Created product: {product_name} variant {variant} in {folder_name}")

    log.info("CSV ingestion completed.")
