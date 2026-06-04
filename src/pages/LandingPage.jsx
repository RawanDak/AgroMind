import "./LandingPage.css";
import { PiPlant, PiImage, PiCamera } from "react-icons/pi";
import { useNavigate } from "react-router-dom";

function LandingPage() {const navigate = useNavigate();

function handleImageUpload(event) {
  const file = event.target.files[0];

  if (file) {
    const imageUrl = URL.createObjectURL(file);
    localStorage.setItem("cropImage", imageUrl);
    navigate("/diagnosis");
  }
}
  return (
    <div className="phone">
      

      

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
  <button className="action-btn">
    <PiCamera />
    Take a photo now
  </button>

  <button className="action-btn">
    <PiImage />
    Choose from gallery
  </button>
</div>
      </main>

      <div className="home-indicator"></div>
    </div>
  );
}

export default LandingPage;