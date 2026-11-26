FROM golang:1.26-alpine AS build
WORKDIR /src
# Test fixtures from weaviate/weaviate v1.41.0
ARG CORE_REV=4026ba9c88ff36c9b3595dc79b18f07a372314a7
RUN go mod init test-issuer && go get github.com/weaviate/mockoidc@v0.0.2
ADD https://raw.githubusercontent.com/weaviate/weaviate/${CORE_REV}/test/docker/mockoidc/mockoidc.go ./issuer.go
RUN go build -o /issuer issuer.go
ADD https://raw.githubusercontent.com/weaviate/weaviate/${CORE_REV}/test/docker/mockoidchelper/mockoidc_helper.go ./helper.go
RUN go build -o /helper helper.go

FROM alpine:3.23
COPY --from=build /issuer /helper /bin/
CMD ["/bin/issuer"]
