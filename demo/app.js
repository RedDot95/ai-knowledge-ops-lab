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
      link.href = record.source_url || '#';
      link.textContent = 'Source URL';
      link.rel = 'noopener noreferrer';
      if (!record.source_url) {
        link.removeAttribute('href');
      }
      li.append(title, summary, review, link);
      list.appendChild(li);
    }
  } catch (error) {
    status.textContent = 'Not run';
  }
})();
