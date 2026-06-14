import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import "./ProfilePage.css";

function ProfilePage() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");

    fetch("http://127.0.0.1:8000/auth/me", {
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
      </main>
    </div>
  );
}

export default ProfilePage;