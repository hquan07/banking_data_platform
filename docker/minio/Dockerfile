# Development-only MinIO Community build from pinned upstream source commits.
# MinIO Community is archived; do not use this image for production banking data.
FROM golang:1.24.8-alpine AS build

ENV CGO_ENABLED=0 GOBIN=/out
ARG MINIO_VERSION=v0.0.0-20251015172955-9e49d5e7a648
ARG MC_VERSION=v0.0.0-20250813083541-7394ce0dd2a8

RUN go install github.com/minio/minio@${MINIO_VERSION} \
    && go install github.com/minio/mc@${MC_VERSION}
RUN mkdir -p /out/licenses \
    && cp "/go/pkg/mod/github.com/minio/minio@${MINIO_VERSION}/LICENSE" /out/licenses/minio-LICENSE \
    && cp "/go/pkg/mod/github.com/minio/mc@${MC_VERSION}/LICENSE" /out/licenses/mc-LICENSE

FROM alpine:3.22
RUN apk add --no-cache ca-certificates curl
COPY --from=build /out/minio /usr/local/bin/minio
COPY --from=build /out/mc /usr/local/bin/mc
COPY --from=build /out/licenses/ /licenses/

EXPOSE 9000 9001
VOLUME /data
ENTRYPOINT ["minio"]
