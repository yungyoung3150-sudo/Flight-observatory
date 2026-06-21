/**
 * 마카오 항공 가드레일 — Google Apps Script (시트에 붙여 시트 안에서 자동 실행).
 *
 * 당신의 네이버 수집기가 채운 시트(시장최저 vs 우리요금)를 읽어, 인당·비대칭 임계로
 * 판정하고 🔴/🟠면 아이폰(Pushover)으로 알림. 봇이 네이버를 긁지 않는다 — '이미 수집된
 * 시트'만 읽는다.
 *
 *   초과액(인당) = (우리요금_2인 − 시장최저_2인) / 2     (양수 = 우리가 더 비쌈)
 *     < 5만   → 🟢 안전 (무알림)
 *     5만~10만 → 🟠 주의 (일반 알림)
 *     ≥ 10만  → 🔴 경보 (긴급 알림, 컴플레인 위험)
 *
 * ── 설치 (3단계) ─────────────────────────────────────────────
 *  1) 시트에서 확장 프로그램 → Apps Script → 이 코드 붙여넣기 → 저장
 *  2) 프로젝트 설정 → 스크립트 속성에 추가:
 *        PUSHOVER_TOKEN = (Pushover 앱 토큰),  PUSHOVER_USER = (Pushover 유저키)
 *  3) 함수 목록에서 installTriggers 1회 실행 → 권한 승인
 *     → 매일 오전 9시 / 오후 6시(KST)에 runGuardrail 자동 실행
 *  (지금 바로 테스트: runGuardrail 직접 실행 → 🔴/🟠 있으면 아이폰 알림)
 */

var WATCH_MIN_PP = 50000;    // 인당 5만 이상 = 🟠 주의(고객 이슈)
var ALARM_MIN_PP = 100000;   // 인당 10만 이상 = 🔴 경보(컴플레인)

// 읽을 방어 탭들. 시트 탭 이름이 다르면 여기 수정.
var DEFENSE_SHEETS = ['에어마카오_2박3일', '에어마카오_3박4일',
                      '에어부산_2박3일', '에어부산_3박4일'];
// 컬럼(1-base): A=날짜 B=요일 C=우리요금(2인) D=시장최저(2인)
var COL_DATE = 1, COL_OUR = 3, COL_MARKET = 4;
var TZ = 'Asia/Seoul';


function runGuardrail() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var alarms = [], watches = [];

  DEFENSE_SHEETS.forEach(function (name) {
    var sh = ss.getSheetByName(name);
    if (!sh) return;
    var rows = sh.getDataRange().getValues();
    for (var i = 1; i < rows.length; i++) {        // 0행=헤더
      var our = toNum(rows[i][COL_OUR - 1]);
      var mkt = toNum(rows[i][COL_MARKET - 1]);
      if (our === null || mkt === null) continue;  // 둘 다 있어야 판정
      var pp = Math.round((our - mkt) / 2);         // 인당 초과액
      if (pp >= ALARM_MIN_PP) {
        alarms.push(line('🔴', name, rows[i][COL_DATE - 1], mkt, pp));
      } else if (pp >= WATCH_MIN_PP) {
        watches.push(line('🟠', name, rows[i][COL_DATE - 1], mkt, pp));
      }
    }
  });

  Logger.log('경보 ' + alarms.length + ' / 주의 ' + watches.length);
  if (alarms.length === 0 && watches.length === 0) return;  // 안전 → 무알림

  var body = alarms.concat(watches).join('\n')
           + '\n→ 네이버에서 확인 후 해당 출발일 판매 보류/가격조정';
  var title = alarms.length
    ? '🔴 마카오 항공 경보(컴플레인 위험) ' + alarms.length + '건'
    : '🟠 마카오 항공 주의 ' + watches.length + '건';
  sendPushover(body, title, alarms.length ? 1 : 0);  // 경보=긴급(priority1)
}


function toNum(v) {
  if (v === '' || v === null || v === undefined) return null;
  var n = Number(String(v).replace(/[^0-9.\-]/g, ''));
  return isNaN(n) ? null : n;
}

function line(icon, sheet, date, mkt, pp) {
  return icon + ' ' + sheet + ' ' + fmtDate(date)
       + ': 인당 +' + pp.toLocaleString() + ' (시장 ' + mkt.toLocaleString() + ')';
}

function fmtDate(d) {
  return (d instanceof Date) ? Utilities.formatDate(d, TZ, 'M/d') : String(d);
}

function sendPushover(message, title, priority) {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty('PUSHOVER_TOKEN');
  var user = props.getProperty('PUSHOVER_USER');
  if (!token || !user) { Logger.log('Pushover 미설정(스크립트 속성)'); return; }
  UrlFetchApp.fetch('https://api.pushover.net/1/messages.json', {
    method: 'post',
    muteHttpExceptions: true,
    payload: {
      token: token, user: user, title: title,
      message: message, priority: String(priority)
    }
  });
}

/** 하루 2회(09시/18시 KST) 트리거 설치 — 1회만 실행. */
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'runGuardrail') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('runGuardrail').timeBased().atHour(9).everyDays(1).inTimezone(TZ).create();
  ScriptApp.newTrigger('runGuardrail').timeBased().atHour(18).everyDays(1).inTimezone(TZ).create();
  Logger.log('트리거 설치 완료: 매일 09시/18시 KST');
}
