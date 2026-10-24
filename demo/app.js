(async () => {
  const status = document.getElementById('status');
  const list = document.getElementById('records');
  const selector = document.getElementById('run');
  let requestId = 0;
  async function render() {
    const currentRequest = ++requestId;
    list.replaceChildren();
    status.textContent = 'Loading recorded results…';
    try {
    const file = selector.value === 'manual' ? 'manual-replay.json' : 'replay.json';
    const response = await fetch(file);
    if (!response.ok) throw new Error('Replay unavailable');
    const replay = await response.json();
    if (currentRequest !== requestId) return;
    document.getElementById('method').textContent = selector.value === 'manual'
      ? 'Three actual in-session assistant extractions, manually transferred and validated. Full project context was visible. No API; no isolated frozen-prompt experiment; no independently scored accuracy. All entries await human review.'
      : 'Fifteen real SEC filings processed by deterministic rules. Provisional labels are unreviewed; this is not a validated performance benchmark.';
    status.textContent = `${replay.processor || 'Not run'} (${(replay.records || []).length} records)`;

    for (const record of replay.records || []) {
      const li = document.createElement('li');
      const title = document.createElement('h3');
      title.textContent = `${record.source_id} → ${record.event_type}`;
      const summary = document.createElement('p');
      summary.textContent = record.summary || '';
      const review = document.createElement('p');
      review.textContent = `Review status: ${record.review_status}`;
      const link = document.createElement('a');
      let safeURL = '';
      try {
        const candidate = new URL(record.source_url);
        if (candidate.protocol === 'https:' && ['www.sec.gov', 'data.sec.gov'].includes(candidate.hostname)) safeURL = candidate.href;
      } catch (_) { /* Invalid source URLs remain inert text. */ }
      link.href = safeURL || '#';
      link.textContent = 'Source URL';
      link.rel = 'noopener noreferrer';
      if (!safeURL) {
        link.removeAttribute('href');
      }
      li.append(title, summary, review, link);
      const flags = document.createElement('p');
      flags.textContent = `Quality flags: ${(record.validation_issues || []).join(', ') || 'None reported — semantic correctness not established'}`;
      const provenance = document.createElement('p');
      provenance.textContent = `Input SHA256: ${record.input_sha256 || 'Unavailable'}`;
      li.append(flags, provenance);
      const facts = document.createElement('ul');
      for (const fact of record.facts || []) {
        const item = document.createElement('li');
        item.textContent = `${fact.field}: ${fact.value} ${fact.currency || ''} | Evidence: ${fact.evidence?.quote || 'Missing'} [${fact.evidence?.start ?? '?'}:${fact.evidence?.end ?? '?'}]`;
        facts.appendChild(item);
      }
      li.appendChild(facts);
      list.appendChild(li);
    }
  } catch (error) {
    if (currentRequest === requestId) status.textContent = 'Recorded results could not be loaded';
    }
  }
  selector.addEventListener('change', render);
  await render();
})();
