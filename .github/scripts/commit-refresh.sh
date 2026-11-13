#!/usr/bin/env bash
# Commit the refreshed generated/public-source files and push them to BRANCH.
#
# Usage: commit-refresh.sh BRANCH
#
# Generated files are rebuilt in full on every run, so two overlapping runs
# (e.g. a manual run and the schedule) always conflict on them. When a plain
# rebase onto the latest branch fails, this script aborts it, resets to the
# latest branch tip and re-applies only this run's generated paths on top, so
# the newest build wins without touching any other file pushed meanwhile.
set -euo pipefail

BRANCH="${1:?usage: commit-refresh.sh BRANCH}"

PATHS=(
  data/processed
  data/raw/power/neso_carbon_intensity_api_raw.json
  data/raw/power/neso_fetch_metadata.json
  data/raw/power/neso_generation_mix_live.csv
  data/raw/carbon/eua_auction_results.csv
  data/raw/carbon/uk_ets_ccm_monthly_prices.csv
  data/raw/carbon/ecb_eurgbp_monthly.csv
  data/raw/fmd
  data/source_register.csv
  outputs/analyst_note.md
)
if [ -f data/raw/carbon/trading_economics_eu_carbon_reference.csv ]; then
  PATHS+=(data/raw/carbon/trading_economics_eu_carbon_reference.csv)
fi
MESSAGE="Refresh generated dashboard data"

git add -- "${PATHS[@]}"
if git diff --cached --quiet; then
  echo "No generated data changes to commit."
  exit 0
fi
echo "Committing refreshed generated/public-source files:"
git diff --cached --name-only
git commit -q -m "$MESSAGE"
BUILD_COMMIT="$(git rev-parse HEAD)"

for attempt in 1 2 3; do
  git fetch -q origin "$BRANCH"
  if git rebase -q "origin/$BRANCH"; then
    :
  else
    echo "Rebase conflicted on generated files; re-applying this run's outputs on top of origin/$BRANCH."
    git rebase --abort
    git reset -q --hard "origin/$BRANCH"
    git checkout "$BUILD_COMMIT" -- "${PATHS[@]}"
    if git diff --cached --quiet; then
      echo "Latest $BRANCH already has identical generated data."
      exit 0
    fi
    git commit -q -m "$MESSAGE"
  fi
  if git push -q origin "HEAD:$BRANCH"; then
    echo "Pushed refreshed data to $BRANCH."
    exit 0
  fi
  echo "Push attempt ${attempt} failed; retrying."
  sleep $((attempt * 10))
done
exit 1
