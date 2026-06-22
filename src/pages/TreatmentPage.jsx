import "./TreatmentPage.css";
import { PiArrowLeft, PiShoppingCart } from "react-icons/pi";
import { Link, useNavigate } from "react-router-dom";

function TreatmentPage() {
  const diagnosis = JSON.parse(localStorage.getItem("diagnosisResult"));
  const navigate = useNavigate();

  const cart = JSON.parse(localStorage.getItem("cart")) || [];

  const cartCount = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);
  return (
    <div className="treatment-page">
      <nav className="treatment-nav">
        <PiArrowLeft className="back-icon" onClick={() => navigate(-1)} />

        <h1>Treatment guide</h1>

        <Link to="/cart" className="cart-icon-container">
          <PiShoppingCart />

          {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
        </Link>
      </nav>

      <div className="treatment-dots">
        <span></span>
        <span className="active"></span>
        <span></span>
      </div>

      <main className="treatment-content">
        <section className="disease-summary">
          <p>
            {diagnosis?.crop} · {diagnosis?.disease_type}
          </p>
          <h2>{diagnosis?.disease_name}</h2>
        </section>

        <h3 className="section-title">TREATMENT STEPS</h3>

        <section className="steps-list">
          {diagnosis?.treatment?.map((step, index) => (
            <article className="step-card" key={index}>
              <span className="step-number">{index + 1}</span>

              <div>
                <p>{step}</p>
              </div>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}

export default TreatmentPage;
