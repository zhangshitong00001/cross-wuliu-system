# 跨境物流管理系统

## 项目概述
基于Flask + SQLAlchemy + MySQL + Vue.js开发的跨境物流全流程管理系统，覆盖从中国云仓集货到哈萨克斯坦阿拉木图408个收件点配送的全链路管理。

## 技术栈
- **后端**: Python Flask 2.3.3 + SQLAlchemy 2.0
- **数据库**: MySQL 8.0
- **前端**: Vue.js 3 (CDN) + Bootstrap 5
- **认证**: Flask-Login

## 功能模块

### 核心业务流程（13大模块）
1. **云仓集货管理** - 收货登记、库存管理、批次管理、集货确认
2. **阿拉木图收件点分装管理** - 408个收件点管理、分装任务、清单生成
3. **文件生成管理** - 装车文件、报关文件、版本管理
4. **装车运输管理** - 任务分配、车辆管理、路线管理、节点记录
5. **霍尔果斯口岸出口报关管理** - 文件提交、进度同步、材料补充
6. **哈国口岸进口清关管理** - 文件提交、进度跟踪、费用录入
7. **口岸至阿拉木图仓库运输管理** - 车辆调度、到货预告、验收
8. **阿拉木图仓库分拣管理** - 收货登记、入库、分拣任务
9. **收件点配送管理** - 任务生成、调度、路线优化
10. **签收入库管理** - 扫码签收、凭证上传、入库登记
11. **对账管理** - 自动对账、差异识别、多维度对账
12. **资金结算管理** - 结算单生成、审核、支付
13. **支付开票系统** - 支付对接、发票生成、税务对接

### 核心功能模块
- 物流状态实时跟踪
- 多级权限管理（9种角色）
- 数据统计与分析
- 异常预警（8种预警类型）
- 数据接口对接
- 计费规则可配置
- 对账差异智能处理

## 快速启动

### 环境要求
- Python 3.12+
- MySQL 8.0+
- Node.js (可选，用于前端开发)

### 安装步骤

```bash
# 1. 安装依赖
pip install flask flask-sqlalchemy flask-cors flask-login pymysql

# 2. 创建数据库
mysql -u root -p -e "CREATE DATABASE cross_border_logistics DEFAULT CHARACTER SET utf8mb4;"

# 3. 修改配置
# 编辑 config/config.py，修改数据库连接信息

# 4. 启动服务
python run.py
```

### 默认账号
- 超级管理员: admin / admin123
- 仓库操作员: 仓库操作员 / warehouse1
- 运输人员: 运输人员 / transport1
- 报关专员: 报关专员 / customs1

## API文档
系统提供完整的RESTful API，所有业务接口以 `/api/` 开头。

### 认证接口
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/logout | 用户登出 |
| GET | /api/auth/profile | 获取当前用户 |
| GET | /api/auth/users | 用户列表 |
| POST | /api/auth/users | 创建用户 |

### 核心业务接口
| 模块 | 方法 | 路径前缀 |
|------|------|----------|
| 云仓集货 | GET/POST | /api/warehouse/receipts |
| 库存管理 | GET | /api/warehouse/inventory |
| 批次管理 | GET/POST | /api/warehouse/batches |
| 收件点 | GET/POST/PUT | /api/sorting/points |
| 分装任务 | GET/POST | /api/sorting/tasks |
| 文件管理 | GET/POST/PUT | /api/document/list |
| 运输任务 | GET/POST | /api/transport/tasks |
| 报关管理 | GET/POST | /api/customs/declarations |
| 清关管理 | GET/POST | /api/clearance/records |
| 配送管理 | GET/POST | /api/distribution/tasks |
| 签收管理 | GET/POST | /api/sign/records |
| 对账管理 | GET/POST | /api/reconciliation/records |
| 结算管理 | GET/POST | /api/settlement/orders |
| 支付管理 | GET/POST | /api/payment/records |
| 物流跟踪 | GET | /api/tracking/query |
| 异常预警 | GET/POST | /api/alert/list |
| 计费规则 | GET/POST/PUT | /api/charging/rules |

## 数据库模型
系统包含27个数据表，覆盖所有业务场景：
- users, roles, permissions - 用户权限
- warehouse_receipts, warehouse_inventories, warehouse_batches - 仓储
- collection_points, sorting_tasks, sorting_records - 分装
- documents, document_versions - 文件
- vehicles, drivers - 车辆司机
- transport_tasks, transport_nodes, transport_exceptions - 运输
- customs_declarations, customs_materials - 报关
- clearance_records, clearance_fees - 清关
- distribution_tasks, distribution_records - 配送
- sign_records, sign_certificates - 签收
- reconciliation_records, reconciliation_details - 对账
- settlement_orders, settlement_flows - 结算
- payment_records, invoice_records - 支付
- tracking_records - 跟踪
- alert_records - 预警
- charging_rules - 计费
- operation_logs - 日志

## 部署说明
支持部署在阿里云、腾讯云、华为云等云服务器，兼容Windows/Linux操作系统。
