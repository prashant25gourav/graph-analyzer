import { ChangeEvent, FormEvent, useEffect, useState } from "react";

import { uploadForAnalyze } from "../services/api";

const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_MB = 8;

type ValuePoint = {
  label?: string;
  value?: number | null;
  unit?: string;
  confidence?: string;
};

type Analysis = {
  graph_type?: string;
  title?: string;
  x_axis_label?: string;
  y_axis_label?: string;
  units?: string;
  categories_or_legends?: string[];
  highest_value?: ValuePoint;
  lowest_value?: ValuePoint;
  maximum_trend?: string;
  minimum_trend?: string;
  observations?: string[];
  business_insights?: string[];
  recommendations?: string[];
  summary?: string;
  uncertainty_notes?: string[];
};

type AnalyzeResponse = {
  analysis?: Analysis;
};

function normalizedList(items?: string[]): string[] {
  if (!items || items.length === 0) {
    return ["Not Available"];
  }
  return items;
}

function formatValuePoint(point?: ValuePoint): string {
  if (!point) {
    return "Not Available";
  }

  const numeric =
    typeof point.value === "number" && Number.isFinite(point.value)
      ? `${point.value}`
      : "Not Available";

  return `${point.label ?? "Not Available"} | ${numeric} ${point.unit ?? ""}`.trim();
}

function formatConfidence(point?: ValuePoint): string {
  if (!point?.confidence || point.confidence.trim() === "") {
    return "low";
  }
  return point.confidence;
}

export function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [file]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setError("");
    setResult(null);

    const selected = event.target.files?.[0] ?? null;
    if (!selected) {
      setFile(null);
      return;
    }

    if (!ALLOWED_TYPES.includes(selected.type)) {
      setError("Unsupported file type. Use PNG, JPEG, or WEBP.");
      setFile(null);
      return;
    }

    if (selected.size > MAX_MB * 1024 * 1024) {
      setError(`File is too large. Maximum size is ${MAX_MB} MB.`);
      setFile(null);
      return;
    }

    setFile(selected);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!file) {
      setError("Select an image before submitting.");
      return;
    }

    setIsLoading(true);
    try {
      const response = (await uploadForAnalyze(file)) as AnalyzeResponse;
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
      <h2>Analyze Graph</h2>
      <p>
        Upload one graph image for validation and AI-powered structured
        extraction.
      </p>

      <form onSubmit={onSubmit} className="form-block">
        <label htmlFor="analyze-file">Graph image</label>
        <input
          id="analyze-file"
          name="file"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={onFileChange}
        />

        {previewUrl && file ? (
          <div className="preview-wrap">
            <img
              src={previewUrl}
              alt="Selected graph preview"
              className="preview-image"
            />
            <p className="file-meta">
              {file.name} | {(file.size / 1024).toFixed(1)} KB | {file.type}
            </p>
          </div>
        ) : null}

        <button type="submit" disabled={isLoading} className="primary-btn">
          {isLoading ? "Analyzing..." : "Analyze Graph"}
        </button>
      </form>

      {error ? <p className="error-text">{error}</p> : null}

      {result?.analysis ? (
        <div className="result-box">
          <h3>Graph Information</h3>
          <p>
            <strong>Type:</strong>{" "}
            {result.analysis.graph_type ?? "Not Available"}
          </p>
          <p>
            <strong>Title:</strong> {result.analysis.title ?? "Not Available"}
          </p>
          <p>
            <strong>X-axis:</strong>{" "}
            {result.analysis.x_axis_label ?? "Not Available"}
          </p>
          <p>
            <strong>Y-axis:</strong>{" "}
            {result.analysis.y_axis_label ?? "Not Available"}
          </p>
          <p>
            <strong>Units:</strong> {result.analysis.units ?? "Not Available"}
          </p>
          <p>
            <strong>Categories/Legends:</strong>{" "}
            {(result.analysis.categories_or_legends ?? []).length > 0
              ? (result.analysis.categories_or_legends ?? []).join(", ")
              : "Not Available"}
          </p>

          <h3>Values</h3>
          <p>
            <strong>Highest Value:</strong>{" "}
            {formatValuePoint(result.analysis.highest_value)}
          </p>
          <p>
            <strong>Highest Confidence:</strong>{" "}
            {formatConfidence(result.analysis.highest_value)}
          </p>
          <p>
            <strong>Lowest Value:</strong>{" "}
            {formatValuePoint(result.analysis.lowest_value)}
          </p>
          <p>
            <strong>Lowest Confidence:</strong>{" "}
            {formatConfidence(result.analysis.lowest_value)}
          </p>

          <h3>Trends</h3>
          <p>
            <strong>Maximum Trend:</strong>{" "}
            {result.analysis.maximum_trend ?? "Not Available"}
          </p>
          <p>
            <strong>Minimum Trend:</strong>{" "}
            {result.analysis.minimum_trend ?? "Not Available"}
          </p>

          <h3>Key Observations</h3>
          <ul>
            {normalizedList(result.analysis.observations).map((item, index) => (
              <li key={`obs-${index}`}>{item}</li>
            ))}
          </ul>

          <h3>Business Insights</h3>
          <ul>
            {normalizedList(result.analysis.business_insights).map(
              (item, index) => (
                <li key={`ins-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Recommendations</h3>
          <ul>
            {normalizedList(result.analysis.recommendations).map(
              (item, index) => (
                <li key={`rec-${index}`}>{item}</li>
              ),
            )}
          </ul>

          <h3>Summary</h3>
          <p>{result.analysis.summary ?? "Not Available"}</p>

          {(result.analysis.uncertainty_notes ?? []).length > 0 ? (
            <>
              <h3>Uncertainty Notes</h3>
              <ul>
                {normalizedList(result.analysis.uncertainty_notes).map(
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
          Analysis response was received but did not include a usable analysis
          object. Please try again.
        </p>
      ) : null}
    </section>
  );
}
