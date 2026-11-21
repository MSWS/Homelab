# Build carbonate from a pinned, audited commit.
FROM golang:1.26-alpine AS build
ARG COMMIT=3c768a26040a939faeead71bb2b305737b8b045f
RUN apk add --no-cache git ca-certificates tzdata
WORKDIR /src
RUN git clone --quiet https://github.com/develonrails/carbonate.git . \
 && git checkout --quiet "$COMMIT" \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/carbonate ./cmd/carbonate

FROM alpine:3.21
RUN adduser -D -H -u 10001 carbonate
COPY --from=build /out/carbonate /usr/local/bin/carbonate
USER carbonate
ENV HOME=/home/carbonate CARBONATE_NO_INVITATIONS=1
VOLUME /state
VOLUME /home/carbonate
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/carbonate"]
CMD ["serve", "-addr", "0.0.0.0:8080", "-session", "/home/carbonate/.config/carbonate/auth.json", "-watch", "5m"]
