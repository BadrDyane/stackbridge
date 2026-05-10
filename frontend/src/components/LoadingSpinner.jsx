export default function LoadingSpinner({ size = 24 }) {
    return (
      <div
        style={{
          width: size,
          height: size,
          border: `2px solid var(--color-border)`,
          borderTopColor: "var(--color-accent)",
          borderRadius: "50%",
          animation: "spin 0.7s linear infinite",
          margin: "0 auto",
        }}
      />
    );
  }
  
  // Inject keyframes once
  const style = document.createElement("style");
  style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
  document.head.appendChild(style);