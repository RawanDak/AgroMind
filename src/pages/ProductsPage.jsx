import "./ProductsPage.css";
import { useNavigate } from "react-router-dom";
import {
  PiArrowLeft,
  PiShareNetwork,
  PiPlant,
} from "react-icons/pi";

function ProductCard({
  name,
  badge,
  ingredient,
  target,
  warning,
  score,
}) {
  return (
    <section className="product-card">
      <div className="product-header">
        <h3>{name}</h3>
        <span>{badge}</span>
      </div>

      <div className="product-info">
        <div>
          <p>ACTIVE INGREDIENT</p>
          <strong>{ingredient}</strong>
        </div>

        <div>
          <p>DISEASE TARGET</p>
          <strong>{target}</strong>
        </div>
      </div>

      <h4>USAGE INSTRUCTIONS</h4>

      <ul>
        <li>Mix 1–2 ml per litre of water</li>
        <li>Spray all leaf surfaces — top and underside</li>
        <li>Apply every 7–10 days during active disease</li>
      </ul>

      <div className="product-warning">
        {warning}
      </div>

      <div className="match-score">
        <p>Match score</p>

        <div className="score-bar">
          <span style={{ width: `${score}%` }}></span>
        </div>

        <strong>{score}%</strong>
      </div>
    </section>
  );
}

function ProductsPage() {
  const navigate = useNavigate();

  const diagnosis = JSON.parse(
    localStorage.getItem("diagnosisResult")
  );

  return (
    <div className="products-page">
      <nav className="products-nav">
        <PiArrowLeft
          className="back-icon"
          onClick={() => navigate(-1)}
        />

        <h1>Recommended products</h1>

        <PiShareNetwork />
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
              {diagnosis?.recommended_products?.length || 0}
              {" "}
              products matched to your diagnosis
            </h2>
          </div>
        </section>

        <div className="products-grid">
          {diagnosis?.recommended_products?.map(
            (product, index) => (
              <div key={index}>
                <p className="product-label">
                  PRODUCT {index + 1}
                </p>

                <ProductCard
                  name={product.name}
                  badge={product.product_type}
                  ingredient={product.ingredients}
                  target={diagnosis.disease_name}
                  warning="Follow label instructions."
                  score={95}
                />
              </div>
            )
          )}
        </div>
      </main>
    </div>
  );
}

export default ProductsPage;