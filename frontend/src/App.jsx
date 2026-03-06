import { useState, useEffect, useRef } from "react";
import { TwistyPlayer } from "cubing/twisty";

const COLOR_KEYS = ["U", "R", "F", "D", "L", "B"];

function makeDefaultCube() {
  const faces = {};
  COLOR_KEYS.forEach((f) => { faces[f] = Array(9).fill(f); });
  return faces;
}

function facesToString(faces) {
  return COLOR_KEYS.map(f => faces[f].join("")).join("");
}

function stringToFaces(str) {
  const faces = {};
  COLOR_KEYS.forEach((f, i) => {
    faces[f] = str.slice(i * 9, i * 9 + 9).split("");
  });
  return faces;
}

const COLORS = {
  U: { hex: "#FFFFFF", label: "White" },
  R: { hex: "#FF4500", label: "Orange" },
  F: { hex: "#00AA44", label: "Green" },
  D: { hex: "#FFD700", label: "Yellow" },
  L: { hex: "#CC2200", label: "Red" },
  B: { hex: "#1A6FCC", label: "Blue" },
};

const FACE_LABELS = {
  U: "Top (White)", R: "Right (Orange)", F: "Front (Green)",
  D: "Bottom (Yellow)", L: "Left (Red)", B: "Back (Blue)",
};

function FaceInput({ faceKey, faceData, onChange, selectedColor }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 11, color: "#aaa", letterSpacing: 2, textTransform: "uppercase" }}>
        {FACE_LABELS[faceKey]}
      </span>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 34px)", gap: 3 }}>
        {faceData.map((color, i) => (
          <div key={i} onClick={() => onChange(faceKey, i, selectedColor)}
            style={{
              width: 34, height: 34, background: COLORS[color].hex,
              border: "2px solid rgba(0,0,0,0.4)", borderRadius: 5, cursor: "pointer",
              boxShadow: "inset 0 1px 3px rgba(255,255,255,0.15)",
              transition: "transform 0.1s",
            }}
            onMouseEnter={e => e.currentTarget.style.transform = "scale(1.15)"}
            onMouseLeave={e => e.currentTarget.style.transform = "scale(1)"}
          />
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div style={{ flex: 1, padding: "12px 14px", background: "#0d0d12", border: `1px solid ${accent}33`, borderRadius: 8, display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 9, color: "#555", letterSpacing: 3 }}>{label}</div>
      <div style={{ fontSize: 20, fontFamily: "sans-serif", fontWeight: "bold", color: accent }}>{value}</div>
    </div>
  );
}

export default function App() {
  const playerRef = useRef(null);
  const containerRef = useRef(null);

  const [faces, setFaces] = useState(makeDefaultCube());
  const [selectedColor, setSelectedColor] = useState("U");
  const [solution, setSolution] = useState(null);
  const [scrambleAlg, setScrambleAlg] = useState("");
  const [loading, setLoading] = useState(false);
  const [scrambling, setScrambling] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("input");
  const [solverBackend, setSolverBackend] = useState(null);
  const [solveStats, setSolveStats] = useState(null);
  const [scrambleMoves, setScrambleMoves] = useState(null);
  const [speed, setSpeed] = useState(1);

  // Initialize TwistyPlayer
  useEffect(() => {
    if (!containerRef.current) return;
    const player = new TwistyPlayer({
      puzzle: "3x3x3",
      alg: "",
      hintFacelets: "none",
      backView: "none",
      background: "none",
      controlPanel: "none",
    });
    player.style.width = "100%";
    player.style.height = "100%";
    containerRef.current.appendChild(player);
    playerRef.current = player;

    fetch("http://localhost:5000/health")
      .then(r => r.json())
      .then(d => setSolverBackend(d.solver))
      .catch(() => setSolverBackend(null));

    return () => {
      if (containerRef.current && player) {
        containerRef.current.removeChild(player);
      }
    };
  }, []);

  const setPlayerAlg = (setupAlg, solutionAlg) => {
    if (!playerRef.current) return;
    playerRef.current.experimentalSetupAlg = setupAlg || "";
    playerRef.current.alg = solutionAlg || "";
    playerRef.current.timestamp = "start";
  };

  const handleCellChange = (faceKey, idx, color) => {
    setFaces(prev => ({ ...prev, [faceKey]: prev[faceKey].map((c, i) => i === idx ? color : c) }));
  };

  const handleReset = () => {
    setFaces(makeDefaultCube());
    setSolution(null); setScrambleAlg(""); setSolveStats(null);
    setScrambleMoves(null); setError(null);
    setPlayerAlg("", "");
  };

  const handleScramble = async () => {
    setScrambling(true); setError(null); setSolution(null); setSolveStats(null);
    try {
      const res  = await fetch("http://localhost:5000/scramble?length=20");
      const data = await res.json();
      setScrambleMoves(data.scramble_moves);
      setFaces(stringToFaces(data.cube_string));
      const algStr = data.scramble_moves.join(" ");
      setScrambleAlg(algStr);
      // Show scrambled state in player
      setPlayerAlg(algStr, "");
      setScrambling(false);
    } catch (e) {
      setError("Could not connect to backend.");
      setScrambling(false);
    }
  };

  const handleSolve = async () => {
    setLoading(true); setError(null); setSolution(null); setSolveStats(null);
    try {
      const res  = await fetch("http://localhost:5000/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cube_string: facesToString(faces) }),
      });
      const data = await res.json();
      if (data.error) { setError(data.error); setLoading(false); return; }
      setSolution(data.solution);
      setSolveStats({ moves: data.move_count, solver: data.solver, timeMs: data.solve_time_ms });
      // Set player: setup = scramble, alg = solution — now you can play it back!
      setPlayerAlg(scrambleAlg, data.solution.join(" "));
      playerRef.current.timestamp = "start";
      setActiveTab("solve");
      setLoading(false);
    } catch (e) {
      setError("Could not connect to backend.");
      setLoading(false);
    }
  };

  const handlePlay = () => {
    if (!playerRef.current) return;
    playerRef.current.play();
  };

  const handlePause = () => {
    if (!playerRef.current) return;
    playerRef.current.pause();
  };

  const handleStepForward = async () => {
    if (!playerRef.current) return;
    playerRef.current.stepForward();
  };

  const handleStepBack = async () => {
    if (!playerRef.current) return;
    playerRef.current.stepBackward();
  };

  const handleJumpToStart = () => {
    if (!playerRef.current) return;
    playerRef.current.timestamp = "start";
  };

  const handleJumpToEnd = () => {
    if (!playerRef.current) return;
    playerRef.current.timestamp = "end";
  };

  const btnStyle = (active, accent = "#ff4500") => ({
    padding: "10px 14px",
    background: active ? `linear-gradient(135deg, ${accent}, ${accent}bb)` : "transparent",
    border: `1px solid ${active ? accent : "#2a2a2a"}`,
    borderRadius: 7, color: active ? "#fff" : "#666",
    cursor: "pointer", fontSize: 14, letterSpacing: 2, transition: "all 0.15s",
    boxShadow: active ? `0 0 16px ${accent}44` : "none",
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", display: "flex", flexDirection: "column", fontFamily: "'Courier Prime', monospace", color: "#e8e0d0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0a0a0f; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #0d0d0d; }
        ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 3px; }
        input[type=range] { accent-color: #ff4500; }
      `}</style>

      {/* Header */}
      <header style={{ padding: "18px 32px", borderBottom: "1px solid #1a1a1a", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ fontSize: 28, fontWeight: "bold", letterSpacing: 6, background: "linear-gradient(135deg, #ff4500, #ffd700, #00aa44, #1a6fcc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          CUBE SOLVER
        </div>
        <div style={{ height: 1, flex: 1, background: "linear-gradient(90deg, #2a2a2a, transparent)" }} />
        <div style={{
          padding: "4px 12px", borderRadius: 20,
          background: solverBackend === "CUDA" ? "rgba(0,200,100,0.1)" : "rgba(255,140,0,0.1)",
          border: `1px solid ${solverBackend === "CUDA" ? "#00c864" : "#ff8c00"}44`,
          fontSize: 10, letterSpacing: 2,
          color: solverBackend === "CUDA" ? "#00c864" : solverBackend ? "#ff8c00" : "#444",
        }}>
          {solverBackend ? `⚡ ${solverBackend.toUpperCase()}` : "● OFFLINE"}
        </div>
      </header>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* LEFT PANEL */}
        <div style={{ width: 400, minWidth: 400, borderRight: "1px solid #1a1a1a", display: "flex", flexDirection: "column", overflowY: "auto" }}>

          {/* Tabs */}
          <div style={{ display: "flex", borderBottom: "1px solid #1a1a1a" }}>
            {["input", "solve"].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{
                flex: 1, padding: "13px", background: activeTab === tab ? "#10101a" : "transparent",
                border: "none", borderBottom: activeTab === tab ? "2px solid #ff4500" : "2px solid transparent",
                color: activeTab === tab ? "#e8e0d0" : "#444", cursor: "pointer",
                fontSize: 11, letterSpacing: 3, textTransform: "uppercase", transition: "all 0.2s",
              }}>
                {tab === "input" ? "01 · INPUT" : "02 · SOLVE"}
              </button>
            ))}
          </div>

          {/* INPUT TAB */}
          {activeTab === "input" && (
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 20 }}>

              <div>
                <div style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginBottom: 10 }}>SELECT COLOR</div>
                <div style={{ display: "flex", gap: 8 }}>
                  {COLOR_KEYS.map(k => (
                    <button key={k} onClick={() => setSelectedColor(k)} style={{
                      width: 40, height: 40, background: COLORS[k].hex,
                      border: selectedColor === k ? "3px solid #fff" : "3px solid transparent",
                      borderRadius: 8, cursor: "pointer",
                      boxShadow: selectedColor === k ? `0 0 14px ${COLORS[k].hex}99` : "none",
                      transform: selectedColor === k ? "scale(1.12)" : "scale(1)",
                      transition: "all 0.15s",
                    }} title={COLORS[k].label} />
                  ))}
                </div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#555" }}>
                  Painting: <span style={{ color: COLORS[selectedColor].hex }}>{COLORS[selectedColor].label}</span>
                </div>
              </div>

              <div style={{ height: 1, background: "#181818" }} />

              {scrambleMoves && (
                <div style={{ padding: 12, background: "#0d0d14", border: "1px solid #1e1e2e", borderRadius: 8 }}>
                  <div style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginBottom: 8 }}>SCRAMBLE</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {scrambleMoves.map((m, i) => (
                      <span key={i} style={{ fontSize: 11, color: "#888", padding: "2px 6px", background: "#161616", borderRadius: 4 }}>{m}</span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
                {COLOR_KEYS.map(f => (
                  <FaceInput key={f} faceKey={f} faceData={faces[f]} onChange={handleCellChange} selectedColor={selectedColor} />
                ))}
              </div>

              <div style={{ height: 1, background: "#181818" }} />

              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={handleScramble} disabled={scrambling} style={{
                  flex: 1, padding: "12px 8px",
                  background: scrambling ? "#1a1a1a" : "linear-gradient(135deg, #1a6fcc, #0d4f99)",
                  border: "none", borderRadius: 8, color: scrambling ? "#444" : "#fff",
                  cursor: scrambling ? "not-allowed" : "pointer", fontSize: 15, letterSpacing: 2,
                  boxShadow: scrambling ? "none" : "0 4px 16px rgba(26,111,204,0.3)",
                }}>
                  {scrambling ? "SCRAMBLING..." : "🎲 SCRAMBLE"}
                </button>
                <button onClick={handleSolve} disabled={loading || scrambling} style={{
                  flex: 1, padding: "12px 8px",
                  background: loading ? "#1a1a1a" : "linear-gradient(135deg, #ff4500, #cc3300)",
                  border: "none", borderRadius: 8, color: loading ? "#444" : "#fff",
                  cursor: loading ? "not-allowed" : "pointer", fontSize: 15, letterSpacing: 2,
                  boxShadow: loading ? "none" : "0 4px 16px rgba(255,69,0,0.3)",
                }}>
                  {loading ? "SOLVING..." : "SOLVE"}
                </button>
                <button onClick={handleReset} style={{
                  padding: "12px 14px", background: "transparent",
                  border: "1px solid #2a2a2a", borderRadius: 8, color: "#555", cursor: "pointer", fontSize: 14,
                }}>↺</button>
              </div>

              {error && (
                <div style={{ padding: 12, background: "rgba(255,50,50,0.07)", border: "1px solid rgba(255,50,50,0.25)", borderRadius: 8, color: "#ff6666", fontSize: 11, lineHeight: 1.7 }}>
                  ⚠ {error}
                </div>
              )}
            </div>
          )}

          {/* SOLVE TAB */}
          {activeTab === "solve" && (
            <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
              {!solution ? (
                <div style={{ color: "#333", fontSize: 13, lineHeight: 2, paddingTop: 12 }}>
                  Enter cube state in INPUT tab and click SOLVE.
                </div>
              ) : (
                <>
                  {solveStats && (
                    <div style={{ display: "flex", gap: 8 }}>
                      <StatCard label="MOVES"      value={solveStats.moves}                        accent="#ffd700" />
                      <StatCard label="SOLVE TIME" value={`${solveStats.timeMs}ms`}                accent="#00aa44" />
                      <StatCard label="ENGINE"     value={solveStats.solver?.split(" ")[0] || "?"} accent="#ff8c00" />
                    </div>
                  )}

                  <div>
                    <div style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginBottom: 8 }}>ANIMATION SPEED · {speed}x</div>
                    <input type="range" min="0.5" max="4" step="0.5" value={speed}
                      onChange={e => {
                        const v = Number(e.target.value);
                        setSpeed(v);
                        if (playerRef.current) playerRef.current.tempoScale = v;
                      }} style={{ width: "100%" }} />
                  </div>

                  <div>
                    <div style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginBottom: 10 }}>PLAYBACK</div>
                    <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
                      <button onClick={handleJumpToStart} style={btnStyle(false)} title="Jump to start">⏮</button>
                      <button onClick={handleStepBack}    style={btnStyle(false, "#888")}>◀</button>
                      <button onClick={handlePlay}        style={{ ...btnStyle(true, "#ff4500"), flex: 1 }}>▶ PLAY</button>
                      <button onClick={handleStepForward} style={btnStyle(false, "#888")}>▶</button>
                      <button onClick={handlePause}       style={btnStyle(false, "#cc2200")}>⏸</button>
                      <button onClick={handleJumpToEnd}   style={btnStyle(false)} title="Jump to end">⏭</button>
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: 9, color: "#444", letterSpacing: 3, marginBottom: 8 }}>MOVE SEQUENCE</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, maxHeight: 200, overflowY: "auto" }}>
                      {solution.map((move, i) => (
                        <div key={i} style={{
                          padding: "4px 9px", borderRadius: 5,
                          background: "#0d0d0d", border: "1px solid #1a1a1a",
                          color: "#888", fontSize: 13, letterSpacing: 2,
                        }}>
                          {move}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={{ padding: 12, background: "#0a0a0f", border: "1px solid #161616", borderRadius: 7, fontSize: 10, color: "#3a3a3a", lineHeight: 1.9 }}>
                    <span style={{ color: "#2a2a2a", letterSpacing: 2 }}>NOTATION · </span>
                    U/D/R/L/F/B = face &nbsp;·&nbsp; ' = CCW &nbsp;·&nbsp; 2 = half turn
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* 3D CUBE — powered by cubing.js TwistyPlayer */}
        <div ref={containerRef} style={{ flex: 1, background: "#07070c", display: "flex", alignItems: "center", justifyContent: "center" }} />
      </div>
    </div>
  );
}