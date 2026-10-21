(async () => {
  const status = document.getElementById('status');
  const list = document.getElementById('records');
  try {
    const response = await fetch('replay.json');
    const replay = await response.json();
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
    status.textContent = 'Not run';
  }
})();
