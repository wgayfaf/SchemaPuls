<template>
                <div v-show="currentNav === 'machine_management'">
                    <!-- 顶部机器与运行指标卡片 (支持根据选定环境动态联动) -->
                    <div class="kpi-grid"
                        style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 16px;">
                        <div class="kpi-box">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>托管机器总数</span>
                                <el-tag v-if="selectedMachineEnv !== 'ALL'" size="small" type="primary" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedMachineEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num">{{ machineEnvTotalCount }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Nodes</span></div>
                        </div>
                        <div class="kpi-box kpi-success">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>在线运行节点</span>
                                <el-tag v-if="selectedMachineEnv !== 'ALL'" size="small" type="success" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedMachineEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num" style="color: #059669;">{{ machineEnvOnlineCount }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Online</span></div>
                        </div>
                        <div class="kpi-box kpi-danger">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>离线/异常节点</span>
                                <el-tag v-if="selectedMachineEnv !== 'ALL'" size="small" type="danger" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedMachineEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num" style="color: #dc2626;">{{ machineEnvOfflineCount }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Down</span></div>
                        </div>
                        <div class="kpi-box kpi-info">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>平均 TCP 握手耗时</span>
                                <el-tag v-if="selectedMachineEnv !== 'ALL'" size="small" type="info" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedMachineEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num" style="color: #0284c7;">{{ machineEnvAvgTcpLatency }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">ms</span></div>
                        </div>
                    </div>

                    <!-- 机器资产管理表格卡片 -->
                    <div class="wb-card">
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <div
                                    style="font-size: 15px; font-weight: 600; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-server" style="color: #10b981;"></i>
                                    <span>机器节点列表</span>
                                </div>
                                <el-radio-group v-model="selectedMachineEnv" size="small">
                                    <el-radio-button label="ALL">全部环境</el-radio-button>
                                    <el-radio-button v-for="env in environmentList" :key="env.id" :label="env.name">{{
                                        env.name }}</el-radio-button>
                                </el-radio-group>
                                <el-tag size="small" type="info" effect="plain">{{ filteredMachines.length }}
                                    台机器</el-tag>
                                <el-input v-model="machineSearchQuery" placeholder="搜索机器名、IP或端口..." clearable
                                    size="small" style="width: 220px;">
                                    <template #prefix><i class="fa-solid fa-magnifying-glass"
                                            style="color: #94a3b8;"></i></template>
                                </el-input>
                            </div>
                            <!-- <div style="display: flex; gap: 10px;">
                                <el-button size="small" type="primary" plain @click="fetchData">
                                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px;"></i>刷新
                                </el-button>
                                <el-button size="small" type="primary" @click="openCreateMachineDialog()">
                                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>新建机器
                                </el-button>
                            </div> -->
                        </div>

                        <el-table :data="filteredMachines" v-loading="loading" style="width: 100%">
                            <el-table-column prop="id" label="ID" width="70" align="center"></el-table-column>
                            <el-table-column label="机器名称" min-width="180">
                                <template #default="{ row }">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <i class="fa-solid fa-server" style="color: #10b981;"></i>
                                        <span style="font-weight: 600; color: #0f172a; font-size: 13.5px;">{{ row.name
                                            }}</span>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="所属环境" width="130">
                                <template #default="{ row }">
                                    <el-tag size="small" :type="getGroupTagType(row.environment_name)" effect="light"
                                        style="font-weight: 600;">
                                        {{ row.environment_name || '生产环境' }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column label="网络访问地址" min-width="170">
                                <template #default="{ row }">
                                    <span class="code-pill">{{ row.host }}:{{ row.port }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="服务基准地址 (Base URL)" min-width="230">
                                <template #default="{ row }">
                                    <span v-if="row.base_url"
                                        style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #0284c7; background: #f0f9ff; padding: 2px 8px; border-radius: 4px; border: 1px solid #bae6fd;">
                                        <i class="fa-solid fa-globe" style="margin-right: 4px; font-size: 11px;"></i>{{
                                        row.base_url }}
                                    </span>
                                    <span v-else style="color: #94a3b8; font-size: 12px; font-style: italic;">
                                        默认 (http://{{ row.host }}:{{ row.port }})
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column label="主机在线 (Ping)" width="140" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.ping_ok === true" class="status-badge healthy"
                                        style="font-size: 11.5px; padding: 2px 7px;">
                                        <i class="fa-solid fa-signal" style="margin-right: 4px; color: #059669;"></i>在线
                                        <span v-if="row.last_ping_latency_ms != null"
                                            style="font-size: 10.5px; opacity: 0.85; margin-left: 2px;">({{
                                            row.last_ping_latency_ms }}ms)</span>
                                    </span>
                                    <span v-else-if="row.ping_ok === false" class="status-badge down"
                                        style="font-size: 11.5px; padding: 2px 7px;">
                                        <i class="fa-solid fa-circle-xmark" style="margin-right: 4px;"></i>不可达
                                    </span>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">待探测</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="服务端口 (TCP)" width="130" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.tcp_ok === true" class="status-badge healthy"
                                        style="font-size: 11.5px; padding: 2px 7px;">
                                        <i class="fa-solid fa-plug-circle-check"
                                            style="margin-right: 4px; color: #059669;"></i>开放
                                    </span>
                                    <span v-else-if="row.tcp_ok === false" class="status-badge down"
                                        style="font-size: 11.5px; padding: 2px 7px;">
                                        <i class="fa-solid fa-plug-circle-xmark" style="margin-right: 4px;"></i>关闭/超时
                                    </span>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">待探测</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="综合探活状态" width="140" align="center">
                                <template #default="{ row }">
                                    <el-tooltip v-if="row.last_error_message" :content="row.last_error_message"
                                        placement="top">
                                        <span :class="getStatusBadgeClass(row.current_status)" style="cursor: pointer;">
                                            <i :class="getStatusIcon(row.current_status)"
                                                style="margin-right: 4px;"></i>
                                            {{ row.current_status }}
                                            <i class="fa-solid fa-circle-info"
                                                style="margin-left: 4px; font-size: 10px;"></i>
                                        </span>
                                    </el-tooltip>
                                    <span v-else :class="getStatusBadgeClass(row.current_status)">
                                        <i :class="getStatusIcon(row.current_status)" style="margin-right: 4px;"></i>
                                        {{ row.current_status }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="cron_interval_minutes" label="周期" width="80" align="center">
                                <template #default="{ row }">
                                    <span style="font-size: 12px; color: var(--text-muted);">{{
                                        row.cron_interval_minutes }}m</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="名下接口" width="130" align="center">
                                <template #default="{ row }">
                                    <el-button size="small" type="primary" link @click="goToMachineTargets(row)">
                                        <i class="fa-solid fa-arrow-up-right-from-square"
                                            style="margin-right: 4px;"></i>{{ getMachineApiCount(row.id) }} 个接口
                                    </el-button>
                                </template>
                            </el-table-column>
                            <el-table-column label="最新探活时间" width="170" align="center">
                                <template #default="{ row }">
                                    <span style="color: #94a3b8; font-size: 12px;">{{ formatTime(row.last_probed_at)
                                        }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="220" align="center" fixed="right">
                                <template #default="{ row }">
                                    <div style="display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; width: 190px; margin: 0 auto;">
                                        <el-button size="small" type="success" plain style="flex: 1 1 45%; margin: 0; padding: 4px 6px; height: 28px;"
                                            :loading="triggeringMachineId === row.id" @click="handleTriggerMachine(row)">
                                            <i class="fa-solid fa-bolt" style="margin-right: 4px;"></i>探活
                                        </el-button>
                                        <el-button size="small" type="warning" plain style="flex: 1 1 45%; margin: 0; padding: 4px 6px; height: 28px;" @click="openPostmanImportForMachine(row)" title="从 Postman 集合或 ZIP 压缩包导入接口到该机器">
                                            <i class="fa-solid fa-file-import" style="margin-right: 4px;"></i>导入
                                        </el-button>
                                        <el-button size="small" type="info" plain style="flex: 1 1 45%; margin: 0; padding: 4px 6px; height: 28px;" @click="openMachineDbDrawer(row)" title="管理该机器关联的目标数据库 (支持数据准备与自动销毁)">
                                            <i class="fa-solid fa-database" style="margin-right: 4px;"></i>数据库
                                        </el-button>
                                        <el-button size="small" type="primary" plain style="flex: 1 1 20%; margin: 0; padding: 4px 6px; height: 28px;" @click="openEditMachineDialog(row)">
                                            <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                        </el-button>
                                        <el-popconfirm :title="'确定删除机器 [' + row.name + '] 吗？'" confirm-button-text="确定"
                                            cancel-button-text="取消" @confirm="handleDeleteMachine(row.id, row.name)">
                                            <template #reference>
                                                <el-button size="small" type="danger" plain style="flex: 1 1 20%; margin: 0; padding: 4px 6px; height: 28px;">
                                                    <i class="fa-solid fa-trash-can" style="margin-right: 4px;"></i>删除
                                                </el-button>
                                            </template>
                                        </el-popconfirm>
                                    </div>
                                </template>
                            </el-table-column>
                        </el-table>
                    </div>
                </div>

<!-- ================= 领域弹窗/抽屉 ================= -->
<el-dialog v-model="machineDialogVisible" :title="editingMachineId ? '编辑机器节点' : '新建机器节点'" width="560px"
    destroy-on-close>
    <el-form :model="machineForm" label-width="110px">
        <el-form-item label="所属环境" required>
            <el-select v-model="machineForm.environment_id" placeholder="选择所属环境" style="width: 100%;">
                <el-option v-for="env in environmentList" :key="env.id"
                    :label="env.name + (env.description ? ' (' + env.description + ')' : '')"
                    :value="env.id"></el-option>
            </el-select>
        </el-form-item>
        <el-form-item label="机器名称" required>
            <el-input v-model="machineForm.name" placeholder="例如: 生产网关节点-01"></el-input>
        </el-form-item>
        <el-row :gutter="12">
            <el-col :span="15">
                <el-form-item label="IP / 域名" required>
                    <el-input v-model="machineForm.host"
                        placeholder="例如: 192.168.1.10 或 httpbin.org"></el-input>
                </el-form-item>
            </el-col>
            <el-col :span="9">
                <el-form-item label="TCP 端口" required label-width="80px">
                    <el-input-number v-model="machineForm.port" :min="1" :max="65535"
                        style="width: 100%;"></el-input-number>
                </el-form-item>
            </el-col>
        </el-row>
        <el-form-item label="服务基准地址">
            <el-input v-model="machineForm.base_url"
                placeholder="例如: https://api.prod.com 或 http://192.168.1.10:8080 (选填)">
                <template #prefix><i class="fa-solid fa-globe" style="color: #64748b;"></i></template>
            </el-input>
            <div style="font-size: 11.5px; color: #64748b; line-height: 1.4; margin-top: 4px;">
                选填。该机器节点对外暴露的前置服务基准 URL（支持 http/https、域名或 IP 端口）。名下接口将默认继承此基准地址。
            </div>
        </el-form-item>
        <el-form-item label="探活周期(分)">
            <el-input-number v-model="machineForm.cron_interval_minutes" :min="1" :max="60"
                style="width: 140px;"></el-input-number>
            <span style="margin-left: 10px; color: var(--text-muted); font-size: 12px;">后台定时探测 TCP 端口开放情况</span>
        </el-form-item>
        <el-form-item label="告警通知邮箱">
            <el-input v-model="machineForm.email_input"
                placeholder="留空则使用 SMTP 设置页的全局收件人；也可单独指定，多个邮箱用逗号隔开"></el-input>
        </el-form-item>
    </el-form>
    <template #footer>
        <el-button @click="machineDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMachineForm" :loading="machineSubmitting">
            {{ editingMachineId ? '保存修改' : '确认接入' }}
        </el-button>
    </template>
</el-dialog>

<!-- 机器关联数据库管理抽屉 -->
<el-drawer v-model="machineDbDrawerVisible" :title="'目标数据库管理 - ' + (currentMachineForDb ? currentMachineForDb.name : '')" size="680px" destroy-on-close>
    <div style="padding: 0 4px;">
        <!-- 头部提示卡片 -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 600; color: #1e293b; font-size: 14px; display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-database" style="color: #3b82f6;"></i>
                        <span>{{ currentMachineForDb?.name }}</span>
                        <el-tag size="small" type="info">{{ currentMachineForDb?.host }}:{{ currentMachineForDb?.port }}</el-tag>
                    </div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                        配置该机器关联的数据库凭据。在接口编辑中启用“环境准备”后，系统将在每次执行前自动写入测试数据并导出主键变量，执行后自动回滚销毁。
                    </div>
                </div>
                <div style="display: flex; gap: 8px;">
                    <el-button size="small" type="primary" @click="openCreateDbDialog">
                        <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加数据库
                    </el-button>
                    <el-button size="small" plain @click="fetchMachineDbs(currentMachineForDb.id)" :loading="loadingMachineDbs">
                        <i class="fa-solid fa-arrows-rotate"></i>
                    </el-button>
                </div>
            </div>
            <div style="margin-top: 10px; display: flex; gap: 16px; font-size: 12px; color: #475569; border-top: 1px dashed #cbd5e1; padding-top: 8px;">
                <span><i class="fa-solid fa-shield-halved" style="color: #10b981; margin-right: 4px;"></i>独立受控连接池 (Max Connections 复用保护)</span>
                <span><i class="fa-solid fa-rotate-left" style="color: #f59e0b; margin-right: 4px;"></i>执行后保证清理防污染</span>
            </div>
        </div>

        <!-- 数据库列表表格 -->
        <el-table :data="machineDbList" v-loading="loadingMachineDbs" style="width: 100%" empty-text="暂无数据库配置，点击右上角添加">
            <el-table-column prop="name" label="配置别名" min-width="130">
                <template #default="{ row }">
                    <div style="font-weight: 600; color: #1e293b;">{{ row.name }}</div>
                    <el-tag size="small" type="success" effect="plain" style="font-size: 10px; height: 18px; margin-top: 2px;">
                        {{ (row.db_type || 'postgresql').toUpperCase() }}
                    </el-tag>
                </template>
            </el-table-column>
            <el-table-column label="连接目标" min-width="180">
                <template #default="{ row }">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #0284c7;">
                        {{ row.host }}:{{ row.port }}
                    </div>
                    <div style="font-size: 11.5px; color: #64748b;">
                        库名: <span style="font-weight: 500; color: #334155;">{{ row.database }}</span> / 用户: {{ row.username }}
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="pool_size" label="连接池上限" width="100" align="center">
                <template #default="{ row }">
                    <el-tag size="small" type="info">{{ row.pool_size || 10 }} Conns</el-tag>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="180" align="center">
                <template #default="{ row }">
                    <el-button size="small" type="success" plain @click="handleTestDbConnection(row)" :loading="testingDb">
                        测试
                    </el-button>
                    <el-button size="small" type="primary" plain @click="openEditDbDialog(row)">
                        编辑
                    </el-button>
                    <el-popconfirm :title="'确定删除数据库配置 [' + row.name + '] 吗？'" @confirm="handleDeleteDb(row.id, row.name)">
                        <template #reference>
                            <el-button size="small" type="danger" plain>删除</el-button>
                        </template>
                    </el-popconfirm>
                </template>
            </el-table-column>
        </el-table>
    </div>
</el-drawer>

<!-- 添加/编辑数据库配置弹窗 -->
<el-dialog v-model="dbDialogVisible" :title="editingDbId ? '编辑目标数据库配置' : '接入目标数据库配置'" width="560px" destroy-on-close append-to-body>
    <el-form :model="dbForm" label-width="110px">
        <el-form-item label="配置别名" required>
            <el-input v-model="dbForm.name" placeholder="例如: 业务核心PostgreSQL主库"></el-input>
        </el-form-item>
        <el-form-item label="数据库类型" required>
            <el-select v-model="dbForm.db_type" disabled style="width: 100%;">
                <el-option label="PostgreSQL (支持表结构探查与 Mock 准备)" value="postgresql"></el-option>
            </el-select>
        </el-form-item>
        <el-row :gutter="12">
            <el-col :span="16">
                <el-form-item label="主机/IP" required>
                    <el-input v-model="dbForm.host" placeholder="例如: 127.0.0.1 或 postgres"></el-input>
                </el-form-item>
            </el-col>
            <el-col :span="8">
                <el-form-item label="端口" required label-width="60px">
                    <el-input-number v-model="dbForm.port" :min="1" :max="65535" style="width: 100%;"></el-input-number>
                </el-form-item>
            </el-col>
        </el-row>
        <el-form-item label="数据库名" required>
            <el-input v-model="dbForm.database" placeholder="例如: postgres 或 my_app"></el-input>
        </el-form-item>
        <el-row :gutter="12">
            <el-col :span="12">
                <el-form-item label="用户名" required>
                    <el-input v-model="dbForm.username" placeholder="例如: postgres"></el-input>
                </el-form-item>
            </el-col>
            <el-col :span="12">
                <el-form-item label="密码" label-width="70px">
                    <el-input v-model="dbForm.password" type="password" show-password placeholder="数据库密码"></el-input>
                </el-form-item>
            </el-col>
        </el-row>
        <el-row :gutter="12">
            <el-col :span="12">
                <el-form-item label="连接池上限">
                    <el-input-number v-model="dbForm.pool_size" :min="1" :max="20" style="width: 100%;"></el-input-number>
                </el-form-item>
            </el-col>
            <el-col :span="12">
                <el-form-item label="SSL 模式" label-width="80px">
                    <el-select v-model="dbForm.ssl_mode" style="width: 100%;">
                        <el-option label="prefer (推荐)" value="prefer"></el-option>
                        <el-option label="disable" value="disable"></el-option>
                        <el-option label="require" value="require"></el-option>
                    </el-select>
                </el-form-item>
            </el-col>
        </el-row>
        <div style="background: #f1f5f9; padding: 8px 12px; border-radius: 6px; font-size: 11.5px; color: #475569; line-height: 1.5; margin-bottom: 10px;">
            <i class="fa-solid fa-lightbulb" style="color: #f59e0b; margin-right: 4px;"></i>
            <strong>并发保护机制：</strong>系统采用单例受控连接池，定时调度高频拨测时自动复用既有连接，单个配置最多占用所设数量连接，避免突发激增导致数据库挂起。
        </div>
    </el-form>
    <template #footer>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <el-button type="success" plain @click="handleTestDbConnection(dbForm)" :loading="testingDb">
                <i class="fa-solid fa-plug" style="margin-right: 4px;"></i>测试连接
            </el-button>
            <div style="display: flex; gap: 8px;">
                <el-button @click="dbDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="handleSaveDbForm" :loading="savingDb">
                    {{ editingDbId ? '保存修改' : '确认接入' }}
                </el-button>
            </div>
        </div>
    </template>
</el-dialog>
</template>

<script>
import { inject } from 'vue'

// 共享工作台全局上下文 (后续可收敛为领域 composables)
export default {
    name: 'MachineManagementView',
    setup() {
        return inject('workbench')
    }
}
</script>
