import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import "./ProfilePage.css";
import { useNavigate } from "react-router-dom";

function ProfilePage() {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("token");

    fetch(`${import.meta.env.VITE_API_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((response) => response.json())
      .then((data) => setUser(data))
      .catch((error) => console.error("Error loading profile:", error));
  }, []);

  if (!user) {
    return <p>Loading profile...</p>;
  }

  return (
    <div className="profile-page">
      <Navbar />

      <main className="profile-card">
        <h1>My Profile</h1>

        <p>
          <strong>Full Name:</strong> {user.full_name}
        </p>

        <p>
          <strong>Email:</strong> {user.email}
        </p>

        <p>
          <strong>Member Since:</strong>{" "}
          {new Date(user.created_at).toLocaleDateString()}
        </p>
        <button className="history-btn" onClick={() => navigate("/history")}>
          View Scan History
      </button>
      </main>
    </div>
  );
}

export default ProfilePage;