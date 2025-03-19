import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Image from 'next/image';
import { Product } from '../types/Product';
import { StarIcon } from '@heroicons/react/solid';
import { ShoppingCartIcon, HeartIcon, XCircleIcon } from '@heroicons/react/outline';

interface ProductDetailsProps {
  searchProducts: Product[];
  setSearchProducts: React.Dispatch<React.SetStateAction<Product[]>>;
  isAuthenticated: boolean;
}

const ProductDetails: React.FC<ProductDetailsProps> = ({
  searchProducts,
  setSearchProducts,
  isAuthenticated
}) => {
  const router = useRouter();
  const [selectedProducts, setSelectedProducts] = useState<Product[]>([]);

  useEffect(() => {
    // Set selected products from search products when component mounts
    if (searchProducts && searchProducts.length > 0) {
      setSelectedProducts(searchProducts);
    }
  }, [searchProducts]);

  const handleRemoveProduct = (productId: string) => {
    setSelectedProducts(selectedProducts.filter(product => product.id !== productId));
    setSearchProducts(searchProducts.filter(product => product.id !== productId));
    
    // If all products are removed, go back to home page
    if (selectedProducts.length <= 1) {
      router.push('/');
    }
  };

  const handleClearAll = () => {
    setSelectedProducts([]);
    setSearchProducts([]);
    router.push('/');
  };

  const handleAddToCart = (product: Product) => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    
    // Add to cart logic would go here
    console.log('Added to cart:', product.title);
  };

  const handleAddToWishlist = (product: Product) => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    
    // Add to wishlist logic would go here
    console.log('Added to wishlist:', product.title);
  };

  if (selectedProducts.length === 0) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">No Products Selected</h1>
          <button 
            onClick={() => router.push('/')}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            Browse Products
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Product Details</h1>
      
      {selectedProducts.map((product, index) => (
        <div key={product.id} className="bg-white rounded-lg shadow-lg mb-8 overflow-hidden">
          <div className="flex flex-col md:flex-row">
            <div className="md:w-1/3 p-4 flex justify-center">
              <div className="relative h-64 w-64">
                <Image 
                  src={product.image} 
                  alt={product.title}
                  layout="fill"
                  objectFit="contain"
                  className="rounded-lg"
                />
              </div>
            </div>
            
            <div className="md:w-2/3 p-6">
              <div className="flex justify-between items-start">
                <h2 className="text-2xl font-bold text-gray-800 mb-2">{product.title}</h2>
                <button 
                  onClick={() => handleRemoveProduct(product.id)} 
                  className="text-red-500 hover:text-red-700"
                  title="Remove product"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>
              
              <div className="flex items-center mb-4">
                {[...Array(5)].map((_, i) => (
                  <StarIcon 
                    key={i} 
                    className={`h-5 w-5 ${i < Math.round(product.rating.rate) ? 'text-yellow-400' : 'text-gray-300'}`} 
                  />
                ))}
                <span className="text-gray-600 ml-2">({product.rating.count} reviews)</span>
              </div>
              
              <p className="text-gray-600 mb-4">{product.description}</p>
              
              <div className="mb-4">
                <h3 className="text-lg font-semibold mb-2">Product Details:</h3>
                <ul className="list-disc pl-5 text-gray-600">
                  <li>Category: {product.category}</li>
                  <li>In Stock: Yes</li>
                  <li>Shipping: Free standard shipping</li>
                </ul>
              </div>
              
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Support Information:</h3>
                <ul className="list-disc pl-5 text-gray-600">
                  <li>30-day return policy</li>
                  <li>1-year warranty</li>
                  <li>24/7 customer support</li>
                </ul>
              </div>
              
              <div className="flex flex-col sm:flex-row items-center justify-between mt-6">
                <span className="text-2xl font-bold text-gray-800 mb-4 sm:mb-0">${product.price.toFixed(2)}</span>
                <div className="flex space-x-3">
                  <button 
                    onClick={() => handleAddToWishlist(product)}
                    className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100 transition-colors"
                  >
                    <HeartIcon className="h-5 w-5 mr-2 text-red-500" />
                    <span>Wishlist</span>
                  </button>
                  
                  <button 
                    onClick={() => handleAddToCart(product)}
                    className="flex items-center justify-center px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                  >
                    <ShoppingCartIcon className="h-5 w-5 mr-2" />
                    <span>Add to Cart</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
      
      {selectedProducts.length > 1 && (
        <div className="flex justify-center mt-8 mb-12">
          <button 
            onClick={handleClearAll}
            className="px-6 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
          >
            Clear All
          </button>
        </div>
      )}
    </div>
  );
};

export default ProductDetails;
