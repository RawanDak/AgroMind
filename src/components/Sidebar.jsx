import "./Sidebar.css";
import { Link } from "react-router-dom";

function Sidebar() {
  return (
    <div className="sidebar">
      <h2>AgroMind</h2>

      <nav>
        <Link to="/">Shop</Link>
        <Link to="/diagnosis">Disease Detection</Link>
        <Link to="/products">Products</Link>
        <Link to="/login">Login</Link>
        <Link to="/signup">Sign Up</Link>
      </nav>
    </div>
  );
}

export default Sidebar;