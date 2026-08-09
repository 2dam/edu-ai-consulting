# Buzz 릴레이 (buzz.ichapterwise.com) — Render 배포용 Dockerfile
# ghcr.io/block/buzz:main 이미지를 그대로 쓰되, Render 환경변수 주입을 위해
# 최소 래퍼. (이미지가 이미 relay 바이너리 포함 가정)
FROM ghcr.io/block/buzz:main

# Render가 주입하는 환경변수를 그대로 사용 (PORT, BUZZ_* 등).
# 런타임 인수가 필요하면 아래에 명시. 기본값은 이미지 내부 기본.
EXPOSE 3000
# 기본 명령은 이미지 ENTRYPOINT 가 담당. 필요 시 오버라이드:
# CMD ["buzz-relay"]
