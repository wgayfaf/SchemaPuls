<template>
                <div v-show="currentNav === 'incidents'">
                    <!-- 故障排障列表卡片 -->
                    <div class="wb-card">
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <div
                                    style="font-size: 15px; font-weight: 600; color: #ef4444; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-triangle-exclamation"></i>
                                    <span>实时告警与受损节点清单</span>
                                </div>
                                <el-tag size="small" :type="downTargets.length > 0 ? 'danger' : 'success'"
                                    effect="plain">
                                    {{ downTargets.length }} 个故障目标待处置
                                </el-tag>
                                <el-input v-model="incidentSearchQuery" placeholder="搜索故障目标、地址或环境..." clearable
                                    size="small" style="width: 230px;">
                                    <template #prefix><i class="fa-solid fa-magnifying-glass"
                                            style="color: #94a3b8;"></i></template>
                                </el-input>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <el-button size="small" type="primary" plain @click="fetchData">
                                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px;"></i>刷新
                                </el-button>
                            </div>
                        </div>

                        <div v-if="filteredDownTargets.length === 0"
                            style="text-align: center; padding: 48px 20px; color: #059669;">
                            <i class="fa-solid fa-circle-check"
                                style="font-size: 48px; margin-bottom: 12px; color: #10b981;"></i>
                            <div style="font-size: 16px; font-weight: 600; color: #0f172a;">太棒了！当前没有任何异常受损节点</div>
                            <div style="font-size: 13px; color: var(--text-muted); margin-top: 6px;">
                                接口管理内所有纳管接口均处于正常健康运行状态。</div>
                        </div>
                        <el-table v-else :data="filteredDownTargets" style="width: 100%">
                            <el-table-column label="所属环境" width="130">
                                <template #default="{ row }">
                                    <el-tag size="small" :type="getGroupTagType(row.environment_name)" effect="light"
                                        style="font-weight: 600;">
                                        {{ row.environment_name || '生产环境' }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column prop="name" label="受损接口名称" min-width="180">
                                <template #default="{ row }">
                                    <div style="font-weight: 600; color: #0f172a;">{{ row.name }}</div>
                                    <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                                        <i class="fa-solid fa-server" style="color: #10b981; margin-right: 3px;"></i>{{
                                        row.machine_name || (row.machine_host + ':' + row.machine_port) }}
                                        <span v-if="row.machine_status === 'OFFLINE'"
                                            style="color: #ef4444; font-weight: 600;">(宿主离线)</span>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="网络访问地址" min-width="260">
                                <template #default="{ row }">
                                    <div style="display: flex; align-items: center; gap: 6px;">
                                        <el-tag size="small"
                                            :type="row.http_method === 'GET' ? 'success' : (row.http_method === 'POST' ? 'primary' : 'warning')"
                                            effect="dark" style="font-weight: 700; font-size: 11px;">
                                            {{ row.http_method || 'GET' }}
                                        </el-tag>
                                        <span class="code-pill"
                                            style="max-width: 210px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                                            :title="row.full_url || (row.machine_host + ':' + row.machine_port + row.http_path)">
                                            {{ row.full_url || (row.machine_host + ':' + row.machine_port +
                                            row.http_path) }}
                                        </span>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="健康状态" width="135" align="center">
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
                            <el-table-column label="最新延迟" width="120" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.last_http_latency_ms"
                                        :class="getLatencyBadgeClass(row.last_http_latency_ms)">
                                        {{ row.last_http_latency_ms }} ms
                                    </span>
                                    <span v-else style="color: #dc2626; font-size: 12px; font-weight: 600;">超时/断开</span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="consecutive_failures" label="连续失败" width="100" align="center">
                                <template #default="{ row }"><el-tag type="danger" effect="dark">{{
                                        row.consecutive_failures }} 次</el-tag></template>
                            </el-table-column>
                            <el-table-column label="操作" width="220" align="center" fixed="right">
                                <template #default="{ row }">
                                    <el-button size="small" type="success" plain :loading="triggeringApiId === row.id"
                                        @click="handleTriggerApi(row)">
                                        <i class="fa-solid fa-bolt" style="margin-right: 4px;"></i>复测
                                    </el-button>
                                    <el-button size="small" type="info" plain @click="openApiMetricsDrawer(row)">
                                        <i class="fa-solid fa-chart-line" style="margin-right: 4px;"></i>时序排障
                                    </el-button>
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
    name: 'IncidentsView',
    setup() {
        return inject('workbench')
    }
}
</script>
