# Also builds as a bare static binary for estates that will not run containers:
#   CGO_ENABLED=0 go build -ldflags="-s -w" -o edge-shipper .
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/edge-shipper .

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/edge-shipper /edge-shipper
ENTRYPOINT ["/edge-shipper"]
