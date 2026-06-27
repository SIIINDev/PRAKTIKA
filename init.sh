#!/usr/bin/env bash
#
# init.sh — seed the knowledge base with a set of openly-licensed PDFs.
#
# Downloads each PDF below into a temporary directory and uploads it to the
# running backend via POST /api/v1/documents/upload (multipart field: file).
# Downloaded files are NOT committed; the temp dir is removed on exit.
#
# Usage:
#   ./init.sh                 # uses default API URL below
#   API_URL=http://host:8000 ./init.sh
#
set -uo pipefail

API_URL="${API_URL:-http://localhost:8000}"
UPLOAD_ENDPOINT="${API_URL}/api/v1/documents/upload"

# ── Edit this list freely. Each entry: "<url> <output-filename.pdf>" ──────────
PDFS=(
  "https://arxiv.org/pdf/1706.03762 attention-is-all-you-need.pdf"
  "https://arxiv.org/pdf/1810.04805 bert.pdf"
  "https://arxiv.org/pdf/1409.0473 neural-machine-translation.pdf"
  "https://arxiv.org/pdf/1512.03385 deep-residual-learning.pdf"
  "https://arxiv.org/pdf/1412.6980 adam-optimizer.pdf"
  "https://arxiv.org/pdf/1301.3781 word2vec.pdf"
  "https://arxiv.org/pdf/1406.2661 generative-adversarial-nets.pdf"
  "https://arxiv.org/pdf/1503.02531 distilling-knowledge.pdf"
  "https://arxiv.org/pdf/2005.14165 gpt3-few-shot.pdf"
  "https://arxiv.org/pdf/1810.00826 graph-isomorphism-networks.pdf"
)
# ─────────────────────────────────────────────────────────────────────────────

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "==> Seeding knowledge base"
echo "    API endpoint : ${UPLOAD_ENDPOINT}"
echo "    Temp dir     : ${TMP_DIR}"
echo

ok=0
fail=0

for entry in "${PDFS[@]}"; do
  url="${entry%% *}"
  name="${entry##* }"
  dest="${TMP_DIR}/${name}"

  echo "--> ${name}"
  echo "    download: ${url}"
  if ! curl -fsSL --retry 2 --max-time 120 -o "$dest" "$url"; then
    echo "    [WARN] download failed — skipping" >&2
    fail=$((fail + 1))
    continue
  fi

  if [ ! -s "$dest" ]; then
    echo "    [WARN] downloaded file is empty — skipping" >&2
    fail=$((fail + 1))
    continue
  fi

  echo "    upload  : POST ${UPLOAD_ENDPOINT}"
  if curl -fsS --max-time 120 -X POST -F "file=@${dest};type=application/pdf" "$UPLOAD_ENDPOINT" >/dev/null; then
    echo "    [OK] uploaded"
    ok=$((ok + 1))
  else
    echo "    [WARN] upload failed — skipping" >&2
    fail=$((fail + 1))
  fi
  echo
done

echo "==> Done. uploaded=${ok} skipped=${fail} total=${#PDFS[@]}"
[ "$ok" -gt 0 ]
