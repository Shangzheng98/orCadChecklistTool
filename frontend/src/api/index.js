import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

export function getCheckers() {
  return api.get('/checkers');
}

export function runCheck(file, selectedCheckers) {
  const formData = new FormData();
  formData.append('file', file);
  if (selectedCheckers && selectedCheckers.length > 0) {
    formData.append('selected_checkers', selectedCheckers.join(','));
  }
  return api.post('/check', formData);
}

export function getRules() {
  return api.get('/rules');
}

export function updateRules(content) {
  return api.put('/rules', content, {
    headers: { 'Content-Type': 'text/plain' },
  });
}

export function summarize(reportJson) {
  return api.post('/summarize', { report_json: reportJson });
}

export default api;
