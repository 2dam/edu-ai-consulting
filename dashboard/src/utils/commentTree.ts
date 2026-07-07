import type { CommentOut } from "../api/types";

/** 새 댓글/답글을 트리 상태에 불변적으로 삽입한다 (재조회 없이 화면에 바로 반영). */
export function insertComment(tree: CommentOut[], newComment: CommentOut): CommentOut[] {
  if (newComment.parent_id === null) {
    return [...tree, newComment];
  }

  function insertInto(nodes: CommentOut[]): CommentOut[] {
    return nodes.map((node) => {
      if (node.id === newComment.parent_id) {
        return { ...node, replies: [...node.replies, newComment] };
      }
      if (node.replies.length > 0) {
        return { ...node, replies: insertInto(node.replies) };
      }
      return node;
    });
  }

  return insertInto(tree);
}

export function countComments(tree: CommentOut[]): number {
  return tree.reduce((sum, node) => sum + 1 + countComments(node.replies), 0);
}
