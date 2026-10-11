import { useEffect, useMemo, useRef, useState } from "react";

const STATUS_LABEL = {
  present: "Reported",
  absent: "Reported as not seen",
  uncertain: "Uncertain wording",
};
const CHECK_LABEL = {
  verified: "Checked against evidence",
  partial: "Partly supported",
  flagged: "Flagged: needs review",
  no_evidence: "No evidence found",
};
const CLAIM_LABEL = { supported: "Supported", partial: "Partly supported", unsupported: "Not supported" };
const URGENCY_TEXT = {
  prompt: "Doctors usually treat this as time-sensitive. Contact the doctor who ordered this X-ray.",
  discuss: "Worth discussing with your doctor.",
};

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

const MAX_FILE_BYTES = 5 * 1024 * 1024;

function groupFindings(findings) {
  const map = new Map();
  for (const f of findings) {
    const key = `${f.title}|${f.status}`;
    if (!map.has(key)) map.set(key, { key, first: f, sentenceIndexes: [] });
    map.get(key).sentenceIndexes.push(f.sentence_index);
  }
  return [...map.values()];
}

function ReportPane({ text, result, activeGroup }) {
  const byIndex = useMemo(() => {
    const m = new Map();
    for (const f of result.findings) if (!m.has(f.sentence_index)) m.set(f.sentence_index, f);
    return m;
  }, [result]);
  const parts = [];
  let cursor = 0;
  for (const s of result.sentences) {
    if (s.start > cursor) parts.push(text.slice(cursor, s.start));
    const f = byIndex.get(s.index);
    const active = activeGroup && activeGroup.sentenceIndexes.includes(s.index);
    const cls = ["sentence", f ? `s-${f.status}` : "s-none", active ? "is-active" : ""].join(" ");
    parts.push(
      <mark key={s.index} className={cls} title={f ? STATUS_LABEL[f.status] : "Not interpreted by MedTruth"}>
        {text.slice(s.start, s.end)}
      </mark>
    );
    cursor = s.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return <p className="report-text">{parts}</p>;
}

function FindingRow({ group, active, onSelect }) {
  const f = group.first;
  const v = f.verification;
  return (
    <li className={`finding st-${f.status} ${active ? "is-active" : ""}`}>
      <button className="finding-head" onClick={onSelect} aria-pressed={active}>
        <span className="finding-title">{f.title}</span>
        <span className={`chip chip-${f.status}`}>{STATUS_LABEL[f.status]}</span>
        <span className={`chip chip-check-${v.status}`}>{CHECK_LABEL[v.status]}</span>
      </button>
      <p className="explanation">{f.explanation.text}</p>
      {f.status !== "absent" && URGENCY_TEXT[f.urgency] && (
        <p className={`urgency urgency-${f.urgency}`}>{URGENCY_TEXT[f.urgency]}</p>
      )}
      <details className="trail">
        <summary>
          Evidence trail
          {group.sentenceIndexes.length > 1 ? ` (mentioned in ${group.sentenceIndexes.length} sentences)` : ""}
        </summary>
        <p className="trail-label">From your report</p>
        <blockquote>{f.sentence}</blockquote>
        <p className="trail-label">Evidence retrieved</p>
        <ul className="evidence">
          {f.evidence.map((e) => (
            <li key={e.entry_id}>
              <strong>{e.title}</strong> <span className="score">match {e.score}</span>
              <br />
              {e.summary}
            </li>
          ))}
        </ul>
        <p className="source-note">{f.evidence[0] ? f.evidence[0].source : ""}</p>
        <p className="trail-label">Each claim, checked</p>
        <ul className="claims">
          {v.claims.map((c, i) => (
            <li key={i} className={`claim claim-${c.label}`}>
              <span className="claim-label">{CLAIM_LABEL[c.label]}</span> {c.text}
              {c.from.length > 0 && <span className="claim-from"> (found in: {c.from.join(", ")})</span>}
              {c.reasons.length > 0 && c.label !== "supported" && (
                <span className="claim-reason"> {c.reasons.join("; ")}.</span>
              )}
            </li>
          ))}
        </ul>
        <p className="meta">
          Confidence: {v.confidence}. Explanation written by: {f.explanation.method}.
        </p>
      </details>
    </li>
  );
}

export default function App() {
  const [text, setText] = useState("");
  const [samples, setSamples] = useState([]);
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [analyzed, setAnalyzed] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeKey, setActiveKey] = useState(null);
  const [fileName, setFileName] = useState("");
  const [reading, setReading] = useState(false);
  const fileInput = useRef(null);

  async function onFileChosen(e) {
    const file = e.target.files && e.target.files[0];
    e.target.value = ""; // allow choosing the same file again
    if (!file) return;
    setError("");
    if (file.size > MAX_FILE_BYTES) {
      setError("That file is larger than 5 MB. Please choose a smaller report file.");
      return;
    }
    setReading(true);
    try {
      let content;
      if (/\.(txt|text|md)$/i.test(file.name)) {
        content = await file.text();
      } else {
        // PDFs (including scans), Word files and images are read by the backend (with OCR where needed)
        const res = await fetch("/api/extract?filename=" + encodeURIComponent(file.name), {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream" },
          body: file,
        });
        if (!res.ok) {
          let detail = "";
          try { detail = (await res.json()).detail; } catch { /* ignore */ }
          throw new Error(detail || `Could not read that file (${res.status}).`);
        }
        content = (await res.json()).text;
      }
      setText(content.slice(0, 20000));
      setFileName(file.name);
    } catch (err) {
      setError(err.message === "Failed to fetch" ? "Could not reach the MedTruth backend to read the file." : err.message);
    } finally {
      setReading(false);
    }
  }

  useEffect(() => {
    api("/api/samples").then(setSamples).catch(() => {});
    api("/api/health").then(setHealth).catch(() => setHealth({ status: "down" }));
  }, []);

  const groups = useMemo(() => (result ? groupFindings(result.findings) : []), [result]);
  const activeGroup = groups.find((g) => g.key === activeKey) || null;

  async function analyze() {
    setLoading(true);
    setError("");
    setActiveKey(null);
    const submitted = text.trim();
    try {
      const data = await api("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_text: submitted, use_llm: true }),
      });
      setResult(data);
      setAnalyzed(submitted);
    } catch (e) {
      setResult(null);
      setError(
        e.message.startsWith("Request failed") || e.message === "Failed to fetch"
          ? "Could not reach the MedTruth backend. Start it with: uvicorn app.main:app --port 8000"
          : e.message
      );
    } finally {
      setLoading(false);
    }
  }

  const s = result && result.summary;

  return (
    <div className="page">
      <header className="top">
        <h1>MedTruth AI</h1>
        <p className="tagline">
          Paste a chest X-ray report. Get a plain-language explanation where every statement can be traced to your
          report or to the evidence behind it.
        </p>
        <p className="disclaimer" role="note">
          This explains the wording of a report. It is not a diagnosis and does not replace your doctor.
        </p>
      </header>

      <main className="layout">
        <section className="pane pane-report" aria-label="Report">
          <h2>Your report</h2>
          {!result ? (
            <>
              <div className="samples">
                <span>Try a sample:</span>
                {samples.map((sm) => (
                  <button key={sm.id} className="link" onClick={() => setText(sm.text)}>
                    {sm.title}
                  </button>
                ))}
              </div>
              <label htmlFor="report" className="sr-only">
                Report text
              </label>
              <textarea
                id="report"
                value={text}
                onChange={(e) => { setText(e.target.value); setFileName(""); }}
                placeholder="Paste the text of an X-ray report here"
                rows={14}
              />
              <div className="actions">
                <input
                  ref={fileInput}
                  type="file"
                  accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
                  onChange={onFileChosen}
                  hidden
                />
                <button type="button" className="secondary" disabled={reading} onClick={() => fileInput.current.click()}>
                  {reading ? "Reading file…" : "Choose file"}
                </button>
                {fileName && <span className="hint">Loaded: {fileName}</span>}
                <button className="primary" onClick={analyze} disabled={loading || text.trim().length < 10}>
                  {loading ? "Analyzing" : "Explain this report"}
                </button>
                {health && health.status === "down" && (
                  <span className="hint">Backend not reachable yet.</span>
                )}
              </div>
            </>
          ) : (
            <>
              <ReportPane text={analyzed} result={result} activeGroup={activeGroup} />
              <ul className="legend">
                <li><span className="swatch s-present" /> Reported finding</li>
                <li><span className="swatch s-absent" /> Reported as not seen</li>
                <li><span className="swatch s-uncertain" /> Uncertain wording</li>
                <li><span className="swatch s-none" /> Not interpreted</li>
              </ul>
              <button className="link" onClick={() => { setResult(null); setActiveKey(null); }}>
                Edit report
              </button>
            </>
          )}
          {error && <p className="error" role="alert">{error}</p>}
        </section>

        <section className="pane pane-results" aria-label="Explanation">
          <h2>What it means</h2>
          {!result && <p className="empty">Results appear here. Select a sentence in the report to see what each part means.</p>}
          {result && (
            <>
              <p className="summary">
                {s.findings === 0
                  ? "No findings from the knowledge base were recognised in this text."
                  : `${s.findings} finding${s.findings === 1 ? "" : "s"} found, ${s.verified} checked against evidence, ${s.flagged} flagged.`}
                {s.faithfulness !== null && ` Support score ${Math.round(s.faithfulness * 100)}%.`}
              </p>
              <p className="meta">
                Explanations written {result.llm.enabled ? `with an LLM (${result.llm.model}) and then verified` : "from a built-in template (no LLM configured)"}.
                Sentences shown without colour were not interpreted.
              </p>
              <ul className="findings">
                {groups.map((g) => (
                  <FindingRow
                    key={g.key}
                    group={g}
                    active={g.key === activeKey}
                    onSelect={() => setActiveKey(g.key === activeKey ? null : g.key)}
                  />
                ))}
              </ul>
              <details className="agents">
                <summary>What each agent did</summary>
                <ol>
                  {result.trace.map((t) => (
                    <li key={t.agent}>
                      <strong>{t.agent}.</strong> {t.output}
                    </li>
                  ))}
                </ol>
                <p className="source-note">Knowledge base: {result.knowledge_base}</p>
              </details>
              <p className="disclaimer">{result.disclaimer}</p>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
