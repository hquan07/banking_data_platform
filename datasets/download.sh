#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
raw_dir="${script_dir}/raw"

usage() {
  echo "Usage: $0 {ds1|ds2|ds3|ds4|all}" >&2
  exit 2
}

require_tools() {
  command -v kaggle >/dev/null || {
    echo "Kaggle CLI is required. Install/configure it and retry." >&2
    exit 1
  }
  command -v unzip >/dev/null || {
    echo "unzip is required." >&2
    exit 1
  }
}

download_ds1() {
  mkdir -p "${raw_dir}/creditcard"
  kaggle datasets download -d mlg-ulb/creditcardfraud \
    -f creditcard.csv -p "${raw_dir}/creditcard" --unzip
}

download_ds2() {
  mkdir -p "${raw_dir}/ieee-cis"
  for file in train_transaction.csv train_identity.csv; do
    kaggle competitions download -c ieee-fraud-detection \
      -f "${file}" -p "${raw_dir}/ieee-cis"
    unzip -o "${raw_dir}/ieee-cis/${file}.zip" -d "${raw_dir}/ieee-cis"
    rm "${raw_dir}/ieee-cis/${file}.zip"
  done
}

download_ds3() {
  mkdir -p "${raw_dir}/paysim"
  kaggle datasets download -d ealaxi/paysim1 \
    -p "${raw_dir}/paysim" --unzip
}

download_ds4() {
  mkdir -p "${raw_dir}/bank-account-fraud"
  kaggle datasets download \
    -d feedzai/bank-account-fraud-dataset-neurips-2022 \
    -f Base.csv -p "${raw_dir}/bank-account-fraud" --unzip
}

require_tools
case "${1:-}" in
  ds1) download_ds1 ;;
  ds2) download_ds2 ;;
  ds3) download_ds3 ;;
  ds4) download_ds4 ;;
  all)
    download_ds1
    download_ds2
    download_ds3
    download_ds4
    ;;
  *) usage ;;
esac
