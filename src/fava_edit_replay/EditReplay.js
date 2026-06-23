async function applyEditReplayDiff() {
  const button = document.getElementById('apply-diff-btn');
  const buttonText = document.getElementById('button-text');
  const defaultApplyLabel = button?.dataset.defaultLabel || buttonText?.textContent || 'Apply Replay';
  if (button.disabled) return;
  buttonText.textContent = 'Applying...';
  button.disabled = true;

  try {
    const params = new URLSearchParams(window.location.search);
    // Get the diff JSON from window.lastDiffJson
    const diff = window.lastDiffJson;
    if (!diff) {
      alert('No diff to apply.');
      buttonText.textContent = defaultApplyLabel;
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
    buttonText.textContent = defaultApplyLabel;
    button.disabled = false;
  }
}

async function saveEditReplay() {
  const button = document.getElementById('save-replay-btn');
  const saveLabel = button?.querySelector('span')?.textContent || 'Save as Permanent Rule';
  if (button.disabled) return;
  button.textContent = 'Saving...';
  button.disabled = true;
  try {
    const params = new URLSearchParams(window.location.search);
    // Get the diff JSON from window.lastDiffJson
    const diff = window.lastDiffJson;
    if (!diff) {
      alert('No diff to save.');
      button.textContent = saveLabel;
      button.disabled = false;
      return;
    }
    params.set('diff', diff);
    const url = `save_replay?${params.toString()}`;
    const response = await fetch(url);
    const result = await response.text();
    alert(result);
    button.textContent = saveLabel;
    button.disabled = false;
  } catch (error) {
    console.error('Error saving replay:', error);
    alert('Failed to save replay.');
    button.textContent = saveLabel;
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

function handleEditReplayKeydown(event) {
  if (!(event.metaKey || event.ctrlKey) || event.key !== 's') {
    return;
  }
  const form = document.getElementById('edit-replay-form');
  const submitBtn = form?.querySelector('button[type="submit"]');
  if (!form || submitBtn?.disabled) {
    return;
  }
  event.preventDefault();
  form.requestSubmit();
}

function openEditReplayModal(btn) {
  const overlay = document.getElementById('edit-replay-overlay');
  if (!overlay) return;

  document.getElementById('edit-lineno').value = btn.getAttribute('data-lineno') || '';
  document.getElementById('edit-time-filter').value = btn.getAttribute('data-time') || '';
  document.getElementById('edit-account-filter').value = btn.getAttribute('data-account') || '';
  document.getElementById('edit-advanced-filter').value = btn.getAttribute('data-filter') || '';
  document.getElementById('edit-diff').value = btn.getAttribute('data-diff') || '';

  overlay.hidden = false;
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', handleEditReplayKeydown);
  document.getElementById('edit-time-filter').focus();
}

function closeEditReplayModal() {
  const overlay = document.getElementById('edit-replay-overlay');
  if (!overlay) return;
  overlay.hidden = true;
  document.body.style.overflow = '';
  document.removeEventListener('keydown', handleEditReplayKeydown);
}

async function saveEditedReplay(event) {
  event.preventDefault();
  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  const saveLabel = submitBtn.textContent;
  submitBtn.textContent = 'Saving...';
  submitBtn.disabled = true;

  try {
    const params = new URLSearchParams(window.location.search);
    params.set('lineno', form.lineno.value);
    params.set('time', form.time_filter.value);
    params.set('account', form.account_filter.value);
    params.set('filter', form.advanced_filter.value);
    params.set('diff', form.diff.value);
    const response = await fetch(`update_replay?${params.toString()}`);
    const result = await response.text();
    if (result === 'Replay updated.') {
      window.location.reload();
      return;
    }
    alert(result);
  } catch (error) {
    console.error('Error updating replay:', error);
    alert('Failed to update replay.');
  } finally {
    submitBtn.textContent = saveLabel;
    submitBtn.disabled = false;
  }
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

async function applyAllReplays() {
  if (!confirm('This will apply all replays to all the transactions in the ledger, are you sure?')) {
    return;
  }
  
  const button = document.getElementById('apply-all-replays-btn');
  const buttonText = button.querySelector('span');
  const originalText = buttonText.textContent;
  
  buttonText.textContent = 'Applying...';
  button.disabled = true;
  
  try {
    const params = new URLSearchParams(window.location.search);
    const url = `apply_all_replays?${params.toString()}`;
    const response = await fetch(url);
    const result = await response.text();
    alert(result);
    // Reload the page to refresh the replay list
    window.location.reload();
  } catch (error) {
    console.error('Error applying all replays:', error);
    alert('Failed to apply all replays.');
    buttonText.textContent = originalText;
    button.disabled = false;
  }
}

const LIST_REPLAYS_COLUMNS_KEY = 'editreplay-list-replays-hidden-columns';

function getHiddenListReplayColumns() {
  try {
    const stored = localStorage.getItem(LIST_REPLAYS_COLUMNS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function setHiddenListReplayColumns(hidden) {
  localStorage.setItem(LIST_REPLAYS_COLUMNS_KEY, JSON.stringify(hidden));
}

function applyListReplayColumnVisibility(table, hiddenColumns) {
  table.querySelectorAll('[data-column]').forEach((el) => {
    const column = el.getAttribute('data-column');
    el.classList.toggle('editreplay-col-hidden', hiddenColumns.includes(column));
  });
}

function initListReplaysColumnToggles() {
  const table = document.querySelector('.editreplay-list-replays-container table');
  const toggles = document.querySelector('.editreplay-column-toggles');
  if (!table || !toggles) {
    return;
  }

  const hiddenColumns = getHiddenListReplayColumns();
  applyListReplayColumnVisibility(table, hiddenColumns);

  toggles.querySelectorAll('input[data-column]').forEach((input) => {
    const column = input.getAttribute('data-column');
    input.checked = !hiddenColumns.includes(column);
    input.addEventListener('change', () => {
      const hidden = getHiddenListReplayColumns();
      if (input.checked) {
        const index = hidden.indexOf(column);
        if (index >= 0) {
          hidden.splice(index, 1);
        }
      } else if (!hidden.includes(column)) {
        hidden.push(column);
      }
      setHiddenListReplayColumns(hidden);
      applyListReplayColumnVisibility(table, hidden);
    });
  });
}

function handleJournalClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement) || target instanceof HTMLAnchorElement) {
    return;
  }
  if (target.closest('.indicators')) {
    target.closest('.journal > li')?.classList.toggle('show-full-entry');
  }
}

export default {
  onExtensionPageLoad: async () => {
    document
      .querySelector('.editreplay-transactions-container ol.journal')
      ?.addEventListener('click', handleJournalClick);
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
    const txnDiffToggles = document.querySelector('.txn-diff-view-toggles');
    if (txnDiffToggles) {
      const component = txnDiffToggles.closest('.editreplay-header-block')?.querySelector('.txn-diff-component');
      const diffView = component?.querySelector('.txn-diff-view--ledger');
      const textView = component?.querySelector('.txn-diff-view--text');
      const textBtn = txnDiffToggles.querySelector('.txn-diff-view-btn--text');
      const diffBtn = txnDiffToggles.querySelector('.txn-diff-view-btn--diff');

      const setTxnDiffView = (view) => {
        const showDiff = view === 'diff';
        if (diffView) {
          diffView.hidden = !showDiff;
        }
        if (textView) {
          textView.hidden = showDiff;
        }
        textBtn?.classList.toggle('txn-diff-view-btn--active', !showDiff);
        diffBtn?.classList.toggle('txn-diff-view-btn--active', showDiff);
        textBtn?.setAttribute('aria-pressed', showDiff ? 'false' : 'true');
        diffBtn?.setAttribute('aria-pressed', showDiff ? 'true' : 'false');
      };

      textBtn?.addEventListener('click', () => setTxnDiffView('text'));
      diffBtn?.addEventListener('click', () => setTxnDiffView('diff'));
    }
    // Attach click listeners to all filter-pill buttons
    document.querySelectorAll('.filter-pill').forEach(btn => {
      btn.addEventListener('click', function() {
        applyFilterSuggestion(this);
      });
    });
    // Attach click listeners to all edit-replay buttons
    document.querySelectorAll('.edit-replay-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        openEditReplayModal(this);
      });
    });
    const editOverlay = document.getElementById('edit-replay-overlay');
    if (editOverlay) {
      editOverlay.querySelector('.editreplay-overlay-bg')?.addEventListener('click', closeEditReplayModal);
      editOverlay.querySelector('.editreplay-overlay-close')?.addEventListener('click', closeEditReplayModal);
      document.getElementById('edit-replay-form')?.addEventListener('submit', saveEditedReplay);
    }
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
    // Attach click listener to apply-all-replays-btn
    const applyAllReplaysBtn = document.getElementById('apply-all-replays-btn');
    if (applyAllReplaysBtn) {
      applyAllReplaysBtn.addEventListener('click', applyAllReplays);
    }
    initListReplaysColumnToggles();
  }
}