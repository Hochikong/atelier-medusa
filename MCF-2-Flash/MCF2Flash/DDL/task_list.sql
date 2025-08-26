-- collector_rest.tasks_list definition

DROP TABLE collector_rest.tasks_list_v2;

CREATE TABLE collector_rest.tasks_list_v2
(
    `id`             int(11)  NOT NULL AUTO_INCREMENT PRIMARY KEY ,
    `created_at`     datetime NOT NULL,
    `updated_at`     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '数据更新时间，由触发器更新',
    `deleted_at`     datetime     DEFAULT NULL,
    `task_uid`       varchar(100) DEFAULT NULL,
    `task_content`   varchar(200) DEFAULT NULL,
    `task_status`    int          DEFAULT NULL,
    `driver_info`    varchar(50)  DEFAULT NULL,
    `download_dir`   varchar(100) DEFAULT NULL,
    `extra_content`  text
)    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci
    COMMENT 'MCFv2批量模式-任务表';

CREATE INDEX idx_task_content ON collector_rest.tasks_list_v2(task_content);
CREATE INDEX idx_task_status ON collector_rest.tasks_list_v2(task_status);
CREATE INDEX idx_task_uid ON collector_rest.tasks_list_v2(task_uid);