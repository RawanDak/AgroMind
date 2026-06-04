import "./ProductsPage.css";
import { PiArrowLeft, PiShareNetwork, PiPlant } from "react-icons/pi";

function ProductCard({
  number,
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

      <div className="product-warning">{warning}</div>

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
  return (
    <div className="products-page">
      <nav className="products-nav">
        <PiArrowLeft />
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
            <p>TOMATO · EARLY BLIGHT</p>
            <h2>2 products matched to your diagnosis</h2>
          </div>
        </section>

        <div className="products-grid">
          <div>
            <p className="product-label">PRODUCT 1 OF 2</p>
            <ProductCard
              name="Daconil Weatherstik"
              badge="Best match"
              ingredient="Chlorothalonil 54%"
              target="Early Blight, Septoria"
              warning="⚠️ Wear gloves, mask and eye protection. Do not apply within 7 days of harvest."
              score={94}
            />
          </div>

          <div>
            <p className="product-label">PRODUCT 2 OF 2</p>
            <ProductCard
              name="Kocide 3000"
              badge="Organic-approved"
              ingredient="Copper hydroxide 46.1%"
              target="Early Blight, Downy Mildew"
              warning="⚠️ Avoid spraying during rain or high humidity. Follow label precisely."
              score={81}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default ProductsPage;