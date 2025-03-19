import shopify
import unittest
import json
from test.test_helper import TestCase
from pyactiveresource.activeresource import ActiveResource
from shopify import Product, Image, Variant
from shopify.collection import PaginatedCollection


class TestProduct(TestCase):
    def setUp(self):
        super(TestProduct, self).setUp()
        self.fake("products/632910392", body=self.load_fixture("product"))
        self.product = Product.find(632910392)
        
        # Setup for testing products with and without handles
        self.fake("products/product_with_handle", body=json.dumps({
            "product": {
                "id": 123456789,
                "title": "Product with Handle",
                "handle": "product-with-handle"
            }
        }))
        self.fake("products/product_without_handle", body=json.dumps({
            "product": {
                "id": 987654321,
                "title": "Product without Handle",
                "handle": ""
            }
        }))
        
        # Load these test products
        self.product_with_handle = Product.find("product_with_handle")
        self.product_without_handle = Product.find("product_without_handle")

    def test_get_products_with_handle(self):
        """Test that products with a handle return the correct storefront URL."""
        self.assertEqual(self.product_with_handle.storefront_url, 
                         f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/product-with-handle")

    def test_get_products_without_handle(self):
        """Test that products without a handle return an empty string for storefront URL."""
        self.assertEqual(self.product_without_handle.storefront_url, "")

    def test_get_product(self):
        self.assertEqual(632910392, self.product.id)
        self.assertEqual("IPod Nano - 8GB", self.product.title)
        # Test storefront_url for regular product with handle
        if hasattr(self.product, 'handle') and self.product.handle:
            expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/{self.product.handle}"
            self.assertEqual(self.product.storefront_url, expected_url)

    def test_get_products(self):
        self.fake("products", body=self.load_fixture("products"))
        products = Product.find()
        self.assertEqual(2, len(products))
        
        # Test storefront_url for each product
        for product in products:
            if hasattr(product, 'handle') and product.handle:
                expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/{product.handle}"
                self.assertEqual(product.storefront_url, expected_url)
            else:
                self.assertEqual(product.storefront_url, "")

    def test_get_products_paginated(self):
        self.fake(
            "products",
            url_suffix="?limit=2",
            extension="",
            body=self.load_fixture("products"),
            headers={"Link": '<https://www.example.com/api/unstable/products.json?page_info=abc&limit=2>; rel="next"'},
        )
        self.fake(
            "products",
            url_suffix="?page_info=abc&limit=2",
            extension="",
            body=self.load_fixture("products"),
        )
        products = PaginatedCollection(Product.find(limit=2))
        
        # Test handling of pagination
        with self.assertRaises(StopIteration):
            while True:
                product = next(products)
                if hasattr(product, 'handle') and product.handle:
                    expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/{product.handle}"
                    self.assertEqual(product.storefront_url, expected_url)
                else:
                    self.assertEqual(product.storefront_url, "")

    def test_get_product_namespaced(self):
        namespaced_product = {
            "product": {
                "id": 632910392,
                "title": "IPod Nano - 8GB",
                "handle": "ipod-nano"
            }
        }
        self.fake("products/632910392", body=json.dumps(namespaced_product))
        product = Product.find(632910392)
        
        # Test storefront_url with namespaced product
        expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/ipod-nano"
        self.assertEqual(product.storefront_url, expected_url)

    def test_create_product(self):
        self.fake(
            "products", method="POST", code=201, body=self.load_fixture("product")
        )
        product = Product()
        product.title = "Tennis Racket"
        product.save()
        self.assertEqual("IPod Nano - 8GB", product.title)
        
        # Test storefront_url after creation
        if hasattr(product, 'handle') and product.handle:
            expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/{product.handle}"
            self.assertEqual(product.storefront_url, expected_url)

    def test_update_product(self):
        self.fake(
            "products/632910392",
            method="PUT",
            code=201,
            body=self.load_fixture("product"),
        )
        product = Product({"id": 632910392})
        product.title = "New and Improved"
        product.save()
        self.assertEqual("IPod Nano - 8GB", product.title)
        
        # Test storefront_url after update
        if hasattr(product, 'handle') and product.handle:
            expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/{product.handle}"
            self.assertEqual(product.storefront_url, expected_url)

    def test_cannot_update_a_product_and_get_errors(self):
        self.fake(
            "products/632910392",
            method="PUT",
            code=422,
            body=self.load_fixture("product_error"),
        )
        product = Product.find(632910392)
        product.title = "IPod Nano - 8GB"
        self.assertFalse(product.save())
        self.assertEqual(1, len(product.errors.full_messages()))
        self.assertTrue("failed" in product.errors.full_messages()[0])
        
        # Test storefront_url after failed update
        if hasattr(product, 'handle') and product.handle:
            expected_url = f"https://{self.session.url.replace('https://', '').split('/')[0]}/products/{product.handle}"
            self.assertEqual(product.storefront_url, expected_url)

    def test_delete_product(self):
        self.fake("products/632910392", method="DELETE", body="destroyed")
        product = Product.find(632910392)
        self.assertEqual(True, product.destroy())

    def test_price_range(self):
        product_response = json.loads(self.load_fixture("product"))
        prices = [float(variant["price"]) for variant in product_response["product"]["variants"]]
        prices = sorted(prices)
        product = Product(product_response["product"])
        self.assertEqual({"min": prices[0], "max": prices[-1]}, product.price_range())

    def test_price_range_no_prices(self):
        product_response = json.loads(self.load_fixture("product"))
        product_response["product"]["variants"] = []
        product = Product(product_response["product"])
        self.assertEqual(None, product.price_range())

    def test_product_collection(self):
        product_response = json.loads(self.load_fixture("product"))
        product = Product(product_response["product"])
        for i, variant in enumerate(product.variants):
            self.assertTrue(isinstance(variant, Variant),
                            "variant #%d is no Variant" % i)

    def test_product_add_metafields(self):
        self.fake(
            "products/632910392/metafields",
            method="POST",
            code=201,
            body=self.load_fixture("metafield"),
            headers={"Content-type": "application/json"},
        )
        metafield = self.product.add_metafield(
            Metafield({"namespace": "contact", "key": "email", "value": "123@example.com", "value_type": "string"})
        )
        self.assertEqual("contact", metafield.namespace)
        self.assertEqual("email", metafield.key)
        self.assertEqual("123@example.com", metafield.value)

    def test_empty_product_collections_with_non_empty_response(self):
        self.fake(
            "collections.json?product_id=632910392",
            body=self.load_fixture("collections"),
        )
        collections = self.product.collections()
        self.assertEqual(2, len(collections))
        
    def test_empty_product_collections_with_empty_response(self):
        self.fake(
            "collections.json?product_id=632910392",
            body='{"custom_collections":[],"smart_collections":[]}',
        )
        collections = self.product.collections()
        self.assertEqual(0, len(collections))

    def test_empty_product_smart_collections_with_non_empty_response(self):
        self.fake(
            "smart_collections.json?product_id=632910392",
            body=self.load_fixture("smart_collections"),
        )
        collections = self.product.smart_collections()
        self.assertEqual(2, len(collections))

    def test_empty_product_smart_collections_with_empty_response(self):
        self.fake(
            "smart_collections.json?product_id=632910392",
            body='{"smart_collections":[]}',
        )
        collections = self.product.smart_collections()
        self.assertEqual(0, len(collections))
