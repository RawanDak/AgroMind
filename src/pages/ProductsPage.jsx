import "./ProductsPage.css";
import { Link, useNavigate } from "react-router-dom";
import { PiArrowLeft, PiShoppingCart, PiPlant } from "react-icons/pi";

function ProductCard({ product, target }) {
  const handleAddToCart = async () => {
    const token = localStorage.getItem("token");

    if (!token) {
      alert("Please login first.");
      window.location.href = "/login";
      return;
    }

    const response = await fetch(
      `${import.meta.env.VITE_API_URL}/products/${product.product_id}`,
    );

    const fullProduct = await response.json();

    const currentCart = JSON.parse(localStorage.getItem("cart")) || [];

    const existingItem = currentCart.find(
      (item) => item.product_id === fullProduct.product_id,
    );

    let updatedCart;

    if (existingItem) {
      updatedCart = currentCart.map((item) =>
        item.product_id === fullProduct.product_id
          ? { ...item, quantity: (item.quantity || 1) + 1 }
          : item,
      );
    } else {
      updatedCart = [
        ...currentCart,
        {
          ...fullProduct,
          quantity: 1,
        },
      ];
    }

    localStorage.setItem("cart", JSON.stringify(updatedCart));

    alert(`${fullProduct.name} added to cart`);
  };

  return (
    <section className="product-card">
      <div className="product-header">
        <h3>{product.name}</h3>
        <span>{product.product_type}</span>
      </div>

      <div className="product-info">
        <div>
          <p>ACTIVE INGREDIENT</p>
          <strong>{product.ingredients || "Not specified"}</strong>
        </div>

        <div>
          <p>DISEASE TARGET</p>
          <strong>{target}</strong>
        </div>
      </div>

      <h4>USAGE INSTRUCTIONS</h4>

      <p className="usage-text">
        {product.how_to_use || "No usage instructions available."}
      </p>

      <div className="product-warning">
        {product.caution || "Follow label instructions."}
      </div>

      

      <button className="cart-btn" onClick={handleAddToCart}>
        Add to Cart
      </button>
    </section>
  );
}

function ProductsPage() {
  const navigate = useNavigate();

  const diagnosis = JSON.parse(localStorage.getItem("diagnosisResult"));

  const cart = JSON.parse(localStorage.getItem("cart")) || [];

  const cartCount = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);

  return (
    <div className="products-page">
      <nav className="products-nav">
        <PiArrowLeft className="back-icon" onClick={() => navigate(-1)} />

        <h1>Recommended products</h1>

        <Link to="/cart" className="cart-icon-container">
          <PiShoppingCart />

          {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
        </Link>
      </nav>

      <div className="products-dots">
        <span></span>
        <span></span>
        <span className="active"></span>
      </div>

      <main className="products-content">
        <section className="products-summary">
          <PiPlant />

          <div>
            <p>
              {diagnosis?.crop?.toUpperCase()}
              {" · "}
              {diagnosis?.disease_name}
            </p>

            <h2>
              {diagnosis?.recommended_products?.length || 0} products matched to
              your diagnosis
            </h2>
          </div>
        </section>

        <div className="products-grid">
          {diagnosis?.recommended_products?.map((product, index) => (
            <div key={index}>
              <p className="product-label">PRODUCT {index + 1}</p>

              <ProductCard product={product} target={diagnosis.disease_name} />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

export default ProductsPage;
