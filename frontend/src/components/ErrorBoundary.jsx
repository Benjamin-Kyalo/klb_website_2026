import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    if (process.env.NODE_ENV !== "production") {
      console.error("ErrorBoundary caught:", error, info);
    }
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            padding: "2rem",
            fontFamily: "system-ui, sans-serif",
            textAlign: "center",
          }}
        >
          <div style={{ maxWidth: "32rem" }}>
            <h1 style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>
              Something went wrong
            </h1>
            <p style={{ color: "#4f6579", lineHeight: 1.6, marginBottom: "1.5rem" }}>
              An unexpected error occurred. Please reload the page. If the problem
              persists, contact the site administrator.
            </p>
            <button
              type="button"
              onClick={this.handleReload}
              style={{
                background: "#0875b9",
                color: "#fff",
                border: 0,
                borderRadius: "8px",
                padding: "0.7rem 1.4rem",
                fontSize: "0.95rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
