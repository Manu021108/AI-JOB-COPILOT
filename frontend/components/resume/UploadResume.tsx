"use client";
import { useRef, useState } from "react";
import { uploadResume } from "@/lib/api";
import type { ResumeUploadResponse } from "@/types/resume";

const PHASE_LABELS: Record<string, string> = {
  uploading: "Uploading your resume…",
  extracting: "Extracting text from your document…",
  analyzing: "Building your candidate profile…",
};

export default function UploadResume({ onUploaded }: { onUploaded: (r: ResumeUploadResponse) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleFile = async (file: File) => {
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      const resume = await uploadResume(file, setPhase);
      setPhase("analyzing");
      await new Promise((r) => setTimeout(r, 900));
      onUploaded(resume);
      setPhase(null);
    } catch (e) {
      const message = mapError((e as Error).message);
      setPhase(null);
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card upload-card">
      <h3>Upload your resume</h3>
      <p className="muted">We accept .pdf and .docx files (up to 10 MB). Your resume is parsed and your candidate profile is built automatically.</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        disabled={busy}
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = "";
        }}
      />
      {phase ? (
        <div className="upload-status">
          <span className="spinner" aria-hidden />
          {PHASE_LABELS[phase]}
        </div>
      ) : (
        <button className="btn" disabled={busy} onClick={() => inputRef.current?.click()}>
          Choose file
        </button>
      )}
      {error && <div className="error">{error}</div>}
    </div>
  );
}

function mapError(message: string): string {
  const text = message.toLowerCase();
  if (text.includes("file type")) return "Only .pdf and .docx files are supported.";
  if (text.includes("too large") || text.includes("size")) return "Your resume is larger than 10 MB.";
  if (text.includes("scanned") || text.includes("empty")) return "We couldn't read any text. Please upload a text-based (non-scanned) resume.";
  if (text.includes("corrupt") || text.includes("document")) return "That file could not be read as a valid document.";
  if (text.includes("analy")) return "We couldn't analyze this resume. Please try another file.";
  return text;
}