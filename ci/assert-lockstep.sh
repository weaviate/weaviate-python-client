#!/usr/bin/env bash
# Fails unless the weaviate-client and weaviate-client-web wheels in <dist-dir> (default:
# dist) carry the same version; the two packages are released in lockstep.
set -euo pipefail
dist="${1:-dist}"
base=$(basename "$dist"/weaviate_client-*.whl); base=${base#weaviate_client-}; base=${base%%-*}
web=$(basename "$dist"/weaviate_client_web-*.whl); web=${web#weaviate_client_web-}; web=${web%%-*}
echo "weaviate-client=$base weaviate-client-web=$web"
if [ "$base" != "$web" ]; then
  echo "version mismatch: weaviate-client $base != weaviate-client-web $web (must release in lockstep)" >&2
  exit 1
fi
