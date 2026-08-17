import { ChangeEvent, FormEvent, useEffect, useState } from "react";

import { uploadForCompare } from "../services/api";

const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_MB = 8;

type Analysis = {
  graph_type?: string;
  title?: string;
  x_axis_label?: string;
  y_axis_label?: string;
  units?: string;
  maximum_trend?: string;
  minimum_trend?: string;
};

type DeltaValue = {
  label?: string;
  graph_a?: number | null;
  graph_b?: number | null;
  absolute_change?: number | null;
  percent_change?: number | null;
  unit?: string;
};

type Comparison = {
  comparability?: {
    structurally_comparable?: boolean;
    numerically_comparable?: boolean;
    reasons?: string[];
  };
  similarities?: string[];
  differences?: string[];
  value_comparison?: DeltaValue[];
  trend_comparison?: string[];
  significant_changes?: string[];
  comparative_insights?: string[];
  recommendations?: string[];
  summary?: string;
  uncertainty_notes?: string[];
};

type CompareResponse = {
  graph_a?: { analysis?: Analysis };
  graph_b?: { analysis?: Analysis };
  comparison?: Comparison;
};

function normalizedList(items?: string[]): string[] {
  if (!items || items.length === 0) {
    return ["Not Available"];
  }
  return items;
}

function formatNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "NA";
  }
  return value.toFixed(2);
}

export function ComparePage() {
  const [graphA, setGraphA] = useState<File | null>(null);
  const [graphB, setGraphB] = useState<File | null>(null);
  const [previewA, setPreviewA] = useState("");
  const [previewB, setPreviewB] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<CompareResponse | null>(null);

  useEffect(() => {
    if (!graphA) {
      setPreviewA("");
      return;
    }

    const objectUrl = URL.createObjectURL(graphA);
    setPreviewA(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [graphA]);

  useEffect(() => {
    if (!graphB) {
      setPreviewB("");
      return;
    }

    const objectUrl = URL.createObjectURL(graphB);
    setPreviewB(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [graphB]);

  const validateFile = (file: File | null): string => {
    if (!file) {
      return "File is required.";
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      return "Unsupported file type. Use PNG, JPEG, or WEBP.";
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      return `File is too large. Maximum size is ${MAX_MB} MB.`;
    }
    return "";
  };

  const onSelectGraphA = (event: ChangeEvent<HTMLInputElement>) => {
    setError("");
    setResult(null);
    const selected = event.target.files?.[0] ?? null;
    const validationError = validateFile(selected);
    if (validationError && selected) {
      setGraphA(null);
      setError(`Graph A: ${validationError}`);
      return;
    }
    setGraphA(selected);
  };

  const onSelectGraphB = (event: ChangeEvent<HTMLInputElement>) => {
    setError("");
    setResult(null);
    const selected = event.target.files?.[0] ?? null;
    const validationError = validateFile(selected);
    if (validationError && selected) {
      setGraphB(null);
      setError(`Graph B: ${validationError}`);
      return;
    }
    setGraphB(selected);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setResult(null);

    const validationA = validateFile(graphA);
    const validationB = validateFile(graphB);
    if (validationA || validationB) {
      setError(
        `Graph A: ${validationA || "OK"} | Graph B: ${validationB || "OK"}`,
      );
      return;
    }

    setIsLoading(true);
    try {
      const response = (await uploadForCompare(
        graphA as File,
        graphB as File,
      )) as CompareResponse;
      setResult(response);
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "Unexpected error";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="panel">
      <h2>Compare Graphs</h2>
      <p>
        Upload Graph A and Graph B for validation, AI extraction, and
        deterministic comparison.
      </p>

      <form onSubmit={onSubmit} className="form-block">
        <label htmlFor="graph-a">Graph A</label>
        <input
          id="graph-a"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={onSelectGraphA}
        />

        {previewA && graphA ? (
          <div className="preview-wrap">
            <img
              src={previewA}
              alt="Graph A preview"
              className="preview-image"
            />
            <p className="file-meta">
              {graphA.name} | {(graphA.size / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : null}

        <label htmlFor="graph-b">Graph B</label>
        <input
          id="graph-b"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={onSelectGraphB}
        />

        {previewB && graphB ? (
          <div className="preview-wrap">
            <img
              src={previewB}
              alt="Graph B preview"
              className="preview-image"
            />
            <p className="file-meta">
              {graphB.name} | {(graphB.size / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : null}

        <button type="submit" disabled={isLoading} className="primary-btn">
          {isLoading ? "Analyzing..." : "Compare Graphs"}
        </button>
      </form>

      {error ? <p className="error-text">{error}</p> : null}

      {result?.comparison ? (
        <div className="result-box">
          <h3>Graph A Overview</h3>
          <p>
            <strong>Type:</strong>{" "}
            {result.graph_a?.analysis?.graph_type ?? "Not Available"}
          </p>
          <p>
            <strong>Title:</strong>{" "}
            {result.graph_a?.analysis?.title ?? "Not Available"}
          </p>
          <p>
            <strong>X-axis:</strong>{" "}
            {result.graph_a?.analysis?.x_axis_label ?? "Not Available"}
          </p>
          <p>
            <strong>Y-axis:</strong>{" "}
            {result.graph_a?.analysis?.y_axis_label ?? "Not Available"}
          </p>
          <p>
            <strong>Units:</strong>{" "}
            {result.graph_a?.analysis?.units ?? "Not Available"}
          </p>

          <h3>Graph B Overview</h3>
          <p>
            <strong>Type:</strong>{" "}
            {result.graph_b?.analysis?.graph_type ?? "Not Available"}
          </p>
          <p>
            <strong>Title:</strong>{" "}
            {result.graph_b?.analysis?.title ?? "Not Available"}
          </p>
          <p>
            <strong>X-axis:</strong>{" "}
            {result.graph_b?.analysis?.x_axis_label ?? "Not Available"}
          </p>
          <p>
            <strong>Y-axis:</strong>{" "}
            {result.graph_b?.analysis?.y_axis_label ?? "Not Available"}
          </p>
          <p>
            <strong>Units:</strong>{" "}
            {result.graph_b?.analysis?.units ?? "Not Available"}
          </p>

          <h3>Similarities</h3>
          <ul>
            {normalizedList(result.comparison.similarities).map(
              (item, index) => (
                <li key={`sim-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Differences</h3>
          <ul>
            {normalizedList(result.comparison.differences).map(
              (item, index) => (
                <li key={`diff-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Comparability</h3>
          <p>
            <strong>Structural:</strong>{" "}
            {result.comparison.comparability?.structurally_comparable
              ? "Comparable"
              : "Limited"}
          </p>
          <p>
            <strong>Numerical:</strong>{" "}
            {result.comparison.comparability?.numerically_comparable
              ? "Comparable"
              : "Limited"}
          </p>
          <ul>
            {normalizedList(result.comparison.comparability?.reasons).map(
              (item, index) => (
                <li key={`reason-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Value Comparison</h3>
          <ul>
            {(result.comparison.value_comparison ?? []).map((item, index) => (
              <li key={`val-${index}`}>
                {item.label ?? "Value"}: A={formatNumber(item.graph_a)}, B=
                {formatNumber(item.graph_b)}, Delta=
                {formatNumber(item.absolute_change)}, Percent=
                {item.percent_change == null
                  ? "NA"
                  : `${formatNumber(item.percent_change)}%`}
                {item.unit ? ` (${item.unit})` : ""}
              </li>
            ))}
          </ul>

          <h3>Trend Comparison</h3>
          <ul>
            {normalizedList(result.comparison.trend_comparison).map(
              (item, index) => (
                <li key={`trend-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Significant Changes</h3>
          <ul>
            {normalizedList(result.comparison.significant_changes).map(
              (item, index) => (
                <li key={`chg-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Comparative Business Insights</h3>
          <ul>
            {normalizedList(result.comparison.comparative_insights).map(
              (item, index) => (
                <li key={`ins-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Recommendations</h3>
          <ul>
            {normalizedList(result.comparison.recommendations).map(
              (item, index) => (
                <li key={`rec-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Summary</h3>
          <p>{result.comparison.summary ?? "Not Available"}</p>

          {(result.comparison.uncertainty_notes ?? []).length > 0 ? (
            <>
              <h3>Uncertainty Notes</h3>
              <ul>
                {normalizedList(result.comparison.uncertainty_notes).map(
                  (item, index) => (
                    <li key={`unc-${index}`}>{item}</li>
                  ),
                )}
              </ul>
            </>
          ) : null}
        </div>
      ) : result ? (
        <p className="warning-text">
          Comparison response was received but comparison sections were missing.
          Please try again.
        </p>
      ) : null}
    </section>
  );
}
