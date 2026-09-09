"""Product catalog application use cases."""

from nexo_vending.application.products.activate_product import ActivateProduct
from nexo_vending.application.products.change_product_barcode import ChangeProductBarcode
from nexo_vending.application.products.create_product import CreateProduct
from nexo_vending.application.products.deactivate_product import DeactivateProduct
from nexo_vending.application.products.find_product_by_barcode import FindProductByBarcode
from nexo_vending.application.products.update_product import UpdateProduct

__all__ = [
    "ActivateProduct",
    "ChangeProductBarcode",
    "CreateProduct",
    "DeactivateProduct",
    "FindProductByBarcode",
    "UpdateProduct",
]
