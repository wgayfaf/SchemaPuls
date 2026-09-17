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
                            <el-table-column label="操作" width="200" align="center" fixed="right">
                                <template #default="{ row }">
                                    <div class="machine-action-grid">
                                        <el-button size="small" type="success" plain
                                            :loading="triggeringMachineId === row.id" @click="handleTriggerMachine(row)">
                                            <i class="fa-solid fa-bolt" style="margin-right: 4px;"></i>探活
                                        </el-button>
                                        <el-button size="small" type="warning" plain @click="openPostmanImportForMachine(row)" title="从 Postman 集合或 ZIP 压缩包导入接口到该机器">
                                            <i class="fa-solid fa-file-import" style="margin-right: 4px;"></i>导入接口
                                        </el-button>
                                        <el-button size="small" type="primary" plain @click="openEditMachineDialog(row)">
                                            <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                        </el-button>
                                        <el-popconfirm :title="'确定删除机器 [' + row.name + '] 吗？'" confirm-button-text="确定"
                                            cancel-button-text="取消" @confirm="handleDeleteMachine(row.id, row.name)">
                                            <template #reference>
                                                <el-button size="small" type="danger" plain>
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
            <el-input v-model="machineForm.email_input" placeholder="多个邮箱用逗号隔开，如: ops@company.com"></el-input>
        </el-form-item>
    </el-form>
    <template #footer>
        <el-button @click="machineDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMachineForm" :loading="machineSubmitting">
            {{ editingMachineId ? '保存修改' : '确认接入' }}
        </el-button>
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
