import "./DiagnosisToolPage.css";
import { PiPlant, PiImage, PiCamera } from "react-icons/pi";
import { useNavigate } from "react-router-dom";
import { useRef } from "react";
import { useState } from "react";
import Navbar from "../components/Navbar";

function DiagnosisToolPage() {
  const navigate = useNavigate();

  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);
  const [loading, setLoading] = useState(false);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <h2>Analyzing your crop...</h2>
      </div>
    );
  }

  async function handleImageUpload(event) {
    const file = event.target.files[0];

    if (!file) return;

    setLoading(true);

    const imageUrl = URL.createObjectURL(file);
    localStorage.setItem("cropImage", imageUrl);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem("token");

      const response = await fetch("http://localhost:8000/diagnose", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      console.log("API RESULT:", data);

      localStorage.setItem("diagnosisResult", JSON.stringify(data));

      navigate("/diagnosis");
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <div className="phone">
      <Navbar />
      <section className="hero">
        <div className="logo-circle">
          <PiPlant />
        </div>

        <h1>What's wrong with your crop?</h1>

        <p>
          Take a photo or upload one.
          <br />
          AI will diagnose it in seconds.
        </p>
      </section>

      <main className="content">
        <label className="upload-card">
          <PiImage className="upload-icon" />
          <h3>Upload a crop photo</h3>
          <p>JPG or PNG · Tap to browse</p>

          <input
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            hidden
          />
        </label>

        <div className="button-row">
          <button
            type="button"
            className="action-btn"
            onClick={() => cameraInputRef.current.click()}
          >
            <PiCamera />
            Take a photo now
          </button>

          <button
            type="button"
            className="action-btn"
            onClick={() => galleryInputRef.current.click()}
          >
            <PiImage />
            Choose from gallery
          </button>

          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleImageUpload}
            hidden
          />

          <input
            ref={galleryInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            hidden
          />
        </div>
      </main>

      <div className="home-indicator"></div>
    </div>
  );
}

export default DiagnosisToolPage;
