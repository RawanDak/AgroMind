const API_URL = import.meta.env.VITE_API_URL;

export async function registerUser({ email, password, fullName }) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
    }),
  });

  if (!response.ok) {
    throw new Error("Registration failed");
  }

  return response.json();
}

export async function loginUser({ email, password }) {
  const formData = new FormData();
  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Login failed");
  }

  return response.json();
}