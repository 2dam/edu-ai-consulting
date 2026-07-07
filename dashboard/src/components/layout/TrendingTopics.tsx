import { useEffect, useState } from "react";
import { getTrendingKeywords } from "../../api/community";
import "./TrendingTopics.css";

export function TrendingTopics() {
  const [keywords, setKeywords] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTrendingKeywords()
      .then(setKeywords)
      .catch(() => setKeywords([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (keywords.length === 0) return null;

  return (
    <section className="trending-topics">
      <h3>🔥 요즘 화제 키워드</h3>
      <ul>
        {keywords.map((k, i) => (
          <li key={k}>
            <span className="trending-rank">{i + 1}</span>
            {k}
          </li>
        ))}
      </ul>
    </section>
  );
}
