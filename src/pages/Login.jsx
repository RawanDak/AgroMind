import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import { loginUser } from "../services/authService";

function LoginPage() {
  const navigate = useNavigate();

  const [values, setValues] = useState({
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setValues({
      ...values,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const data = await loginUser(values);

      localStorage.setItem("token", data.access_token);

      setMessage("Login successful!");
      navigate("/");
    } catch (error) {
      setMessage("Login failed.");
    }
  };

  const fields = [
    {
      name: "email",
      type: "email",
      placeholder: "Email",
      required: true,
    },
    {
      name: "password",
      type: "password",
      placeholder: "Password",
      required: true,
    },
  ];

  return (
    <AuthForm
      title="Login"
      fields={fields}
      values={values}
      onChange={handleChange}
      onSubmit={handleSubmit}
      buttonText="Login"
      message={message}
    >
      <p className="auth-switch">
        Don't have an account? <Link to="/register">Register</Link>
      </p>
    </AuthForm>
  );
}

export default LoginPage;
