// ==UserScript==
// @name         ulearning-questiontrain-export
// @namespace    https://lms.dgut.edu.cn/
// @version      0.1.0
// @description  Export ULearning question training to 佛脚刷题 JSON and download
// @match        https://lms.dgut.edu.cn/utest/index.html*
// @grant        GM_setClipboard
// @grant        GM_notification
// ==/UserScript==

(function () {
  'use strict';

  const API_BASE = 'https://lms.dgut.edu.cn/utestapi';
  const PAGE_SIZE = 30;

  function getCookie(name) {
    const parts = document.cookie.split(';').map(s => s.trim());
    for (const p of parts) {
      if (p.startsWith(name + '=')) return decodeURIComponent(p.slice(name.length + 1));
    }
    return '';
  }

  function safeJsonParse(s) {
    try { return JSON.parse(s); } catch { return null; }
  }

  function parseHashParams() {
    // Example:
    //   #/questionTrain/practice/2674/134202/1
    const hash = location.hash || '';
    const m = hash.match(/#\/questionTrain\/practice\/(\d+)\/(\d+)\/(\d+)/);
    if (!m) return null;
    return { qtId: m[1], ocId: m[2], qtType: m[3] };
  }

  function getAuthAndUserId() {
    const authorization = getCookie('AUTHORIZATION') || getCookie('token');
    const userInfoRaw = getCookie('USERINFO') || getCookie('USER_INFO');
    const userInfo = userInfoRaw ? safeJsonParse(userInfoRaw) : null;
    const userId = userInfo && userInfo.userId ? String(userInfo.userId) : '';
    return { authorization, userId };
  }

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
      throw new Error(`API error: ${data && data.message ? data.message : 'unknown'}`);
    }
    return data;
  }

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

  function formatToFojiao(q) {
    // Keep same behavior as Python formatter
    const typeMap = {
      1: '选择题',
      2: '选择题',
      3: '判断题',
      4: '填空题',
      5: '问答题',
    };
    const optionLabels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];

    const qType = typeMap[q.type] || '选择题';
    const title = (q.title || '').trim();
    const items = Array.isArray(q.item) ? q.item : [];
    const ans = Array.isArray(q.userAnswer) ? q.userAnswer : [];

    if (qType === '选择题') {
      const options = items.map((it, idx) => {
        const label = optionLabels[idx] || String(idx);
        const text = (it && it.title ? String(it.title) : '').trim();
        return `${label}. ${text}`;
      });
      const answerStr = ans.length ? ans.slice().sort().join('') : '';
      return { '题型': '选择题', '题干': title, '选项': options, '答案': answerStr, '解析': '' };
    }

    if (qType === '判断题') {
      let answerStr = '';
      if (ans.length) {
        const a0 = ans[0];
        if (['A', '正确', 'True', 'true', '对', '√'].includes(a0)) answerStr = '正确';
        else if (['B', '错误', 'False', 'false', '错', '×'].includes(a0)) answerStr = '错误';
        else answerStr = String(a0);
      }
      return { '题型': '判断题', '题干': title, '答案': answerStr, '解析': '' };
    }

    if (qType === '填空题') {
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

    if (qType === '问答题') {
      const answerStr = ans.length ? ans.map(x => String(x)).join('\n') : '';
      return { '题型': '问答题', '题干': title, '答案': answerStr, '解析': '' };
    }

    return null;
  }

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

  function notify(text) {
    if (typeof GM_notification === 'function') {
      GM_notification({ text, title: 'ULearning Export Helper', timeout: 3500 });
    } else {
      alert(text);
    }
  }

  function addButton() {
    const btn = document.createElement('button');
    btn.textContent = 'Export Questions JSON';
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

    btn.addEventListener('click', async () => {
      try {
        btn.disabled = true;
        btn.textContent = 'Exporting...';

        const hashParams = parseHashParams();
        if (!hashParams) {
          throw new Error('Not on practice page: #/questionTrain/practice/{qtId}/{ocId}/{qtType}');
        }

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

        notify('Fetching answer sheet...');
        const answerSheet = await apiGet(
          '/questionTraining/student/answerSheet',
          { qtId, ocId, qtType, traceId: userId },
          authorization
        );
        const total = Number(answerSheet?.result?.total || 0);
        const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

        const answerMap = buildAnswerMap(answerSheet);

        const allRawQuestions = [];
        for (let page = 1; page <= totalPages; page++) {
          btn.textContent = `Exporting... ${page}/${totalPages}`;
          const qList = await apiGet(
            '/questionTraining/student/questionList',
            { qtId, ocId, qtType, pn: page, ps: PAGE_SIZE, traceId: userId },
            authorization
          );
          const trainingQuestions = qList?.result?.trainingQuestions || [];
          for (const q of trainingQuestions) {
            const a = answerMap.get(q.id);
            if (a) {
              q.userAnswer = a.answer;
              q.isCorrect = a.correct;
            }
            allRawQuestions.push(q);
          }
          // Small delay to avoid hammering server
          await new Promise(r => setTimeout(r, 250));
        }

        const formatted = allRawQuestions
          .map(formatToFojiao)
          .filter(Boolean);

        const filename = `ulearning_${qtId}_${ocId}_${qtType}_questions.json`;
        downloadJson(formatted, filename);
        notify(`Exported ${formatted.length} questions`);
      } catch (e) {
        notify(String(e && e.message ? e.message : e));
      } finally {
        btn.disabled = false;
        btn.textContent = 'Export Questions JSON';
      }
    });

    document.body.appendChild(btn);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addButton);
  } else {
    addButton();
  }
})();
