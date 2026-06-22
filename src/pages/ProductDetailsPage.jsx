import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import "./ProductDetailsPage.css";

function ProductDetailsPage() {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/products/${productId}`)
      .then((response) => response.json())
      .then((data) => setProduct(data))
      .catch((error) => console.error("Error loading product:", error));
  }, [productId]);

  if (!product) {
    return <p>Loading product...</p>;
  }

  return (
    <div className="product-details-page">
      <Navbar />

      <main className="product-details-card">
        <h1>{product.name}</h1>

        <p>
          <strong>Type:</strong> {product.product_type}
        </p>
        <p>
          <strong>Crops:</strong> {product.crops}
        </p>
        <p>
          <strong>Ingredients:</strong> {product.ingredients}
        </p>
        <p>
          <strong>Usage:</strong> {product.usage}
        </p>
        <p>
          <strong>Dilution:</strong> {product.dilution}
        </p>
      </main>
    </div>
  );
}

export default ProductDetailsPage;
