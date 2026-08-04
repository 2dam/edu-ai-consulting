
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { getAdmissionVideos } from "../api/videos";
import type { AdmissionVideoOut } from "../api/types";
import "./AdmissionVideos.css";

const TOPICS = ["전체", "대입 입시", "수시 학생부종합", "정시 수능", "대학 입학전형"];

function formatCount(value: number) {
  return new Intl.NumberFormat("ko-KR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function formatDate(value: string | null) {
  if (!value) return "게시일 미상";
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium" }).format(new Date(value));
}

export function AdmissionVideos() {
  const [videos, setVideos] = useState<AdmissionVideoOut[]>([]);
  const [topic, setTopic] = useState("전체");
  const [draft, setDraft] = useState("");
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(0);

  useEffect(() => {
    let active = true;
    const load = (showLoading = false) => {
      if (showLoading) setLoading(true);
      setError("");
      getAdmissionVideos({
        q: keyword || undefined,
        searchQuery: topic === "전체" ? undefined : topic,
        limit: 100,
      })
        .then((page) => {
          if (!active) return;
          setVideos(page.items);
          setTotal(page.total);
        })
        .catch(() => {
          if (!active) return;
          if (showLoading) {
            setVideos([]);
            setTotal(0);
          }
          setError("입시 영상 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
        })
        .finally(() => {
          if (active && showLoading) setLoading(false);
        });
    };

    load(true);
    const intervalId = window.setInterval(() => load(), 60_000);
    const refreshOnFocus = () => load();
    window.addEventListener("focus", refreshOnFocus);
    return () => {
      active = false;
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refreshOnFocus);
    };
  }, [keyword, topic]);

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    setKeyword(draft.trim());
  };

  return (
    <section className="video-page">
      <div className="video-heading">
        <div>
          <p className="video-eyebrow">YouTube Data API · 공개 영상</p>
          <h1>입시 영상</h1>
          <p>수시·정시·학생부·대학 전형 정보를 최신 공개 영상으로 확인하세요.</p>
        </div>
        <span className="video-total">{total.toLocaleString("ko-KR")}개 영상</span>
      </div>

      <form className="video-search" onSubmit={submitSearch}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="영상 제목 또는 채널 검색"
          aria-label="입시 영상 검색"
        />
        <button type="submit">검색</button>
      </form>

      <div className="video-topics" aria-label="입시 영상 주제">
        {TOPICS.map((item) => (
          <button
            key={item}
            type="button"
            className={topic === item ? "active" : ""}
            onClick={() => setTopic(item)}
          >
            {item}
          </button>
        ))}
      </div>

      {loading && <p className="video-state">영상을 불러오는 중입니다…</p>}
      {!loading && error && <p className="video-state error">{error}</p>}
      {!loading && !error && videos.length === 0 && (
        <p className="video-state">조건에 맞는 영상이 없습니다.</p>
      )}

      <div className="video-grid">
        {videos.map((video) => (
          <article className="video-card" key={video.video_id}>
            <a href={video.source_url} target="_blank" rel="noreferrer" className="video-thumbnail">
              {video.thumbnail_url ? (
                <img src={video.thumbnail_url} alt="" loading="lazy" />
              ) : (
                <span>영상 썸네일 없음</span>
              )}
              <span className="video-play" aria-hidden="true">▶</span>
            </a>
            <div className="video-card-body">
              <span className="video-topic-label">{video.search_query ?? "입시"}</span>
              <h2>
                <a href={video.source_url} target="_blank" rel="noreferrer">
                  {video.title}
                </a>
              </h2>
              <p className="video-channel">{video.channel_title ?? "채널 정보 없음"}</p>
              <div className="video-meta">
                <span>{formatDate(video.published_at)}</span>
                <span>조회 {formatCount(video.view_count)}</span>
                <span>좋아요 {formatCount(video.like_count)}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
