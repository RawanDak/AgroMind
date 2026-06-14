import { Link } from "react-router-dom";
import "./ProductCard.css";

function ProductCard({ product }) {
  const handleAddToCart = () => {
  const token = localStorage.getItem("token");

  if (!token) {
    alert("Please login first.");
    window.location.href = "/login";
    return;
  }

  const currentCart =
    JSON.parse(localStorage.getItem("cart")) || [];

  const existingItem = currentCart.find(
    (item) => item.product_id === product.product_id
  );

  let updatedCart;

  if (existingItem) {
    updatedCart = currentCart.map((item) =>
      item.product_id === product.product_id
        ? { ...item, quantity: (item.quantity || 1) + 1 }
        : item
    );
  } else {
    updatedCart = [
      ...currentCart,
      {
        ...product,
        quantity: 1,
      },
    ];
  }

  localStorage.setItem(
    "cart",
    JSON.stringify(updatedCart)
  );

  alert(`${product.name} added to cart`);
};
  return (
    <div className="product-card">
      <h3>{product.name}</h3>

      <p>
        <strong>Type:</strong> {product.product_type}
      </p>

      <p>
        <strong>Crops:</strong> {product.crops}
      </p>

      <p>
        <strong>Spec:</strong> {product.spec}
      </p>

      <div className="product-actions">
        <Link
          className="details-btn"
          to={`/products/${product.product_id}`}
        >
          Learn More
        </Link>

        <button className="cart-btn" onClick={handleAddToCart}>
          Add to Cart
        </button>
      </div>
    </div>
  );
}

export default ProductCard;