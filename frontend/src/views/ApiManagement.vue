<template>
                <div v-show="currentNav === 'api_management'">
                    <!-- 顶部接口指标卡片 (支持根据选定环境动态联动) -->
                    <div class="kpi-grid"
                        style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 16px;">
                        <div class="kpi-box">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>纳管接口总数</span>
                                <el-tag v-if="selectedApiEnv !== 'ALL'" size="small" type="primary" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedApiEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num">{{ apiEnvTotalCount }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">APIs</span></div>
                        </div>
                        <div class="kpi-box kpi-success">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>契约与运行正常</span>
                                <el-tag v-if="selectedApiEnv !== 'ALL'" size="small" type="success" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedApiEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num" style="color: #059669;">{{ apiEnvHealthyCount }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Healthy</span></div>
                        </div>
                        <div class="kpi-box kpi-danger">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>异常/熔断挂起</span>
                                <el-tag v-if="selectedApiEnv !== 'ALL'" size="small" type="danger" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedApiEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num" style="color: #dc2626;">{{ apiEnvIssueCount }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Issues</span></div>
                        </div>
                        <div class="kpi-box kpi-info">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>平均 HTTP 响应延迟</span>
                                <el-tag v-if="selectedApiEnv !== 'ALL'" size="small" type="info" effect="plain"
                                    style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedApiEnv
                                    }}</el-tag>
                            </div>
                            <div class="kpi-num" style="color: #8b5cf6;">{{ apiEnvAvgLatency }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">ms</span></div>
                        </div>
                    </div>

                    <!-- 接口资产管理表格卡片 -->
                    <div class="wb-card">
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <div
                                    style="font-size: 15px; font-weight: 600; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-code" style="color: #8b5cf6;"></i>
                                    <span>机器接口列表</span>
                                </div>
                                <el-radio-group v-model="selectedApiEnv" size="small">
                                    <el-radio-button label="ALL">全部环境</el-radio-button>
                                    <el-radio-button v-for="env in environmentList" :key="env.id" :label="env.name">{{
                                        env.name }}</el-radio-button>
                                </el-radio-group>
                                <el-select v-model="selectedApiMachine" placeholder="所属机器" size="small"
                                    style="width: 170px;">
                                    <el-option label="全部机器节点" value="ALL"></el-option>
                                    <el-option v-for="m in currentEnvMachineOptions" :key="m.id"
                                        :label="m.name + ' (' + m.host + ':' + m.port + ')'" :value="m.id"></el-option>
                                </el-select>
                                <el-select v-model="selectedApiStatus" placeholder="状态过滤" size="small"
                                    style="width: 130px;">
                                    <el-option label="全部状态" value="ALL"></el-option>
                                    <el-option label="HEALTHY" value="HEALTHY"></el-option>
                                    <el-option label="DOWN" value="DOWN"></el-option>
                                    <el-option label="DEGRADED" value="DEGRADED"></el-option>
                                    <el-option label="CIRCUIT_BROKEN" value="CIRCUIT_BROKEN"></el-option>
                                </el-select>
                                <el-tag size="small" type="info" effect="plain">{{ filteredApis.length }} 个接口</el-tag>
                                <el-input v-model="apiSearchQuery" placeholder="搜索接口名、路径、机器..." clearable size="small"
                                    style="width: 210px;">
                                    <template #prefix><i class="fa-solid fa-magnifying-glass"
                                            style="color: #94a3b8;"></i></template>
                                </el-input>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <el-button size="small" type="primary" plain @click="fetchData">
                                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px;"></i>刷新
                                </el-button>
                                <el-button size="small" type="warning" plain @click="openGenericPostmanImport">
                                    <i class="fa-solid fa-file-import" style="margin-right: 4px;"></i>导入 Postman 接口
                                </el-button>
                                <el-button size="small" type="primary" @click="openCreateApiDialog()">
                                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>新建接口
                                </el-button>
                            </div>
                        </div>

                        <el-table :data="filteredApis" v-loading="loading" style="width: 100%">
                            <el-table-column prop="id" label="ID" width="50" align="center"></el-table-column>
                            <el-table-column label="接口名称" min-width="150">
                                <template #default="{ row }">
                                    <div style="display: flex; flex-direction: column;">
                                        <div style="font-weight: 600; color: #0f172a; font-size: 13.5px;">{{ row.name }}
                                        </div>
                                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                                            <i class="fa-solid fa-server"
                                                style="color: #10b981; margin-right: 4px;"></i>{{ row.machine_name }}
                                            <span v-if="row.machine_status === 'OFFLINE'"
                                                style="color: #ef4444; font-weight: 600;">(宿主离线)</span>
                                        </div>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="所属环境" width="100" align="center">
                                <template #default="{ row }">
                                    <el-tag size="small" :type="getGroupTagType(row.environment_name)" effect="light"
                                        style="font-weight: 600;">
                                        {{ row.environment_name || '生产环境' }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column label="请求方法与完整地址" min-width="190">
                                <template #default="{ row }">
                                    <div style="display: flex; align-items: center; gap: 6px;">
                                        <el-tag size="small"
                                            :type="row.http_method === 'GET' ? 'success' : (row.http_method === 'POST' ? 'primary' : 'warning')"
                                            effect="dark" style="font-weight: 700; font-size: 11px;">
                                            {{ row.http_method }}
                                        </el-tag>
                                        <span class="code-pill"
                                            style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                                            :title="row.full_url || (row.machine_host + ':' + row.machine_port + row.http_path)">
                                            {{ row.full_url || (row.machine_host + ':' + row.machine_port +
                                             row.http_path) }}
                                        </span>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="运行状态" width="115" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.current_status === 'CIRCUIT_BROKEN'"
                                        class="status-badge circuit-broken">
                                        <i class="fa-solid fa-ban" style="margin-right: 4px;"></i>熔断挂起
                                    </span>
                                    <span v-else :class="getStatusBadgeClass(row.current_status)">
                                        <i :class="getStatusIcon(row.current_status)" style="margin-right: 4px;"></i>
                                        {{ row.current_status }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column label="HTTP/延迟" width="110" align="center">
                                <template #default="{ row }">
                                    <div
                                        v-if="row.last_http_latency_ms !== null && row.last_http_latency_ms !== undefined">
                                        <span :class="getLatencyBadgeClass(row.last_http_latency_ms)">
                                            {{ row.last_http_latency_ms }} ms
                                        </span>
                                    </div>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">待探测</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="契约校验" width="90" align="center">
                                <template #default="{ row }">
                                    <el-tag v-if="row.last_schema_matched === true" type="success"
                                        size="small">一致</el-tag>
                                    <el-tag v-else-if="row.last_schema_matched === false" type="danger"
                                        size="small">突变</el-tag>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">未校验</span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="cron_interval_minutes" label="探测周期" width="95" align="center">
                                <template #default="{ row }">
                                    <el-tooltip :content="getIntervalTooltip(row.cron_interval_minutes, row.is_active)" placement="top">
                                        <el-tag v-if="row.is_active === false" size="small" type="info" effect="plain"
                                            class="probe-interval-tag"
                                            style="cursor: pointer; font-size: 11px;" @click="toggleApiActive(row)">
                                            <i class="fa-solid fa-pause" style="margin-right: 3px;"></i>已关闭
                                        </el-tag>
                                        <el-tag v-else size="small" type="primary" effect="plain"
                                            class="probe-interval-tag"
                                            style="cursor: pointer; font-weight: 600; font-size: 11px;" @click="toggleApiActive(row)">
                                            <i class="fa-solid fa-clock" style="margin-right: 3px; font-size: 10px;"></i>{{ formatIntervalDisplay(row.cron_interval_minutes, row.is_active) }}
                                        </el-tag>
                                    </el-tooltip>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="200" align="center" fixed="right">
                                <template #default="{ row }">
                                    <div class="api-action-grid">
                                        <el-button size="small" type="success" plain :loading="triggeringApiId === row.id"
                                            @click="handleTriggerApi(row)">
                                            <i class="fa-solid fa-bolt" style="margin-right: 4px;"></i>拨测
                                        </el-button>
                                        <el-button size="small" type="info" plain @click="openApiMetricsDrawer(row)">
                                            <i class="fa-solid fa-chart-line" style="margin-right: 4px;"></i>时序
                                        </el-button>
                                        <el-button size="small" type="primary" plain @click="openEditApiDialog(row)">
                                            <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                        </el-button>
                                        <el-popconfirm :title="'确定删除接口 [' + row.name + '] 吗？'" confirm-button-text="确定"
                                            cancel-button-text="取消" @confirm="handleDeleteApi(row.id, row.name)">
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
</template>

<script>
import { inject } from 'vue'

// 共享工作台全局上下文 (后续可收敛为领域 composables)
export default {
    name: 'ApiManagementView',
    setup() {
        return inject('workbench')
    }
}
</script>
