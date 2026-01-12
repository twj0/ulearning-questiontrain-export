// ==UserScript==
// @name         ulearning-questiontrain-export
// @namespace    https://lms.dgut.edu.cn/
// @version      0.1.2
// @description  Export ULearning question training to 佛脚刷题 JSON and download (strip HTML tags)
// @match        https://lms.dgut.edu.cn/utest/index.html*
// @grant        GM_setClipboard
// @grant        GM_notification
// ==/UserScript==

(function () {
  'use strict';

  /**
   * API base URL.
   * @type {string}
   */
  const API_BASE = 'https://lms.dgut.edu.cn/utestapi';
  
  /**
   * Page size for questionList.
   * @type {number}
   */
  const PAGE_SIZE = 30;
  
  /**
   * Delay between answer submissions (ms).
   * Safety consideration.
   * @type {number}
   */
  const ANSWER_DELAY_MS = 180; // 180ms per answer

  /**
   * Get cookie value by name.
   * @param {string} name - Cookie name
   * @returns {string} Cookie value or empty string
   */
  function getCookie(name) {
    const parts = document.cookie.split(';').map(s => s.trim());
    for (const p of parts) {
      if (p.startsWith(name + '=')) return decodeURIComponent(p.slice(name.length + 1));
    }
    return '';
  }

  /**
   * Safely parse JSON string.
   * @param {string} s - JSON string
   * @returns {any|null} Parsed object or null if parsing fails
   */
  function safeJsonParse(s) {
    try { return JSON.parse(s); } catch { return null; }
  }

  /**
   * Parse practice hash parameters.
   * @returns {{qtId: string, ocId: string, qtType: string} | null} Parsed ids or null if not on practice page
   */
  function parseHashParams() {
    // Example:
    //   #/questionTrain/practice/2674/134202/1
    const hash = location.hash || '';
    const m = hash.match(/#\/questionTrain\/practice\/(\d+)\/(\d+)\/(\d+)/);
    if (!m) return null;
    return { qtId: m[1], ocId: m[2], qtType: m[3] };
  }

  /**
   * Read Authorization token and userId from cookies.
   * @returns {{authorization: string, userId: string}}
   */
  function getAuthAndUserId() {
    const authorization = getCookie('AUTHORIZATION') || getCookie('token');
    const userInfoRaw = getCookie('USERINFO') || getCookie('USER_INFO');
    const userInfo = userInfoRaw ? safeJsonParse(userInfoRaw) : null;
    const userId = userInfo && userInfo.userId ? String(userInfo.userId) : '';
    return { authorization: normalizeAuthorization(authorization), userId };
  }

  function normalizeAuthorization(raw) {
    const v = (raw || '').trim();
    if (!v) return '';
    // Already has scheme
    if (/^bearer\s+/i.test(v)) return v;
    // Heuristic: JWT-like token -> Bearer
    if (v.split('.').length >= 3) return `Bearer ${v}`;
    return v;
  }

  /**
   * Send GET request to API.
   * @param {string} path - API path
   * @param {Object} params - Query params
   * @param {string} authorization - Authorization token
   * @returns {Promise<Object>} API response
   * @throws {Error} When HTTP fails or API returns error
   */
  async function apiGet(path, params, authorization) {
    const url = new URL(API_BASE + path);
    Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, String(v)));

    const res = await fetch(url.toString(), {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': authorization || '',
      },
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    if (!data || data.code !== 1) {
      if (data && data.code === 2001) {
        throw new Error('API error: 缺少访问token (请重新登录页面，确保 cookie 里有 AUTHORIZATION；token 可能不等价于 AUTHORIZATION)');
      }
      throw new Error(`API error: ${data && data.message ? data.message : 'unknown'}`);
    }
    return data;
  }

  /**
   * Send POST request to API.
   * @param {string} path - API path
   * @param {Object} params - Query params
   * @param {Object} payload - JSON body
   * @param {string} authorization - Authorization token
   * @returns {Promise<Object>} API response
   * @throws {Error} When HTTP fails or API returns invalid response
   */
  async function apiPost(path, params, payload, authorization) {
    const url = new URL(API_BASE + path);
    Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, String(v)));

    const res = await fetch(url.toString(), {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=utf-8',
        'Authorization': authorization || '',
      },
      body: JSON.stringify(payload || {}),
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    // This endpoint returns code=1 (correct) or code=2 (wrong). Both are valid for extracting correctAnswer.
    if (!data || typeof data.code === 'undefined') {
      throw new Error('API error: invalid response');
    }
    if (data.code === 2001) {
      throw new Error('API error: 缺少访问token (请重新登录页面，确保 cookie 里有 AUTHORIZATION；token 可能不等价于 AUTHORIZATION)');
    }
    return data;
  }

  /**
   * Build answer map from answerSheet (legacy user answers).
   * @param {Object} answerSheet - answerSheet response
   * @returns {Map} questionId -> {answer, correct, questionType}
   */
  function buildAnswerMap(answerSheet) {
    const m = new Map();
    const list = answerSheet?.result?.list || [];
    for (const item of list) {
      m.set(item.id, {
        answer: Array.isArray(item.answer) ? item.answer : [],
        correct: item.correct,
        questionType: item.questionType,
      });
    }
    return m;
  }

  /**
   * Pick a dummy answer to trigger correctAnswer.
   * @param {Object} q - Question object
   * @returns {Array<string>} Dummy answer array
   */
  function pickDummyAnswer(q) {
    // Minimal dummy answer to trigger correctAnswer.
    // Choice: A; True/False: A; Fill/Eassy: empty string.
    if (q.type === 1 || q.type === 2 || q.type === 3) return ['A'];
    if (q.type === 4 || q.type === 5) return [''];
    return ['A'];
  }

  function stripHtml(raw) {
    if (raw === null || typeof raw === 'undefined') return '';
    let s = String(raw);
    if (!s) return '';
    // Normalize common line breaks to \n
    s = s.replace(/<\s*br\s*\/?\s*>/gi, '\n');
    // End of common blocks -> newline
    s = s.replace(/<\s*\/\s*(p|div|li|tr)\s*>/gi, '\n');
    // Remove remaining tags
    s = s.replace(/<[^>]+>/g, '');
    // Decode HTML entities - decode twice for double-encoded entities (e.g. &amp;ldquo; -> &ldquo; -> ")
    const ta = document.createElement('textarea');
    ta.innerHTML = s;
    s = ta.value;
    ta.innerHTML = s;
    s = ta.value;
    // Normalize line endings
    s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    // Normalize spaces
    s = s.replace(/[\t\f\v]+/g, ' ');
    s = s.replace(/[ \u00a0]+/g, ' ');
    s = s.replace(/\n{3,}/g, '\n\n');
    return s;
  }

  /**
   * Format raw question to 佛脚刷题 format.
   * NOTE: Output keys should follow tmpl.jsonc (Chinese keys).
   *
   * Type detection:
   * - If answer is boolean-ish (true/false), force it to be 判断题.
   * - Some trainings encode True/False as type=4; detect by two options like 正确/错误.
   */
  function formatToFojiao(q) {
    const typeMap = {
      1: '选择题',
      2: '选择题',
      3: '判断题',
      4: '填空题',
      5: '问答题',
    };
    const optionLabels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];

    const items = Array.isArray(q.item) ? q.item : [];
    const title = stripHtml(q.title).trim();
    const ans = Array.isArray(q.userAnswer) ? q.userAnswer : [];

    const looksLikeTrueFalse = (() => {
      if (q.type !== 4) return false;
      if (!Array.isArray(items) || items.length !== 2) return false;
      const t0 = (items[0] && items[0].title ? String(items[0].title) : '').trim();
      const t1 = (items[1] && items[1].title ? String(items[1].title) : '').trim();
      const merged = `${t0}${t1}`;
      return ['正确', '错误', '对', '错', '是', '否'].some(k => merged.includes(k));
    })();

    const answerIsBoolish = (() => {
      if (!ans.length) return false;
      const a0 = ans[0];
      if (typeof a0 === 'boolean') return true;
      const s = String(a0).trim().toLowerCase();
      return s === 'true' || s === 'false';
    })();

    const qType = looksLikeTrueFalse ? '判断题' : (typeMap[q.type] || '选择题');
    const finalType = answerIsBoolish ? '判断题' : qType;

    if (finalType === '选择题') {
      const options = items.map((it, idx) => {
        const label = optionLabels[idx] || String(idx);
        const text = stripHtml(it && it.title ? it.title : '').trim();
        return `${label}. ${text}`;
      });

      const answerStr = ans.length ? ans.slice().sort().join('') : '';
      return { '题型': '选择题', '题干': title, '选项': options, '答案': answerStr, '解析': '' };
    }

    if (finalType === '判断题') {
      let answerStr = '';
      if (ans.length) {
        const a0 = ans[0];
        if (['A', '正确', 'True', 'true', '对', '√'].includes(a0)) answerStr = '正确';
        else if (['B', '错误', 'False', 'false', '错', '×'].includes(a0)) answerStr = '错误';
        else if (typeof a0 === 'boolean') answerStr = a0 ? '正确' : '错误';
        else if (String(a0).trim().toLowerCase() === 'true') answerStr = '正确';
        else if (String(a0).trim().toLowerCase() === 'false') answerStr = '错误';
        else answerStr = String(a0);
      }
      return { '题型': '判断题', '题干': title, '答案': answerStr, '解析': '' };
    }

    if (finalType === '填空题') {
      let formattedTitle = title;
      if (ans.length) {
        const patterns = [
          /_{2,}/,
          /\(\s*\)/,
          /【\s*】/,
          /\[\s*\]/,
        ];

        for (let i = 0; i < ans.length; i++) {
          const a = String(ans[i]);
          let replaced = false;
          for (const pat of patterns) {
            if (pat.test(formattedTitle)) {
              formattedTitle = formattedTitle.replace(pat, `{${a}}`);
              replaced = true;
              break;
            }
          }
          if (!replaced) {
            formattedTitle += i === 0 ? ` {${a}}` : `, {${a}}`;
          }
        }
      }
      return { '题型': '填空题', '题干': formattedTitle, '解析': '' };
    }

    if (finalType === '问答题') {
      const answerStr = ans.length ? ans.map(x => String(x)).join('\n') : '';
      return { '题型': '问答题', '题干': title, '答案': answerStr, '解析': '' };
    }

    return null;
  }

  /**
   * Download JSON file.
   * @param {Object[]} data - JSON data
   * @param {string} filename - File name
   */
  function downloadJson(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  /**
   * Show notification.
   * @param {string} text - Message
   */
  function notify(text) {
    if (typeof GM_notification === 'function') {
      GM_notification({ text, title: 'ULearning Export Helper', timeout: 3500 });
    } else {
      alert(text);
    }
  }

  /**
   * Add export button to the page.
   */
  function addButton() {
    const btn = document.createElement('button');
    btn.textContent = 'Export Correct Answers JSON';
    btn.style.cssText = [
      'position:fixed',
      'right:16px',
      'bottom:16px',
      'z-index:999999',
      'padding:10px 12px',
      'border:1px solid #ccc',
      'border-radius:10px',
      'background:#fff',
      'color:#111',
      'font-size:14px',
      'cursor:pointer',
      'box-shadow:0 6px 18px rgba(0,0,0,.12)'
    ].join(';');

    // Bind click handler
    btn.addEventListener('click', async () => {
      try {
        btn.disabled = true;
        btn.textContent = 'Exporting...';

        // Parse current page hash params
        const hashParams = parseHashParams();

        if (!hashParams) {
          throw new Error('Not on practice page: #/questionTrain/practice/{qtId}/{ocId}/{qtType}');
        }

        // Get authorization and user id
        const { authorization, userId } = getAuthAndUserId();

        if (!authorization) {
          throw new Error('Missing Authorization cookie (AUTHORIZATION or token)');
        }
        if (!userId) {
          throw new Error('Missing USERINFO cookie (cannot get userId)');
        }

        const qtId = hashParams.qtId;
        const ocId = hashParams.ocId;
        const qtType = hashParams.qtType;

        notify('Fetching question list...');
        // Fetch answerSheet mainly for the official order (index list)
        const answerSheet = await apiGet(
          '/questionTraining/student/answerSheet',
          { qtId, ocId, qtType, traceId: userId },
          authorization
        );
        const sheetList = answerSheet?.result?.list || [];
        const total = Number(answerSheet?.result?.total || sheetList.length || 0);
        const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

        // Optional: ask whether to limit submissions (safety)
        const input = prompt(
          '导出正确答案: 导出多少呢?（导出900个题目大概要4分钟，主要取决于网速）\n' +
            '- 留空 = 导出全部\n' +
            '- 数字 = 只导出前N个 (测试中)',
          ''
        );
        const limitN = input && String(input).trim() ? Number(String(input).trim()) : null;
        const maxToSubmit = Number.isFinite(limitN) && limitN > 0 ? Math.floor(limitN) : null;

        // Fetch all raw questions
        const allRawQuestions = [];

        for (let page = 1; page <= totalPages; page++) {
          btn.textContent = `Exporting... ${page}/${totalPages}`;
          const qList = await apiGet(
            '/questionTraining/student/questionList',
            { qtId, ocId, qtType, pn: page, ps: PAGE_SIZE, traceId: userId },
            authorization
          );
          const trainingQuestions = qList?.result?.trainingQuestions || [];
          for (const q of trainingQuestions) allRawQuestions.push(q);
          // Small delay to avoid hammering server
          await new Promise(r => setTimeout(r, 250));
        }

        // Build quick map: questionId -> question object
        const qMap = new Map();

        for (const q of allRawQuestions) qMap.set(q.id, q);

        // Collect correct answers by submitting dummy answers in sheet order
        notify('Collecting correct answers (this will submit answers)...');

        const correctMap = new Map();
        for (let idx = 0; idx < sheetList.length; idx++) {
          if (maxToSubmit !== null && idx >= maxToSubmit) break;
          const item = sheetList[idx];
          const qid = item.id;
          const q = qMap.get(qid) || { id: qid, type: item.questionType };

          const dummy = pickDummyAnswer(q);

          const resp = await apiPost(
            '/questionTraining/student/answer',
            { traceId: userId },
            { qtId: Number(qtId), qtType: Number(qtType), index: idx, relationId: qid, answer: dummy },
            authorization
          );
          const ca = resp?.result?.correctAnswer;
          correctMap.set(qid, Array.isArray(ca) ? ca.map(String) : []);

          if ((idx + 1) % 20 === 0) {
            notify(`Collected correct answers: ${idx + 1}/${maxToSubmit ?? sheetList.length}`);
          }
          await new Promise(r => setTimeout(r, ANSWER_DELAY_MS));
        }

        // Attach correct answers to question objects
        for (const q of allRawQuestions) {
          if (correctMap.has(q.id)) {
            q.userAnswer = correctMap.get(q.id);
          }
        }

        // Format to 佛脚刷题 format
        const formatted = allRawQuestions
          .map(formatToFojiao)
          .filter(Boolean);

        // Download JSON file
        const filename = `ulearning_${qtId}_${ocId}_${qtType}_questions.json`;
        downloadJson(formatted, filename);

        notify(`Exported ${formatted.length} questions`);
      } catch (e) {
        notify(String(e && e.message ? e.message : e));
      } finally {
        btn.disabled = false;
        btn.textContent = 'Export Correct Answers JSON';
      }
    });

    document.body.appendChild(btn);
  }

  // Add button after page loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addButton);
  } else {
    addButton();
  }
})();