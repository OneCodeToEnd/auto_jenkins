#!/bin/bash
# jenkins 构建脚本

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

  # 参数检查
if [ $# -lt 1 ]; then
      log "缺少参数"
      log "用法: jbuild <任务名> [分支名]"
      exit 1
fi



 # 获取脚本真实路径（处理符号链接）
SOURCE="${BASH_SOURCE[0]}"

log "获取脚本真实路径: ${SOURCE}"

  # 如果是符号链接，解析到真实路径
while [ -h "$SOURCE" ]; do
    SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    log "寻找脚本目录: ${SCRIPT_DIR}, 源目录:${SOURCE}"
    # 如果 SOURCE 是相对路径，需要基于 SCRIPT_DIR 解析
    [[ $SOURCE != /* ]] && SOURCE="$SCRIPT_DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

log "目标脚本目录:${SCRIPT_DIR}"

 # 切换到脚本目录
cd "$SCRIPT_DIR"

# 执行 Python 脚本，传递所有参数
python3 quick_build.py "$@"
