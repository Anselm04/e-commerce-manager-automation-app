from ..base import ShopifyResource
from .. import mixins
from .metafield import Metafield
from .variant import Variant
from .image import Image


class Product(ShopifyResource, mixins.Metafields, mixins.Events):
    _singular = "product"
    _plural = "products"

    @classmethod
    def _custom_method_collection_url(cls, method, options=None):
        resource = cls.custom_prefix_get() or cls._plural
        return "%s/%s.json" % (resource, method)

    def price_range(self):
        prices = []
        for variant in self.variants:
            prices.append(float(variant.price))

        if not prices:
            return None

        prices = sorted(prices)
        return {"min": prices[0], "max": prices[-1]}

    def collections(self):
        return self.session.CustomCollection.find(product_id=self.id)

    def smart_collections(self):
        return self.session.SmartCollection.find(product_id=self.id)

    def add_to_collection(self, collection):
        return collection.add_product(self)

    def remove_from_collection(self, collection):
        return collection.remove_product(self)

    @property
    def storefront_url(self):
        """
        Return the URL for the product's storefront page.
        Returns an empty string if the product handle is empty.
        """
        if hasattr(self, 'handle') and self.handle:
            return "https://%s/products/%s" % (self._site_domain(), self.handle)
        return ""

    def _site_domain(self):
        """
        Return the domain of the store, e.g. 'example.myshopify.com'.
        """
        return self.session.url.replace('https://', '').split('/')[0]


class ProductPublication(ShopifyResource):
    _singular = "product_publication"
    _plural = "product_publications"
    _prefix_source = "/publications/$publication_id/"


class ProductVariant(ShopifyResource):
    _singular = "variant"
    _plural = "variants"
    _prefix_source = "/products/$product_id/"

    @classmethod
    def _custom_method_collection_url(cls, method, options=None):
        resource = cls.custom_prefix_get() or cls._plural
        if options is not None and "product_id" in options:
            url = "%s/products/%s/%s/%s.json" % (
                cls.site,
                options["product_id"],
                resource,
                method,
            )
        else:
            url = "%s/%s/%s.json" % (cls.site, resource, method)
        return url
