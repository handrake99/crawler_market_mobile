#!/bin/bash

# ==============================================================================
# App Market Analyzer - Daily Cronjob Setup
# ==============================================================================
# 이 스크립트는 App Market Analyzer AI Agent를 매일 오전 7시에 실행하도록
# crontab에 등록하는 가이드 및 헬퍼 스크립트입니다.

PROJECT_DIR="$HOME/work/crawler_market_mobile/app_market_agent"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
MAIN_SCRIPT="$PROJECT_DIR/main.py"
CRON_LOG="$PROJECT_DIR/cron.log"

# 크론탭 명령어 형태 (매일 오전 7시)
CRON_CMD="0 7 * * * cd $PROJECT_DIR && $VENV_PYTHON $MAIN_SCRIPT >> $CRON_LOG 2>&1"

echo "=========================================================="
echo "앱 마켓 분석 Agent 스케줄러(Cron) 설정 가이드"
echo "=========================================================="
echo ""
echo "터미널에서 'crontab -e'를 입력하여 크론 에디터를 열고,"
echo "아래의 줄을 복사하여 붙여넣으세요:"
echo ""
echo "$CRON_CMD"
echo ""
echo "저장하고 나가면 매일 오전 7시에 에이전트가 자동 실행되며,"
echo "실행 로그는 $CRON_LOG 파일에 저장됩니다."
echo "=========================================================="
