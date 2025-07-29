async function applyEditReplayDiff() {
  const button = document.getElementById('apply-diff-btn');
  const buttonText = document.getElementById('button-text');
  if (button.disabled) return;
  buttonText.textContent = 'Applying...';
  button.disabled = true;
 
  try {
    const params = new URLSearchParams(window.location.search);
    // Get the diff JSON from window.lastDiffJson
    const diff = window.lastDiffJson;
    if (!diff) {
      alert('No diff to apply.');
      buttonText.textContent = 'Edit Replay';
      button.disabled = false;
      return;
    }
    params.set('diff', diff);
    const url = `apply_diff?${params.toString()}`;
    const response = await fetch(url);
    const result = await response.text();
    alert(result);
    window.location.reload();
  } catch (error) {
    console.error("Error applying diff:", error);
    alert("Failed to apply diff.");
    buttonText.textContent = 'Edit Replay';
    button.disabled = false;
  }
}

async function saveEditReplay() {
  const button = document.getElementById('save-replay-btn');
  if (button.disabled) return;
  button.textContent = 'Saving...';
  button.disabled = true;
  try {
    const params = new URLSearchParams(window.location.search);
    // Get the diff JSON from window.lastDiffJson
    const diff = window.lastDiffJson;
    if (!diff) {
      alert('No diff to save.');
      button.textContent = 'Save Replay';
      button.disabled = false;
      return;
    }
    params.set('diff', diff);
    const url = `save_replay?${params.toString()}`;
    const response = await fetch(url);
    const result = await response.text();
    alert(result);
    button.textContent = 'Save Replay';
    button.disabled = false;
  } catch (error) {
    console.error('Error saving replay:', error);
    alert('Failed to save replay.');
    button.textContent = 'Save Replay';
    button.disabled = false;
  }
}

function applyFilterSuggestion(btn) {
  const suggestion = JSON.parse(btn.getAttribute('data-suggestion'));
  const params = new URLSearchParams(window.location.search);
  if (suggestion.date) {
    params.set('time', suggestion.date);
  }
  if (suggestion.account) {
    params.set('account', suggestion.account);
  }
  if (suggestion.filter) {
    let filter = params.get('filter') || '';
    if (!filter.includes(suggestion.filter)) {
      filter = filter ? filter + ' ' + suggestion.filter : suggestion.filter;
      params.set('filter', filter);
    }
  }
  window.location.search = params.toString();
}

function loadReplay(btn) {
  const time = btn.getAttribute('data-time');
  const account = btn.getAttribute('data-account');
  const filter = btn.getAttribute('data-filter');
  const diff = btn.getAttribute('data-diff');
  
  const url = new URL(window.location.href);
  url.searchParams.set('page', 'home');
  if (time) url.searchParams.set('time', time);
  if (account) url.searchParams.set('account', account);
  if (filter) url.searchParams.set('filter', filter);
  if (diff) url.searchParams.set('diff', diff);
  
  window.location.href = url.toString();
}

async function deleteReplay(btn) {
  const lineno = btn.getAttribute('data-lineno');
  
  if (!confirm('Are you sure you want to delete this replay?')) {
    return;
  }
  
  try {
    const params = new URLSearchParams(window.location.search);
    params.set('lineno', lineno);
    const url = `delete_replay?${params.toString()}`;
    const response = await fetch(url);
    const result = await response.text();
    alert(result);
    // Reload the page to refresh the replay list
    window.location.reload();
  } catch (error) {
    console.error('Error deleting replay:', error);
    alert('Failed to delete replay.');
  }
}

export default {
  onExtensionPageLoad: async () => {
    // Attach click listener to apply-diff-btn
    const applyBtn = document.getElementById('apply-diff-btn');
    if (applyBtn) {
      applyBtn.addEventListener('click', applyEditReplayDiff);
    }
    // Attach click listener to save-replay-btn
    const saveBtn = document.getElementById('save-replay-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', saveEditReplay);
    }
    // Attach click listeners to all filter-pill buttons
    document.querySelectorAll('.filter-pill').forEach(btn => {
      btn.addEventListener('click', function() {
        applyFilterSuggestion(this);
      });
    });
    // Attach click listeners to all load-replay buttons
    document.querySelectorAll('.load-replay-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        loadReplay(this);
      });
    });
    // Attach click listeners to all delete-replay buttons
    document.querySelectorAll('.delete-replay-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        deleteReplay(this);
      });
    });
    // Store the raw diff JSON for saving
    const diffJsonElem = document.getElementById('editreplay-diff-json');
    if (diffJsonElem) {
      window.lastDiffJson = diffJsonElem.textContent;
    }
    // Attach click listener to list-replays-btn
    const listReplaysBtn = document.getElementById('list-replays-btn');
    if (listReplaysBtn) {
      listReplaysBtn.addEventListener('click', function() {
        const url = new URL(window.location.href);
        url.searchParams.set('page', 'list-replays');
        window.location.href = url.toString();
      });
    }
    // Attach click listener to back-to-home-btn
    const backToHomeBtn = document.getElementById('back-to-home-btn');
    if (backToHomeBtn) {
      backToHomeBtn.addEventListener('click', function() {
        const url = new URL(window.location.href);
        url.searchParams.set('page', 'home');
        window.location.href = url.toString();
      });
    }
  }
}