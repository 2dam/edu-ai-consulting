import { useState } from "react";
import type { ReportReason } from "../../api/types";
import "./ReportButton.css";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "spam", label: "스팸/광고" },
  { value: "abuse", label: "욕설/비방" },
  { value: "personal_info", label: "개인정보 노출" },
  { value: "fake_news", label: "허위 정보" },
  { value: "other", label: "기타" },
];

interface Props {
  onReport: (reason: ReportReason, detail?: string) => Promise<unknown>;
}

export function ReportButton({ onReport }: Props) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState("");
  const [done, setDone] = useState(false);

  if (done) {
    return <span className="report-done">신고 접수됨</span>;
  }

  return (
    <div className="report-widget">
      <button type="button" className="report-toggle" onClick={() => setOpen((v) => !v)}>
        신고
      </button>
      {open && (
        <div className="report-popover">
          {REASONS.map((r) => (
            <button
              key={r.value}
              type="button"
              className="report-reason"
              onClick={async () => {
                await onReport(r.value, detail || undefined);
                setOpen(false);
                setDone(true);
              }}
            >
              {r.label}
            </button>
          ))}
          <input
            className="report-detail-input"
            placeholder="상세 내용 (선택)"
            value={detail}
            onChange={(e) => setDetail(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}
