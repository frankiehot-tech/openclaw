#!/bin/bash
# Cleanup OpenClaw: archive monitoring reports + trim backup files
# Usage:
#   bash ops/deploy/cleanup.sh             # dry-run (default)
#   bash ops/deploy/cleanup.sh --execute   # actually do it
set -euo pipefail

ROOT="/Volumes/1TB-M2/openclaw"
DRY_RUN=true
if [ "${1:-}" = "--execute" ]; then
    DRY_RUN=false
fi

echo "=== OpenClaw Cleanup ==="
echo "Mode: $($DRY_RUN && echo 'DRY RUN' || echo 'EXECUTE')"
echo

# ============================================================
# 1. Archive queue_progress_monitoring_*.md
#    Keep latest 3 in root, move rest to .document_recycle_bin/
# ============================================================
echo "--- Queue Monitoring Reports ---"
ARCHIVE_DIR="$ROOT/.document_recycle_bin"
mkdir -p "$ARCHIVE_DIR"

# Find all monitoring reports (in root, not in .document_recycle_bin/)
reports=()
while IFS= read -r f; do
    reports+=("$f")
done < <(find "$ROOT" -maxdepth 1 -name 'queue_progress_monitoring_*.md' -type f | sort)

count=${#reports[@]}
echo "Found $count monitoring reports in root"

if [ "$count" -gt 3 ]; then
    keep=("${reports[@]: -3}")
    for report in "${reports[@]}"; do
        skip=false
        for k in "${keep[@]}"; do
            [ "$report" = "$k" ] && skip=true && break
        done
        if ! $skip; then
            echo "  -> archive: $(basename "$report")"
            $DRY_RUN || mv "$report" "$ARCHIVE_DIR/$(basename "$report")"
        fi
    done
    echo "Kept 3 latest, archived $((count - 3)) reports"
fi

# ============================================================
# 2. Cleanup *.backup* files
#    Per directory: keep latest 3 backups, archive rest
# ============================================================
echo
echo "--- Backup Files ---"

# Find directories containing .backup files
while IFS= read -r dir; do
    files=()
    while IFS= read -r f; do
        files+=("$f")
    done < <(find "$dir" -maxdepth 1 -name '*.backup*' -type f | sort -t. -k4 -r 2>/dev/null || true)

    count=${#files[@]}
    [ "$count" -eq 0 ] && continue

    echo "Directory: $dir ($count backup(s))"

    if [ "$count" -gt 3 ]; then
        # Keep 3 most recent by modification time
        keep=()
        while IFS= read -r f; do
            keep+=("$f")
        done < <(ls -t "${files[@]}" 2>/dev/null | head -3)

        for bf in "${files[@]}"; do
            skip=false
            for k in "${keep[@]}"; do
                [ "$bf" = "$k" ] && skip=true && break
            done
            if ! $skip; then
                echo "  -> archive: $(basename "$bf")"
                $DRY_RUN || mv "$bf" "$ARCHIVE_DIR/$(basename "$bf").bak"
            fi
        done
        echo "  Kept 3 latest, archived $((count - 3)) backups"
    fi
done < <(find "$ROOT" -type d -not -path '*/node_modules/*' -not -path '*/.venv*/*' -not -path '*/venv*/*' -not -path '*/.git/*' -not -path '*/comfyui_workspace/*' -not -path '*/docs/vendor/*' 2>/dev/null)

# ============================================================
# 3. Cleanup queue analysis reports in logs/ (keep latest 5)
# ============================================================
echo
echo "--- Queue Analysis Reports ---"
reports=()
while IFS= read -r f; do
    reports+=("$f")
done < <(find "$ROOT/logs" -maxdepth 1 -name 'queue_analysis_report_*.md' -type f | sort)
count=${#reports[@]}
echo "Found $count queue analysis reports in logs/"
if [ "$count" -gt 5 ]; then
    keep=("${reports[@]: -5}")
    for report in "${reports[@]}"; do
        skip=false
        for k in "${keep[@]}"; do
            [ "$report" = "$k" ] && skip=true && break
        done
        if ! $skip; then
            echo "  -> archive: $(basename "$report")"
            $DRY_RUN || mv "$report" "$ARCHIVE_DIR/$(basename "$report")"
        fi
    done
    echo "Kept 5 latest, archived $((count - 5)) reports"
fi

# ============================================================
# 4. Cleanup old error classification reports in scripts/ (keep latest 3)
# ============================================================
echo
echo "--- Error Classification Reports ---"
report_dir="$ROOT/scripts"
json_reports=()
while IFS= read -r f; do
    json_reports+=("$f")
done < <(find "$report_dir" -maxdepth 1 -name 'error_classification_*.json' -type f | sort)
txt_reports=()
while IFS= read -r f; do
    txt_reports+=("$f")
done < <(find "$report_dir" -maxdepth 1 -name 'error_classification_*.txt' -type f | sort)
echo "Found ${#json_reports[@]} json + ${#txt_reports[@]} txt reports in scripts/"
for ext in "json" "txt"; do
    var_name="${ext}_reports[@]"
    items=("${!var_name}")
    count=${#items[@]}
    if [ "$count" -gt 3 ]; then
        keep=("${items[@]: -3}")
        for report in "${items[@]}"; do
            skip=false
            for k in "${keep[@]}"; do
                [ "$report" = "$k" ] && skip=true && break
            done
            if ! $skip; then
                echo "  -> archive: $(basename "$report")"
                $DRY_RUN || mv "$report" "$ARCHIVE_DIR/$(basename "$report")"
            fi
        done
        echo "  Kept 3 latest $ext, archived $((count - 3))"
    fi
done

echo
echo "=== Cleanup complete ($($DRY_RUN && echo 'DRY RUN — use --execute to apply') ) ==="
