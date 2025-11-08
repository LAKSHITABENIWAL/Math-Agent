// src/App.js
import React, { useState } from "react";
import "./index.css";

function nowIso() {
  return new Date().toISOString();
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null); // { text, source, question, feedback }
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  // Correction modal state
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState("");
  const [correctionComment, setCorrectionComment] = useState("");

  // simple toast helper
  function showToast(text, kind = "info") {
    setToast({ text, kind, id: Math.random().toString(36).slice(2) });
    setTimeout(() => setToast(null), 3000);
  }

  async function askQuestion(runQuestion = null) {
    const q = (runQuestion ?? question).trim();
    if (!q) return;
    setLoading(true);
    setAnswer(null);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Server error", "error");
      } else {
        // ensure stored shape
        setAnswer({ ...data, question: q, feedback: null });
      }
    } catch (err) {
      showToast(err.message || "Network error", "error");
    } finally {
      setLoading(false);
    }
  }

  // Basic feedback endpoint - still record thumbs up/down
  async function sendFeedbackServer(helpful, extra = {}) {
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: answer?.question || question,
          answer: answer?.text || (answer?.text ?? ""),
          helpful,
          corrected_answer: extra.corrected_answer ?? null,
          comment: extra.comment ?? null,
        }),
      });
    } catch (err) {
      // ignore: not critical, show toast if desired
      console.warn("feedback save failed", err);
    }
  }

  // Called when user presses 👍
  async function handleHelpful() {
    if (!answer) return showToast("No answer to rate", "error");
    // mark locally
    setAnswer((a) => ({ ...a, feedback: true }));
    showToast("Thanks — glad it helped!", "success");
    await sendFeedbackServer(true);
  }

  // Called when user presses 👎
  function handleNotHelpful() {
    if (!answer) return showToast("No answer to rate", "error");
    // open correction modal
    setCorrectionText(""); // clear old
    setCorrectionComment("");
    setShowCorrection(true);
  }

  // when user submits the correction modal
  async function submitCorrection(e) {
    e?.preventDefault?.();
    if (!answer && !question) return showToast("No question to correct", "error");

    const corrected = correctionText.trim();
    const comment = correctionComment.trim();

    // always send the basic feedback record (helpful=false)
    await sendFeedbackServer(false, { corrected_answer: corrected || null, comment: comment || null });

    // If user provided corrected answer, also call /api/feedback/train to inject into KB
    if (corrected) {
      try {
        const res = await fetch("/api/feedback/train", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: answer?.question || question,
            corrected_answer: corrected,
            comment,
          }),
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          showToast("Thanks — correction saved and trained!", "success");
          // update local answer feedback state
          setAnswer((a) => ({ ...a, feedback: false, corrected: corrected }));
        } else {
          showToast(data.error || "Train call failed", "error");
        }
      } catch (err) {
        showToast(err.message || "Network/train error", "error");
      }
    } else {
      // no corrected answer provided — still saved simple feedback
      showToast("Feedback saved. Thanks — we'll improve!", "info");
      setAnswer((a) => ({ ...a, feedback: false }));
    }

    setShowCorrection(false);
  }

  // keyboard submit for modal
  function handleCorrectionKey(e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      submitCorrection();
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      askQuestion();
    }
  }

  function copyToClipboard(text) {
    try {
      navigator.clipboard.writeText(text);
      showToast("Copied to clipboard", "info");
    } catch {
      showToast("Copy failed", "error");
    }
  }

  return (
    <div className="app-root chatgpt-layout">
      <div className="main-center-area">
        <div className="center-wrapper">
          <header className="hero">
            <div className="hero-inner">
              <div className="kicker">MATH SOLVER</div>
              <h1 className="hero-title">Math Agent</h1>
              <p className="hero-sub">Solve complex equations and get detailed explanations instantly</p>
            </div>
          </header>

          <main className="main layout chat-layout">
            <section className="card input-card">
              <textarea
                className="question"
                placeholder="Enter your math problem... (e.g., 2x + 5 = 15)"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKey}
              />
              <div className="card-footer">
                <div className="tip">
                  Press <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
                </div>
                <div className="actions">
                  <button
                    className="btn green"
                    onClick={() => askQuestion()}
                    disabled={loading || !question.trim()}
                  >
                    {loading ? "Solving..." : "Solve"}
                  </button>
                  <button
                    className="btn ghost"
                    onClick={() => {
                      setQuestion("");
                      setAnswer(null);
                      setToast(null);
                    }}
                  >
                    Clear
                  </button>
                </div>
              </div>
            </section>

            {answer && (
              <section className="card answer-card large">
                <div className="answer-top">
                  <div className="answer-meta">
                    Source: <strong>{answer.source}</strong>
                  </div>
                  <div className="answer-actions-inline">
                    <button
                      className="icon-btn"
                      title="Copy answer"
                      onClick={() => copyToClipboard(answer.text)}
                    >
                      📋
                    </button>
                    <button
                      className="icon-btn"
                      title="Re-run question"
                      onClick={() => askQuestion(answer.question || question)}
                    >
                      🔁
                    </button>
                  </div>
                </div>
                <div className="answer-text">
                  <pre>{answer.text}</pre>
                </div>
                <div className="answer-footer">
                  <div className="help-text">Was this helpful?</div>
                  <div className="feedback-chips">
                    <button
                      className={"chip " + (answer.feedback === true ? "chip-on" : "")}
                      onClick={handleHelpful}
                      title="Yes"
                    >
                      👍 Helpful
                    </button>
                    <button
                      className={"chip " + (answer.feedback === false ? "chip-off" : "")}
                      onClick={handleNotHelpful}
                      title="No"
                    >
                      👎 Not helpful
                    </button>
                  </div>
                </div>
              </section>
            )}

            <footer className="site-foot">
              Tip: the backend must be running at <code>localhost:5000</code>
            </footer>
          </main>
        </div>
      </div>

      {/* Correction Modal */}
      {showCorrection && (
        <div className="modal-backdrop" onMouseDown={() => setShowCorrection(false)}>
          <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
            <h3>Send correction</h3>
            <p className="muted">Please paste the correct answer (or a short explanation) below. This will help the agent learn.</p>
            <textarea
              className="correction-input"
              placeholder="Correct answer or explanation (required to train). Leave empty to just send 'not helpful'."
              value={correctionText}
              onChange={(e) => setCorrectionText(e.target.value)}
              onKeyDown={handleCorrectionKey}
            />
            <input
              className="correction-comment"
              placeholder="Optional comment (e.g., typo, wrong method)"
              value={correctionComment}
              onChange={(e) => setCorrectionComment(e.target.value)}
            />
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => { setShowCorrection(false); }}>Cancel</button>
              <button className="btn green" onClick={submitCorrection}>Submit Correction</button>
            </div>
          </div>
        </div>
      )}

      {toast && <div className={"toast " + toast.kind}>{toast.text}</div>}
    </div>
  );
}
