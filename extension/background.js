// TPT Analyzer — Background Service Worker
chrome.runtime.onInstalled.addListener(() => {
  console.log('TPT Analyzer installed');
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'SAVE_PRODUCT') {
    fetch('http://localhost:8000/api/saved', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msg.product)
    })
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(e => sendResponse({ ok: false, error: e.message }));
    return true;
  }
  if (msg.type === 'GET_TRENDING') {
    fetch('http://localhost:8000/api/trending')
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(() => sendResponse({ ok: false, data: [] }));
    return true;
  }
});
