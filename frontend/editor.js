const form = document.querySelector('#article-form');
const statusEl = document.querySelector('#status');
const queryInput = document.querySelector('#query');
const sourcesTemplate = document.querySelector('#sources-template');
const apiBaseAttribute = document.body.dataset.apiBase?.trim();
const defaultApiBase = window.location.origin.startsWith('http')
  ? window.location.origin
  : 'http://localhost:3004';
const apiBase = apiBaseAttribute || defaultApiBase;
const apiEndpoint = `${apiBase.replace(/\/$/, '')}/api/recipe-query`;
let editorInstance;

function setStatus(message, type = 'info') {
  statusEl.textContent = message;
  statusEl.dataset.statusType = type;
}

// TinyMCE expects plugins to be listed either as a space-delimited string or as
// an array of individual names. The previous implementation bundled every
// plugin into a single array item ("advlist autolink ..."), which produced
// requests for an invalid path such as
// `plugins/advlist autolink .../plugin.min.js`. Listing each plugin separately
// ensures TinyMCE loads them correctly.
tinymce.init({
  selector: '#article-editor',
  menubar: true,
  branding: false,
  height: 720,
  plugins: [
    'advlist',
    'autolink',
    'lists',
    'link',
    'image',
    'charmap',
    'preview',
    'anchor',
    'searchreplace',
    'visualblocks',
    'code',
    'fullscreen',
    'insertdatetime',
    'media',
    'table',
    'help',
    'wordcount'
  ],
  toolbar: [
    'undo redo | blocks | bold italic underline | alignleft aligncenter alignright alignjustify',
    'bullist numlist outdent indent | link image table | removeformat | code preview fullscreen | help'
  ],
  setup(editor) {
    editorInstance = editor;
  }
});

async function generateArticle(prompt) {
  const response = await fetch(apiEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: prompt })
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(errorBody.error || 'Failed to generate article');
  }

  return response.json();
}

function renderArticleContent(articleHtml, sources = []) {
  if (editorInstance) {
    editorInstance.setContent(articleHtml || '<p>No content returned.</p>');
  }

  const existingSources = document.querySelector('.article-sources');
  existingSources?.remove();

  if (!sources.length) {
    return;
  }

  const sourcesRoot = sourcesTemplate.content.cloneNode(true);
  const list = sourcesRoot.querySelector('ul');
  list.innerHTML = sources
    .map((url) => `<li><a href="${url}" target="_blank" rel="noopener">${url}</a></li>`)
    .join('');

  const panel = document.createElement('aside');
  panel.className = 'article-sources';
  panel.appendChild(sourcesRoot);

  document.querySelector('.editor')?.appendChild(panel);
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const prompt = queryInput.value.trim();

  if (!prompt) {
    setStatus('Please enter a prompt describing the article you need.', 'error');
    return;
  }

  setStatus('Generating article… This may take a moment.');
  form.querySelector('button').disabled = true;

  try {
    const { article, sources } = await generateArticle(prompt);
    renderArticleContent(article, sources);
    setStatus('Draft ready! You can continue editing before publishing.', 'success');
  } catch (error) {
    console.error(error);
    setStatus(error.message || 'Something went wrong while generating the article.', 'error');
  } finally {
    form.querySelector('button').disabled = false;
  }
});
