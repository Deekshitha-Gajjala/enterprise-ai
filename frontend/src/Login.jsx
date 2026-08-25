import { useState } from "react";
import "./Login.css";

const API =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api";

function Login({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();

    setError("");

    if (!email || !password) {
      setError("Please enter email and password.");
      return;
    }

    if (mode === "register" && !name.trim()) {
      setError("Please enter your name.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API}/auth/${mode}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name,
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Authentication failed."
        );
      }

      localStorage.setItem(
        "enterprise_ai_token",
        data.access_token
      );

      localStorage.setItem(
        "enterprise_ai_user",
        JSON.stringify(data.user)
      );

      onLogin(data.user);

    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">

      <div className="login-card">

        <div className="login-logo">
          AI
        </div>

        <h1>
          Enterprise AI
        </h1>

        <p className="login-subtitle">
          Intelligent Document Assistant
        </p>

        <div className="login-tabs">

          <button
            className={
              mode === "login"
                ? "active"
                : ""
            }
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            Login
          </button>

          <button
            className={
              mode === "register"
                ? "active"
                : ""
            }
            onClick={() => {
              setMode("register");
              setError("");
            }}
          >
            Register
          </button>

        </div>

        <form onSubmit={submit}>

          {mode === "register" && (
            <input
              type="text"
              placeholder="Full name"
              value={name}
              onChange={(e) =>
                setName(e.target.value)
              }
            />
          )}

          <input
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) =>
              setEmail(e.target.value)
            }
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) =>
              setPassword(e.target.value)
            }
          />

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-submit"
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
              ? "Login"
              : "Create account"}
          </button>

        </form>

      </div>

    </div>
  );
}

export default Login;