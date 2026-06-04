import "./DiagnosisPage.css";
import { PiPlant, PiArrowLeft, PiShareNetwork } from "react-icons/pi";
import { useNavigate } from "react-router-dom";

function DiagnosisPage() {
  const navigate = useNavigate();
  const imageUrl = localStorage.getItem("cropImage");

  return (
    <div className="diagnosis-page">
      <nav className="nav-bar">
        <PiArrowLeft />
        <h1>Plant Diagnosis</h1>
        <PiShareNetwork />
      </nav>

      <div className="progress-dots">
        <span className="active"></span>
        <span></span>
        <span></span>
      </div>

      <main className="diagnosis-content">
        <section className="photo-card">
          {imageUrl ? (
            <img src={imageUrl} alt="Uploaded crop" className="crop-preview" />
          ) : (
            <>
              <PiPlant />
              <p>Crop photo</p>
            </>
          )}
        </section>

        <section className="info-grid">
          <div>
            <span>CROP TYPE</span>
            <strong>Tomato</strong>
          </div>

          <div>
            <span>GROWTH STAGE</span>
            <strong>Mature</strong>
          </div>
        </section>

        <section className="result-card">
          <p className="eyebrow">DIAGNOSIS RESULT</p>

          <div className="result-header">
            <h2>Early Blight</h2>
            <span className="confidence">High confidence</span>
          </div>

          <div className="tags">
            <span>Fungal disease</span>
            <span>Spreads quickly</span>
          </div>

          <p className="description">
            Caused by the fungus <strong>Alternaria solani</strong>. Affects
            leaves, stems and fruit — most common in warm, humid conditions.
          </p>

          <h3>SYMPTOMS DETECTED</h3>

          <ul>
            <li>Dark brown concentric rings on lower leaves</li>
            <li>Yellow halo surrounding lesions</li>
            <li>Premature leaf drop from base upward</li>
          </ul>

          <div className="severity">
            <span>Severity</span>
            <div className="severity-bar">
              <div></div>
            </div>
            <strong>Moderate</strong>
          </div>
        </section>

        <button
          className="primary-action"
          onClick={() => navigate("/treatment")}
        >
          View treatment guide ↗
        </button>

        <button
          className="secondary-action"
          onClick={() => navigate("/products")}
        >
          Skip to products ↗
        </button>
      </main>
    </div>
  );
}

export default DiagnosisPage;