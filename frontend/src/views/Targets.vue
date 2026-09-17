<template>
                <div v-show="currentNav === 'targets'">
                    <div class="wb-card">
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 15px; font-weight: 600; color: #0f172a;">接口健康探测列表</span>
                                <el-tag size="small" type="info" effect="plain">{{ filteredTargets.length }} 项</el-tag>
                                <el-button size="small" type="primary" plain @click="switchNav('machine_management')">
                                    <i class="fa-solid fa-server" style="margin-right: 4px;"></i>机器管理
                                </el-button>
                                <el-button size="small" type="primary" plain @click="switchNav('api_management')">
                                    <i class="fa-solid fa-code" style="margin-right: 4px;"></i>接口管理
                                </el-button>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <el-radio-group v-model="selectedGroup" size="small">
                                    <el-radio-button label="ALL">全部环境</el-radio-button>
                                    <el-radio-button v-for="g in groupList" :key="g.name" :label="g.name">{{ g.name
                                        }}</el-radio-button>
                                </el-radio-group>
                            </div>
                        </div>

                        <el-table :data="filteredTargets" v-loading="loading" style="width: 100%">
                            <el-table-column prop="id" label="ID" width="60" align="center"></el-table-column>
                            <el-table-column label="所属环境" width="130">
                                <template #default="{ row }">
                                    <el-tag size="small" :type="getGroupTagType(row.group_name)" effect="light"
                                        style="font-weight: 600;">
                                        {{ row.group_name || '生产环境' }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column prop="name" label="目标名称" min-width="170">
                                <template #default="{ row }">
                                    <div style="font-weight: 600; color: #0f172a;">{{ row.name }}</div>
                                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                                        每 {{ row.cron_interval_minutes }} 分钟定时探活
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="探测目标 (Host:Port:Path)" min-width="250">
                                <template #default="{ row }">
                                    <span class="code-pill">{{ row.http_method }} {{ row.host }}:{{ row.port }}{{
                                        row.http_path }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="最新延迟" width="135" align="center">
                                <template #default="{ row }">
                                    <div v-if="row.last_latency_ms !== null && row.last_latency_ms !== undefined">
                                        <el-tooltip
                                            :content="'HTTP 响应: ' + (row.last_http_latency_ms ? row.last_http_latency_ms + 'ms' : '未发起') + ' | TCP 握手: ' + (row.last_tcp_latency_ms ? row.last_tcp_latency_ms + 'ms' : '失败')"
                                            placement="top">
                                            <span :class="getLatencyBadgeClass(row.last_latency_ms)"
                                                style="cursor: pointer;">
                                                <i class="fa-solid fa-bolt"
                                                    style="font-size: 10px; margin-right: 3px;"></i>
                                                {{ row.last_latency_ms }} ms
                                            </span>
                                        </el-tooltip>
                                    </div>
                                    <span v-else style="color: #94a3b8; font-size: 12px;">待探测</span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="current_status" label="健康状态" width="130" align="center">
                                <template #default="{ row }">
                                    <span :class="getStatusBadgeClass(row.current_status)">
                                        <i :class="getStatusIcon(row.current_status)"></i>
                                        {{ row.current_status }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="consecutive_failures" label="连续失败" width="90" align="center">
                                <template #default="{ row }">
                                    <el-tag v-if="row.consecutive_failures > 0" type="danger" size="small"
                                        effect="plain">{{ row.consecutive_failures }} 次</el-tag>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">0</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="280" align="center" fixed="right">
                                <template #default="{ row }">
                                    <el-button size="small" type="success" plain :loading="triggeringId === row.id"
                                        @click="handleTrigger(row)">
                                        <i class="fa-solid fa-play" style="margin-right: 4px;"></i>探测
                                    </el-button>
                                    <el-button size="small" type="primary" plain @click="openMetricsDrawer(row)">
                                        <i class="fa-solid fa-chart-simple" style="margin-right: 4px;"></i>时序
                                    </el-button>
                                    <el-button size="small" type="primary" plain @click="openEditDialog(row)">
                                        <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                    </el-button>
                                    <el-popconfirm title="确定删除该监控目标吗？" @confirm="handleDelete(row.id)">
                                        <template #reference>
                                            <el-button size="small" type="danger" plain>
                                                <i class="fa-solid fa-trash-can"></i>
                                            </el-button>
                                        </template>
                                    </el-popconfirm>
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
    name: 'TargetsView',
    setup() {
        return inject('workbench')
    }
}
</script>
