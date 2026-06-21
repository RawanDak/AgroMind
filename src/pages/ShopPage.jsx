import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import ProductCard from "../components/ProductCard";
import "./ShopPage.css";

import {
  PiPlant,
  PiSquaresFour,
  PiBug,
  PiDrop,
  PiLeaf,
  PiSun,
  PiCircle,
} from "react-icons/pi";

function ShopPage() {
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const categories = [
    { name: "All", icon: <PiSquaresFour /> },
    { name: "Fertilizer", icon: <PiSun /> },
    { name: "Fungus", icon: <PiCircle /> },
    { name: "Bacterial", icon: <PiDrop /> },
    { name: "Assisted Growth", icon: <PiLeaf /> },
    { name: "Pesticide", icon: <PiBug /> },
  ];

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/products`)
      .then((response) => response.json())
      .then((data) => {
        setProducts(data);
      })
      .catch((error) => {
        console.error("Error loading products:", error);
      });
  }, []);

  const filteredProducts = products.filter((product) => {
  const name = product.name?.toLowerCase() || "";
  const type = product.product_type?.toLowerCase() || "";
  const search = searchTerm.toLowerCase();

  const matchesSearch =
    name.includes(search) ||
    type.includes(search);

  let matchesCategory = true;

  if (selectedCategory === "Fertilizer") {
    matchesCategory = name.includes("fertilizer");
  } else if (selectedCategory === "Fungus") {
    matchesCategory =
      name.includes("fungus") ||
      name.includes("fungal");
  } else if (selectedCategory === "Bacterial") {
    matchesCategory =
      name.includes("bacteria") ||
      name.includes("bacterial");
  } else if (selectedCategory === "Assisted Growth") {
    matchesCategory =
      type.includes("assisted growth");
  } else if (selectedCategory === "Pesticide") {
    matchesCategory =
      type.includes("pesticide");
  }

  return matchesSearch && matchesCategory;
});

  return (
    <div className="shop-page">
      <Navbar />

      <section className="shop-hero">
        <div className="hero-text">
          <h1>Trusted solutions to protect your crops and harvest</h1>
          <p>AI-powered crop care and pesticide recommendations.</p>
          <button className="hero-btn">Shop Now</button>
        </div>

        <PiPlant className="hero-icon" />
      </section>

      <section className="category-section">
        <h2>Shop by category</h2>
        <p>Discover products classified by what is affecting your crops.</p>

        <div className="categories">
          {categories.map((category) => (
            <div
              className={
                selectedCategory === category.name
                  ? "category-card active"
                  : "category-card"
              }
              key={category.name}
              onClick={() => setSelectedCategory(category.name)}
            >
              <h3>{category.name}</h3>
              <div className="category-icon">{category.icon}</div>
            </div>
          ))}
        </div>
      </section>

        <div className="search-container">
  <input
    type="text"
    placeholder="Search products..."
    value={searchTerm}
    onChange={(e) => setSearchTerm(e.target.value)}
    className="search-input"
  />
</div>
      <section className="products-section">
        <h2>Products</h2>
        <p>
          Showing {filteredProducts.length} products for:{" "}
          {selectedCategory}
        </p>

        <div className="product-grid">
          {filteredProducts.map((product) => (
            <ProductCard
              key={product.product_id}
              product={product}
            />
          ))}
        </div>
      </section>

      <footer className="footer">
        <div className="footer-brand">
          <PiPlant />
          <span>AgroMind store</span>
        </div>

        <p>© 2026 AgroMind store. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default ShopPage;