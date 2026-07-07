import "./SourceLink.css";

interface Props {
  sourceUrl: string;
  fakeNewsRiskLabel?: string | null;
}

const RISK_LABEL_KO: Record<string, string> = {
  low: "낮음",
  medium: "보통",
  high: "높음",
};

/** 뉴스 콘텐츠에는 항상 출처 URL을 노출한다 (안전 요구사항). 가짜뉴스 위험도는 어디까지나 참고용이다. */
export function SourceLink({ sourceUrl, fakeNewsRiskLabel }: Props) {
  return (
    <div className="source-link-row">
      <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="source-link">
        원문 보기 ↗
      </a>
      {fakeNewsRiskLabel && (
        <span className={`fake-news-badge risk-${fakeNewsRiskLabel}`} title="AI가 참고용으로 추정한 위험도이며 확정적 판단이 아닙니다">
          허위정보 위험도(참고용): {RISK_LABEL_KO[fakeNewsRiskLabel] ?? fakeNewsRiskLabel}
        </span>
      )}
    </div>
  );
}
