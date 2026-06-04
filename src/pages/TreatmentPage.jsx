import "./TreatmentPage.css";
import { PiArrowLeft, PiShareNetwork } from "react-icons/pi";

function TreatmentPage() {
  return (
    <div className="treatment-page">
      <nav className="treatment-nav">
        <PiArrowLeft />
        <h1>Treatment guide</h1>
        <PiShareNetwork />
      </nav>

      <div className="treatment-dots">
        <span></span>
        <span className="active"></span>
        <span></span>
      </div>

      <main className="treatment-content">
        <section className="disease-summary">
          <p>TOMATO · FUNGAL DISEASE</p>
          <h2>Early Blight — Alternaria solani</h2>
        </section>

        <section className="when-section">
          <div>
            <p>START TREATMENT</p>
            <strong>Within 24 hrs</strong>
          </div>

          <div>
            <p>BEST TIME OF DAY</p>
            <strong>Early morning</strong>
          </div>
        </section>

        <h3 className="section-title">TREATMENT STEPS</h3>

        <section className="steps-list">
          <article className="step-card">
            <span className="step-number">1</span>
            <div>
              <h4>Remove infected leaves</h4>
              <p>
                Carefully remove all leaves showing brown lesions or yellowing,
                starting from the base of the plant upward.
              </p>
              <div className="warning-box">
                Do not compost infected leaves — dispose of them away from the field.
              </div>
            </div>
          </article>

          <article className="step-card">
            <span className="step-number">2</span>
            <div>
              <h4>Apply fungicide spray</h4>
              <p>
                Spray a copper-based or chlorothalonil fungicide evenly on all
                leaves, covering both upper and lower surfaces.
              </p>
              <div className="warning-box">
                Wear gloves and a mask. Avoid spraying during strong wind.
              </div>
            </div>
          </article>

          <article className="step-card">
            <span className="step-number">3</span>
            <div>
              <h4>Monitor and follow up</h4>
              <p>
                Check plants every 2–3 days for new lesions. Repeat treatment
                every 7–10 days unless symptoms improve.
              </p>
              <div className="warning-box">
                Upload a new photo in 7 days so AgroMind can track recovery.
              </div>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}

export default TreatmentPage;