-- =============================================================================
-- 宿舍报修管理系统 —— 数据库建表脚本（MySQL 8.0+，字符集 utf8mb4）
--
-- 使用方式（任选其一）：
--   1) 推荐：在项目根目录执行  python init_db.py
--      （自动建库、建表并写入演示数据，无需手动操作）
--   2) 手动：在 MySQL Workbench 或命令行中直接执行本文件
--
-- 表结构说明：
--   sys_user         用户表（学生 / 维修人员 / 管理员）
--   fault_category   故障类别字典表
--   repair_order     报修工单主表（外键关联用户表与类别表）
--   order_image      工单图片表（外键关联工单表，一对多）
--   order_log        工单流转日志表（记录接单、维修备注、完成、评价等轨迹）
--   repair_review    维修评价表（外键关联工单表，一个工单最多一条评价）
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `dorm_repair`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_general_ci;

USE `dorm_repair`;

-- -----------------------------------------------------------------------------
-- 1. 用户表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sys_user` (
    `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户主键',
    `username`      VARCHAR(50)  NOT NULL                COMMENT '登录账号（唯一）',
    `password_hash` VARCHAR(255) NOT NULL                COMMENT '密码哈希（PBKDF2 加盐，不保存明文）',
    `role`          ENUM('student','worker','admin') NOT NULL DEFAULT 'student' COMMENT '角色：学生 / 维修人员 / 管理员',
    `real_name`     VARCHAR(50)  NOT NULL                COMMENT '真实姓名',
    `phone`         VARCHAR(20)  DEFAULT NULL            COMMENT '联系电话',
    `student_no`    VARCHAR(30)  DEFAULT NULL            COMMENT '学号（学生专用）',
    `dorm_no`       VARCHAR(30)  DEFAULT NULL            COMMENT '宿舍号（学生专用）',
    `worker_no`     VARCHAR(30)  DEFAULT NULL            COMMENT '工号（维修人员专用）',
    `skill`         VARCHAR(50)  DEFAULT NULL            COMMENT '工种（维修人员专用）',
    `is_active`     TINYINT(1)   NOT NULL DEFAULT 1      COMMENT '是否启用：1 启用，0 禁用',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '账号创建时间',
    `last_login_at` DATETIME     DEFAULT NULL            COMMENT '最后登录时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_username` (`username`),
    UNIQUE KEY `uk_user_student_no` (`student_no`),
    UNIQUE KEY `uk_user_worker_no` (`worker_no`),
    KEY `idx_user_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表：学生 / 维修人员 / 管理员';

-- -----------------------------------------------------------------------------
-- 2. 故障类别表
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `fault_category` (
    `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '类别主键',
    `name`       VARCHAR(50)  NOT NULL                COMMENT '故障类别名称',
    `sort_order` INT          NOT NULL DEFAULT 0      COMMENT '显示排序号',
    `is_active`  TINYINT(1)   NOT NULL DEFAULT 1      COMMENT '是否启用',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_category_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='故障类别字典表';

-- -----------------------------------------------------------------------------
-- 3. 报修工单表（核心业务表）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `repair_order` (
    `id`           INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '工单主键',
    `order_no`     VARCHAR(32)  NOT NULL                COMMENT '工单号（业务唯一编号）',
    `student_id`   INT UNSIGNED NOT NULL                COMMENT '报修学生，外键 -> sys_user.id',
    `worker_id`    INT UNSIGNED DEFAULT NULL            COMMENT '接单维修人员，外键 -> sys_user.id（未接单为空）',
    `category_id`  INT UNSIGNED NOT NULL                COMMENT '故障类别，外键 -> fault_category.id',
    `building`     VARCHAR(30)  NOT NULL                COMMENT '宿舍楼栋',
    `dorm_no`      VARCHAR(30)  NOT NULL                COMMENT '宿舍号',
    `description`  TEXT         NOT NULL                COMMENT '故障详细描述',
    `phone`        VARCHAR(20)  NOT NULL                COMMENT '联系电话',
    `status`       ENUM('pending','processing','completed') NOT NULL DEFAULT 'pending'
                                                        COMMENT '工单状态：待受理 / 维修中 / 已完成',
    `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    `accepted_at`  DATETIME     DEFAULT NULL            COMMENT '接单时间',
    `completed_at` DATETIME     DEFAULT NULL            COMMENT '维修完成时间',
    `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '逻辑删除标记：1 已删除（无效工单）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_order_no` (`order_no`),
    KEY `idx_order_status` (`status`),
    KEY `idx_order_student` (`student_id`),
    KEY `idx_order_worker` (`worker_id`),
    KEY `idx_order_created` (`created_at`),
    CONSTRAINT `fk_order_student`  FOREIGN KEY (`student_id`)  REFERENCES `sys_user` (`id`)      ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT `fk_order_worker`   FOREIGN KEY (`worker_id`)   REFERENCES `sys_user` (`id`)      ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT `fk_order_category` FOREIGN KEY (`category_id`) REFERENCES `fault_category` (`id`) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报修工单表';

-- -----------------------------------------------------------------------------
-- 4. 工单图片表（一个工单最多 3 张图片）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `order_image` (
    `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '图片主键',
    `order_id`   INT UNSIGNED NOT NULL                COMMENT '工单，外键 -> repair_order.id',
    `file_path`  VARCHAR(255) NOT NULL                COMMENT '相对 static 的访问路径',
    `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    PRIMARY KEY (`id`),
    KEY `idx_image_order` (`order_id`),
    CONSTRAINT `fk_image_order` FOREIGN KEY (`order_id`) REFERENCES `repair_order` (`id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单现场图片表';

-- -----------------------------------------------------------------------------
-- 5. 工单流转日志表（维修进度轨迹 + 维修备注）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `order_log` (
    `id`          INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志主键',
    `order_id`    INT UNSIGNED NOT NULL                COMMENT '工单，外键 -> repair_order.id',
    `operator_id` INT UNSIGNED DEFAULT NULL            COMMENT '操作人，外键 -> sys_user.id',
    `action`      VARCHAR(20)  NOT NULL                COMMENT '动作：create / accept / processing / remark / complete / review / admin_delete / admin_restore',
    `status`      VARCHAR(20)  DEFAULT NULL            COMMENT '动作发生后的工单状态',
    `remark`      VARCHAR(500) DEFAULT NULL            COMMENT '维修备注或操作说明',
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    PRIMARY KEY (`id`),
    KEY `idx_log_order` (`order_id`),
    CONSTRAINT `fk_log_order`    FOREIGN KEY (`order_id`)    REFERENCES `repair_order` (`id`) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT `fk_log_operator` FOREIGN KEY (`operator_id`) REFERENCES `sys_user` (`id`)     ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单流转日志表';

-- -----------------------------------------------------------------------------
-- 6. 维修评价表（工单完成后由学生评价，一个工单仅一条）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `repair_review` (
    `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '评价主键',
    `order_id`   INT UNSIGNED NOT NULL                COMMENT '工单，外键 -> repair_order.id',
    `student_id` INT UNSIGNED NOT NULL                COMMENT '评价学生，外键 -> sys_user.id',
    `score`      TINYINT      NOT NULL                COMMENT '评分 1-5 星',
    `content`    VARCHAR(500) DEFAULT NULL            COMMENT '评价内容',
    `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评价时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_review_order` (`order_id`),
    KEY `idx_review_student` (`student_id`),
    CONSTRAINT `fk_review_order`   FOREIGN KEY (`order_id`)   REFERENCES `repair_order` (`id`) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT `fk_review_student` FOREIGN KEY (`student_id`) REFERENCES `sys_user` (`id`)     ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='维修服务评价表';

-- =============================================================================
-- 初始化数据
-- =============================================================================

-- 故障类别
INSERT IGNORE INTO `fault_category` (`name`, `sort_order`) VALUES
    ('水电维修', 1),
    ('照明电路', 2),
    ('门窗家具', 3),
    ('网络通信', 4),
    ('空调制冷', 5),
    ('其他', 99);

-- 演示账号（初始密码均为 123456，密码以 PBKDF2-SHA256 哈希形式存储）
INSERT IGNORE INTO `sys_user`
    (`username`, `password_hash`, `role`, `real_name`, `phone`, `student_no`, `dorm_no`, `worker_no`, `skill`)
VALUES
    ('admin', 'pbkdf2:sha256:1000000$TVuAs0dGZsZ4Tu3W$b8b245fd938d6e8cc89d863dba7c277bf820edf826ed492cce2695466ab06455',
     'admin', '系统管理员', '13800000000', NULL, NULL, NULL, NULL),
    ('worker001', 'pbkdf2:sha256:1000000$TVuAs0dGZsZ4Tu3W$b8b245fd938d6e8cc89d863dba7c277bf820edf826ed492cce2695466ab06455',
     'worker', '王师傅', '13800000001', NULL, NULL, 'W1001', '水电维修'),
    ('worker002', 'pbkdf2:sha256:1000000$TVuAs0dGZsZ4Tu3W$b8b245fd938d6e8cc89d863dba7c277bf820edf826ed492cce2695466ab06455',
     'worker', '李师傅', '13800000002', NULL, NULL, 'W1002', '门窗家具'),
    ('student001', 'pbkdf2:sha256:1000000$TVuAs0dGZsZ4Tu3W$b8b245fd938d6e8cc89d863dba7c277bf820edf826ed492cce2695466ab06455',
     'student', '张小明', '13900000001', '20230101', '3号楼 512', NULL, NULL);
