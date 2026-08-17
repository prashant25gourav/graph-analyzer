import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchHealth } from "../services/api";

export function HomePage() {
  const [healthStatus, setHealthStatus] = useState(
    "Checking backend status...",
  );

  useEffect(() => {
    let isMounted = true;

    fetchHealth()
      .then((data) => {
        if (isMounted) {
          setHealthStatus(
            `Backend: ${data.status} (${data.service} v${data.version})`,
          );
        }
      })
      .catch(() => {
        if (isMounted) {
          setHealthStatus(
            "Backend: unavailable (start API or check VITE_API_BASE_URL)",
          );
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section>
      <p className="status-pill">{healthStatus}</p>

      <div className="grid-cards">
        <article className="card">
          <h2>Single Graph Analysis</h2>
          <p>
            Upload one graph and get structured analysis: chart details, values,
            trends, observations, insights, recommendations, and summary.
          </p>
          <Link to="/analyze" className="cta-link">
            Open Analyze Workflow
          </Link>
        </article>

        <article className="card">
          <h2>Graph Comparison</h2>
          <p>
            Upload Graph A and Graph B to compare structure, trends, value
            changes, and business implications with deterministic checks.
          </p>
          <Link to="/compare" className="cta-link">
            Open Compare Workflow
          </Link>
        </article>
      </div>
    </section>
  );
}
