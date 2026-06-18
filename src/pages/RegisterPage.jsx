import { useState } from "react";
import AuthForm from "../components/AuthForm";
import { registerUser } from "../services/authService";
import { useNavigate } from "react-router-dom";

function RegisterPage() {
  const [values, setValues] = useState({
    fullName: "",
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setValues({
      ...values,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await registerUser(values);
      setMessage("Registration successful!");
      navigate("/login");
    } catch (error) {
      setMessage("Registration failed.");
    }
  };

  const fields = [
    {
      name: "fullName",
      type: "text",
      placeholder: "Full Name",
      required: true,
    },
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
      title="Create Account"
      fields={fields}
      values={values}
      onChange={handleChange}
      onSubmit={handleSubmit}
      buttonText="Register"
      message={message}
    >
      <p className="auth-switch">
        Already have an account? <a href="/login">Login</a>
      </p>
    </AuthForm>
  );
}

export default RegisterPage;
