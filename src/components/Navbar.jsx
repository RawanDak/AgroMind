import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  PiPlant,
  PiMagnifyingGlass,
  PiUser,
  PiShoppingCart,
} from "react-icons/pi";
import "./Navbar.css";

function Navbar() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [cartCount, setCartCount] = useState(0);

  const token = localStorage.getItem("token");
  const isLoggedIn = !!token;

  useEffect(() => {
    const cart = JSON.parse(localStorage.getItem("cart")) || [];

    const totalItems = cart.reduce(
      (sum, item) => sum + (item.quantity || 1),
      0,
    );

    setCartCount(totalItems);

    if (!token) return;

    fetch("http://127.0.0.1:8000/auth/me", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((response) => response.json())
      .then((data) => {
        setUser(data);
      })
      .catch((error) => {
        console.error("Error loading user:", error);
      });
  }, [token]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUser(null);
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <Link to="/" className="brand">
        <PiPlant />
        <span>AgroMind store</span>
      </Link>

      <div className="nav-links">
        <Link to="/">Shop</Link>
        <Link to="/tool">AI Diagnosis Tool</Link>

        {!isLoggedIn ? (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        ) : (
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        )}
      </div>

      <div className="nav-icons">
        {isLoggedIn ? (
          <div className="profile-section">
            <PiUser />
            <Link to="/profile" className="user-name">
              {user?.full_name || user?.email}
            </Link>
          </div>
        ) : (
          <Link to="/login" className="icon-link">
            <PiUser />
          </Link>
        )}

        <Link to="/cart" className="cart-icon-container">
          <PiShoppingCart />

          {cartCount > 0 && <span className="cart-badge">{cartCount}</span>}
        </Link>
      </div>
    </nav>
  );
}

export default Navbar;
