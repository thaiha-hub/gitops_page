async function loadToday() {
  const url = window.API_URL || '/today';

  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();

    document.getElementById('date').textContent = data.date;

    var eventsEl = document.getElementById('events');
    if (data.events.length === 0) {
      eventsEl.innerHTML = '<div class="no-events">No special events today.</div>';
    } else {
      eventsEl.innerHTML = data.events
        .map(function(e) { return '<div class="event">' + e + '</div>'; })
        .join('');
    }
  } catch (err) {
    document.getElementById('date').innerHTML = '<span class="error">Error loading data</span>';
    document.getElementById('events').innerHTML = '';
    console.error('Failed to load today info:', err);
  }
}

loadToday();
