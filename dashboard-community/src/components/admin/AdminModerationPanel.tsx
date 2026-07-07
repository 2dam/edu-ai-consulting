import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { getReportQueue, moderateCommunityPost, moderateNewsPost } from "../../api/admin";
import type { ReportQueueItem } from "../../api/types";
import "./AdminModerationPanel.css";

const STATUS_OPTIONS = ["open", "reviewing", "actioned", "dismissed", "all"];

const REASON_KO: Record<string, string> = {
  spam: "스팸/광고",
  abuse: "욕설/비방",
  personal_info: "개인정보 노출",
  fake_news: "허위 정보",
  other: "기타",
};

export function AdminModerationPanel() {
  const [status, setStatus] = useState("open");
  const [reports, setReports] = useState<ReportQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  function load() {
    setLoading(true);
    setForbidden(false);
    getReportQueue(status)
      .then(setReports)
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 403 || e.status === 401)) setForbidden(true);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, [status]);

  async function handleAction(report: ReportQueueItem, action: "hidden" | "deleted") {
    setBusyId(report.id);
    try {
      if (report.target_type === "news_post") {
        await moderateNewsPost(report.target_id, action, `report#${report.id}`, report.id);
      } else {
        await moderateCommunityPost(report.target_id, action, `report#${report.id}`, report.id);
      }
      load();
    } finally {
      setBusyId(null);
    }
  }

  if (forbidden) {
    return <p className="empty-text">관리자만 접근할 수 있습니다. 관리자 계정(user_id=1)으로 등록되어 있는지 확인해주세요.</p>;
  }

  return (
    <div className="admin-panel">
      <div className="page-toolbar">
        <h1 className="page-title">신고 관리</h1>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="loading-text">불러오는 중...</p>}
      {!loading && reports.length === 0 && <p className="empty-text">해당 상태의 신고가 없어요.</p>}

      <ul className="report-queue">
        {reports.map((r) => (
          <li key={r.id} className="report-queue-item">
            <div className="report-queue-meta">
              <span className="report-target-type">{r.target_type}</span>
              <span className="report-reason-badge">{REASON_KO[r.reason] ?? r.reason}</span>
              <span className="report-status-badge">{r.status}</span>
            </div>
            <p className="report-preview">{r.target_preview}</p>
            {r.detail && <p className="report-detail">신고 사유: {r.detail}</p>}
            {r.target_type === "comment" ? (
              <p className="report-unsupported">댓글 단위 모더레이션은 아직 지원되지 않습니다 (TODO).</p>
            ) : (
              <div className="report-actions">
                <button disabled={busyId === r.id} onClick={() => handleAction(r, "hidden")}>
                  숨기기
                </button>
                <button disabled={busyId === r.id} className="danger" onClick={() => handleAction(r, "deleted")}>
                  삭제
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
