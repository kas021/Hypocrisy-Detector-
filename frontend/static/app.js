
async function postJSON(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  return res.json();
}

const el = (s) => document.querySelector(s);
const results = el("#results");
const statusBox = el("#status");

el("#checkBtn").addEventListener("click", async () => {
  results.innerHTML = "";
  statusBox.textContent = "Checking...";
  const claim = el("#claimInput").value.trim();
  const before = parseInt(el("#before").value, 10);
  const after = parseInt(el("#after").value, 10);
  const topk = parseInt(el("#topk").value, 10);
  const thres = parseFloat(el("#thres").value);
  const margin = parseFloat(el("#margin").value);

  try {
    const data = await postJSON("/api/claim", {
      claim, window_before_ms: before, window_after_ms: after, top_k: topk,
      contra_threshold: thres, margin
    });
    statusBox.textContent = "";
    if (!data.hits || data.hits.length === 0) {
      results.innerHTML = `<p class="muted">No contradictions found.</p>`;
      return;
    }
    data.hits.forEach((h) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="meta">
          <div><strong>Source:</strong> ${h.source.title || "Untitled"} (${h.source.date || "n.d."})</div>
          <div><a href="${h.source.url || "#"}" target="_blank" rel="noopener">Open source</a></div>
        </div>
        <div class="text">
          <div class="label">Claim</div>
          <p>${h.claim_text}</p>
          <div class="label">Prior statement</div>
          <p>${h.segment_text}</p>
          <div class="scores">
            <span>contra: ${h.score.contra.toFixed(2)}</span>
            <span>entail: ${h.score.entail.toFixed(2)}</span>
            <span>neutral: ${h.score.neutral.toFixed(2)}</span>
          </div>
        </div>
        <video controls preload="metadata" src="/clips/${h.clip_path}" class="clip"></video>
      `;
      results.appendChild(card);
    });
  } catch (e) {
    console.error(e);
    statusBox.textContent = "Error: " + e.message.slice(0, 300);
  }
});
