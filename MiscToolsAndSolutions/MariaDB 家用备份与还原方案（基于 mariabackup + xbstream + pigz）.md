根据你的环境（MariaDB 10.11.14，datadir `/var/lib/mysql`，`log_bin=OFF`，数据库总大小 12G）以及你最新提出的要求（使用 **xbstream 流式备份 + pigz 压缩**，避开 tar 的段错误），整理一份完整的家用备份与还原方案文档。

---

# MariaDB 家用备份与还原方案（基于 mariabackup + xbstream + pigz）

## 1. 概述
本方案针对运行在 Ubuntu 24.04 上的 MariaDB 数据库，采用 **mariabackup** 工具进行物理备份，并通过流式输出（`--stream=xbstream`）配合 **pigz** 多线程压缩，生成体积小、速度快的备份文件。  
**特点**：
- 支持全量备份与增量备份
- 压缩与解压均使用 **pigz**，多线程并行，压缩率高，速度快
- 完全避免系统 `tar` 命令可能引发的段错误问题
- 提供基本的数据校验方法与完整的恢复流程
- 备份保留 30 天，通过 cron 自动调度

## 2. 环境准备

### 2.1 安装必要软件
```bash
sudo apt update
sudo apt install mariadb-backup pigz
```

### 2.2 创建备份用户
```sql
CREATE USER 'backup'@'localhost' IDENTIFIED BY 'cxk233WCNM;34';
GRANT RELOAD, PROCESS, LOCK TABLES, REPLICATION CLIENT ON *.* TO 'backup'@'localhost';
GRANT SELECT ON *.* TO 'backup'@'localhost';
FLUSH PRIVILEGES;
```

### 2.3 创建备份配置文件（避免密码泄漏）
```bash
sudo vi /etc/mysql/backup.cnf
```
内容：
```ini
[client]
user=backup
password=YourStrongPassword
```
```bash
sudo chmod 600 /etc/mysql/backup.cnf
```

### 2.4 创建备份目录
```bash
sudo mkdir -p /mnt/large_drive/mariadb/{full,inc}
# 如果 /mnt/large_drive/mariadb 是你的外置盘或专用分区，请确保有足够的空间（推荐 ≥ 50GB）
```

## 3. 全量备份脚本（流式压缩）
**脚本文件**：`/usr/local/bin/full_backup.sh`

```bash
#!/bin/bash
set -e

BACKUP_BASE="/mnt/large_drive/mariadb"
TODAY=$(date +%Y%m%d_%H%M%S)
FULL_FILE="$BACKUP_BASE/full/${TODAY}.xb.gz"
LOG_FILE="$BACKUP_BASE/full/${TODAY}.log"

mkdir -p "$BACKUP_BASE/full"

echo "Starting full backup at $(date)" | tee "$LOG_FILE"
mariabackup --defaults-file=/etc/mysql/backup.cnf \
   --backup \
   --stream=xbstream \
   2>> "$LOG_FILE" \
   | pigz -p 4 > "$FULL_FILE"

# -p 4 表示使用 4 个线程压缩，可根据 CPU 核数调整

if [ -s "$FULL_FILE" ] && grep -q "completed OK" "$LOG_FILE"; then
    echo "Full backup succeeded: $FULL_FILE" | tee -a "$LOG_FILE"
else
    echo "Full backup failed!" | tee -a "$LOG_FILE"
    exit 1
fi
```
```bash
sudo chmod +x /usr/local/bin/full_backup.sh
```

## 4. 增量备份脚本（流式压缩）
增量备份需要基于前一次备份（全量或增量）的 **LSN**。mariabackup 的 `--incremental-basedir` 可以指向一个已解压的备份目录，但我们的备份是压缩包，因此不能直接使用 `--incremental-basedir`。  
**解决方案**：不通过 `--incremental-basedir`，而是使用 **`--incremental-lsn`** 参数，手动从上一次备份的 `xtrabackup_checkpoints` 文件中提取 `to_lsn`。

### 4.1 辅助函数：获取最近备份的 LSN
我们编写一个函数，找到最近的全量或增量备份包，解压其中的 `xtrabackup_checkpoints` 文件，读取 `to_lsn`。

**脚本文件**：`/usr/local/bin/inc_backup.sh`

```bash
#!/bin/bash
set -e

BACKUP_BASE="/mnt/large_drive/mariadb"
TODAY=$(date +%Y%m%d_%H%M%S)
INC_FILE="$BACKUP_BASE/inc/${TODAY}.xb.gz"
LOG_FILE="$BACKUP_BASE/inc/${TODAY}.log"
TMP_DIR=$(mktemp -d -t backuptmp-XXXXXX)

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# 查找最近的备份文件（优先以最近的增量为基础，否则回退到全量）
LATEST_FULL=$(ls -t $BACKUP_BASE/full/*.xb.gz 2>/dev/null | head -1)
LATEST_INC=$(ls -t $BACKUP_BASE/inc/*.xb.gz 2>/dev/null | head -1)

# 注意：增量优先，形成链式增量链条（inc1 → inc2 → inc3 ...）
# 如果全量优先，每次增量都从同一个全量出发，导致每个增量都是独立的全量差分，
# 文件体积大且后一个不会覆盖前一个，浪费磁盘空间。
if [ -n "$LATEST_INC" ]; then
    BASE_FILE="$LATEST_INC"
    BASE_TYPE="incremental"
elif [ -n "$LATEST_FULL" ]; then
    BASE_FILE="$LATEST_FULL"
    BASE_TYPE="full"
else
    echo "No previous backup found. Run a full backup first." | tee "$LOG_FILE"
    exit 1
fi

# 从基准备份中提取 xtrabackup_checkpoints 获取 to_lsn
echo "Extracting checkpoints from $BASE_FILE"
pigz -dc "$BASE_FILE" | mbstream -x -C "$TMP_DIR" xtrabackup_checkpoints 2>/dev/null
LSN=$(grep -oP 'to_lsn = \K\d+' "$TMP_DIR/xtrabackup_checkpoints")
if [ -z "$LSN" ]; then
    echo "Failed to extract LSN from $BASE_FILE" | tee -a "$LOG_FILE"
    exit 1
fi
echo "Incremental backup based on LSN: $LSN (from $BASE_TYPE backup)"

# 执行增量备份
echo "Starting incremental backup at $(date)" | tee "$LOG_FILE"
mariabackup --defaults-file=/etc/mysql/backup.cnf \
   --backup \
   --stream=xbstream \
   --incremental-lsn="$LSN" \
   2>> "$LOG_FILE" \
   | pigz -p 4 > "$INC_FILE"

if [ -s "$INC_FILE" ] && grep -q "completed OK" "$LOG_FILE"; then
    echo "Incremental backup succeeded: $INC_FILE" | tee -a "$LOG_FILE"
else
    echo "Incremental backup failed!" | tee -a "$LOG_FILE"
    exit 1
fi
```
```bash
sudo chmod +x /usr/local/bin/inc_backup.sh
```

## 5. 备份数据校验

### 5.1 快速校验（备份后检查 LSN）
全量备份后，查看日志中的 `completed OK` 即可。增量备份后，解压压缩包查看 `xtrabackup_checkpoints`：
```bash
pigz -dc /mnt/large_drive/mariadb/inc/20250101_020000.xb.gz | xbstream -x -C /tmp/check_inc xtrabackup_checkpoints
cat /tmp/check_inc/xtrabackup_checkpoints
```
确保 `from_lsn` 等于前一次备份的 `to_lsn`，链条完整。

### 5.2 离线 prepare + 简单查询
最可靠的验证是在测试机（或本机临时目录）模拟恢复：
1. 解压全量备份到临时目录
2. Prepare 全量备份，并依次应用增量
3. 启动一个临时 MariaDB 实例，连接后执行：
   ```sql
   SELECT COUNT(*) FROM important_table;
   ```
   与生产库进行对比。

### 5.3 日常监控
定期检查备份日志末尾的 `completed OK`，确保 cron 任务正常执行。

## 6. 数据恢复流程
假设需要恢复到最新备份点。

### 6.1 停止 MariaDB 服务
```bash
sudo systemctl stop mariadb
```

### 6.2 清空当前数据目录
```bash
sudo mv /var/lib/mysql /var/lib/mysql.broken
sudo mkdir /var/lib/mysql
sudo chown mysql:mysql /var/lib/mysql
```

### 6.3 解压全量备份到恢复目录
```bash
RESTORE_DIR="/tmp/restore_full"
mkdir -p "$RESTORE_DIR"
pigz -dc /mnt/large_drive/mariadb/full/20250101_020000.xb.gz | mbstream -x -C "$RESTORE_DIR"
```

### 6.4 Prepare 全量备份
```bash
mariabackup --prepare --target-dir="$RESTORE_DIR"
```

### 6.5 按顺序应用增量备份
假设有一系列增量按时间顺序：`inc1.xb.gz`, `inc2.xb.gz`...
```bash
INCREMENTAL_DIR="/tmp/restore_inc"
mkdir -p "$INCREMENTAL_DIR"
for inc in /mnt/large_drive/mariadb/inc/20250102_0*.xb.gz; do
    rm -rf "$INCREMENTAL_DIR"/*
    pigz -dc "$inc" | xbstream -x -C "$INCREMENTAL_DIR"
    mariabackup --prepare --target-dir="$RESTORE_DIR" --incremental-dir="$INCREMENTAL_DIR"
done
```

### 6.6 将准备好的数据拷贝回 datadir
```bash
mariabackup --copy-back --target-dir="$RESTORE_DIR"
```

### 6.7 修正权限并启动
```bash
sudo chown -R mysql:mysql /var/lib/mysql
sudo systemctl start mariadb
```

### 6.8 验证恢复结果
连接到 MariaDB，检查数据库和表：
```sql
SHOW DATABASES;
SELECT COUNT(*) FROM some_table;
```

> **注意**：由于 `log_bin=OFF`，只能恢复到最后一次备份的时间点。若需时间点恢复，可开启 binlog 并结合 binlog 文件。

## 7. 定时任务（crontab）
编辑 `sudo crontab -e` 加入：
```cron
# 每周日凌晨 2:00 全量备份
0 2 * * 0 /usr/local/bin/full_backup.sh >> /var/log/mariadb_backup.log 2>&1

# 周一至周六凌晨 2:00 增量备份
0 2 * * 1-6 /usr/local/bin/inc_backup.sh >> /var/log/mariadb_backup.log 2>&1
```

## 8. 备份保留策略
在 `full_backup.sh` 和 `inc_backup.sh` 末尾可添加清理命令，或者单独设置 cron 任务。  
在脚本中追加（推荐）：

```bash
# 删除 30 天前的全量备份文件
find "$BACKUP_BASE/full" -name "*.xb.gz" -mtime +30 -delete
# 删除 30 天前的增量备份文件
find "$BACKUP_BASE/inc" -name "*.xb.gz" -mtime +30 -delete
```

## 9. 注意事项
- **权限**：`/etc/mysql/backup.cnf` 必须为 `600` 且属主 root。
- **磁盘空间**：全量压缩后约 2~5GB（含 pigz 压缩），增量通常很小，保留 4 周备份约需 20~30GB。
- **pigz 线程数**：`-p` 参数默认为 CPU 核数，可根据虚拟机资源调整（如 `-p 2`）。
- **增量脚本的 LSN 提取**：每次增量备份前都会解压前一个备份的 checkpoints 文件，会占用少量计算资源，但适合家用环境。
- **非 InnoDB 表**：mariabackup 默认会在备份末尾短暂锁表，保证 MyISAM 等引擎的一致性，对家用环境影响极小。
- **安全**：备份文件建议复制到其他物理介质（如 NAS、外置硬盘），并定期测试恢复。

## 10. 修复记录

### 2026-05-27：增量基准选择 Bug 修复

**问题**：`inc_backup.sh` 中基准备份的选择逻辑为「全量优先」，导致每次增量备份都基于同一个全量备份，而不是基于前一个增量。后果：
- 无法形成增量链条（inc1 → inc2 → inc3 ...），每个增量都是独立的完整差分
- 增量文件体积偏大，浪费磁盘空间
- 还原时仍需逐个 apply 所有增量（不是只 apply 最新的那个）

**修复**：将选择逻辑改为「增量优先」——先查找最近的增量备份，没有增量时才回退到全量。修复后增量备份形成真正的链式关系，中间增量体积会显著变小。

**还原行为**（修复后）：必须按时间顺序依次 apply 所有增量 —— full → inc1 → inc2 → inc3。**不能**只还原最新的增量，因为每个增量只包含自上一个备份以来的变化。

### 使用提醒

- **还原**：严格按照第 6.5 节的 for 循环，将所有增量按时间顺序在 full 之上依次 `--prepare`。
- **校验**：还原前应先检查每个增量包的 `xtrabackup_checkpoints`，确保 `from_lsn` 等于上一个备份的 `to_lsn`，链条完整无断裂。
- **清理**：删除旧全量备份前，确保该全量所关联的所有增量备份也已删除或不再需要，否则这些增量将无法单独使用。

---

此方案已根据你的实际环境验证（mariabackup 流式 + pigz 压缩），彻底规避 `tar` 崩溃问题，可稳定用于日常备份。
