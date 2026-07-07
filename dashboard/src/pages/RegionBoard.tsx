import { useParams } from "react-router-dom";
import { BoardFeed } from "../components/post/BoardFeed";

export function RegionBoard() {
  const { region } = useParams<{ region: string }>();
  if (!region) return null;

  return (
    <BoardFeed
      title={`${region} 지역 게시판`}
      boardSlug={`region-${region}`}
      kind="region"
      regionSlug={region}
    />
  );
}
