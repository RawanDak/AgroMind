import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import "./HistoryDetailsPage.css";

function HistoryDetailsPage() {
  const { diagnosisId } = useParams();
  const [diagnosis, setDiagnosis] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");

    fetch(`${import.meta.env.VITE_API_URL}/${diagnosisId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((response) => response.json())
      .then((data) => setDiagnosis(data));
  }, [diagnosisId]);

  if (!diagnosis) {
    return <p>Loading...</p>;
  }

  return (
    <>
      <Navbar />

      <div className="history-details">
        <h1> Crop: {diagnosis.crop}</h1>
        <h2>Disease: {diagnosis.disease_name}</h2>

        <p>
          <strong>Confidence:</strong> {diagnosis.confidence}
        </p>
        <p>
          <strong>Severity:</strong> {diagnosis.severity}
        </p>
        <p>
          <strong>Disease Type:</strong> {diagnosis.disease_type}
        </p>

        <h3>Explanation</h3>
        <p>{diagnosis.explanation}</p>

        <h3>Treatment</h3>
        <p>{diagnosis.treatment}</p>

        <h3>Prevention</h3>
        <p>{diagnosis.prevention}</p>

        <h3>Symptoms</h3>
        <ul>
          {diagnosis.symptoms?.map((symptom, index) => (
            <li key={index}>{symptom}</li>
          ))}
        </ul>
        <h3>Recommended Products</h3>

        {diagnosis.recommended_products?.length > 0 ? (
          <div className="history-products-list">
            {diagnosis.recommended_products.map((product, index) => (
              <div className="history-product-card" key={index}>
                <p>{product.name}</p>
              </div>
            ))}
          </div>
        ) : (
          <p>No recommended products saved.</p>
        )}
      </div>
    </>
  );
}

export default HistoryDetailsPage;
