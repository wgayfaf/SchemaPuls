<template>
                <div v-show="currentNav === 'dashboard'">
                    <!-- 全局资产与健康概览 KPI 网格 -->
                    <div class="kpi-grid">
                        <div class="kpi-box">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                托管环境总数</div>
                            <div class="kpi-num">{{ environmentList.length }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Envs</span></div>
                        </div>
                        <div class="kpi-box kpi-info">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                纳管机器节点</div>
                            <div class="kpi-num" style="color: #0284c7;">
                                {{ machineList.length }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">Nodes</span>
                                <span style="font-size: 11.5px; margin-left: 6px; font-weight: 500;"
                                    :style="{ color: offlineMachineCount > 0 ? '#dc2626' : '#059669' }">
                                    ({{ onlineMachineCount }}在线<span v-if="offlineMachineCount > 0">/{{
                                        offlineMachineCount }}离线</span>)
                                </span>
                            </div>
                        </div>
                        <div class="kpi-box kpi-success">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                服务接口总数</div>
                            <div class="kpi-num" style="color: #059669;">
                                {{ apiList.length }} <span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">APIs</span>
                                <span style="font-size: 11.5px; margin-left: 6px; font-weight: 500;"
                                    :style="{ color: issueApiCount > 0 ? '#dc2626' : '#059669' }">
                                    ({{ healthyApiCount }}正常<span v-if="issueApiCount > 0">/{{ issueApiCount
                                        }}异常</span>)
                                </span>
                            </div>
                        </div>
                        <div class="kpi-box" :class="summary.sla_rate >= 95 ? 'kpi-info' : 'kpi-danger'">
                            <div
                                style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                全局系统可用率 (SLA)</div>
                            <div class="kpi-num" :style="{ color: summary.sla_rate >= 95 ? '#0284c7' : '#dc2626' }">
                                {{ summary.sla_rate || 100 }}<span
                                    style="font-size: 12px; color: #64748b; font-weight: normal;">%</span>
                            </div>
                        </div>
                    </div>

                    <!-- 环境运行全景态势看板 (按环境归类，不直接堆砌具体接口) -->
                    <div class="wb-card">
                        <div
                            style="margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px;">
                            <div>
                                <div
                                    style="font-weight: 700; font-size: 16px; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-layer-group" style="color: #2563eb;"></i>
                                    <span>各环境运行态势看板</span>
                                    <el-tag size="small" type="primary" effect="plain">{{ dashboardEnvironments.length
                                        }} 个环境已纳管</el-tag>
                                </div>
                                <div style="font-size: 12.5px; color: #64748b; margin-top: 4px;">
                                    按环境维度聚合汇总机器连通与接口契约健康度；接口详细探测配置与历史时序请在【接口管理】查看。
                                </div>
                            </div>
                        </div>

                        <!-- 暂无环境时的空状态 -->
                        <div v-if="dashboardEnvironments.length === 0" style="padding: 40px 0; text-align: center;">
                            <el-empty description="暂未配置任何监控环境">
                            </el-empty>
                        </div>

                        <!-- 按环境分类的卡片矩阵 -->
                        <div v-else
                            style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 18px;">
                            <div v-for="env in dashboardEnvironments" :key="env.id" class="env-dashboard-card"
                                :style="{ borderTop: '4px solid ' + getEnvBorderTopColor(env.status) }">

                                <!-- 环境卡片头部 -->
                                <div class="env-dashboard-card-header">
                                    <div>
                                        <div class="env-title-group">
                                            <span class="env-title-text">{{ env.name }}</span>
                                            <span :class="getEnvStatusBadgeClass(env.status)">
                                                {{ env.status === 'HEALTHY' ? '运行健康' : (env.status === 'DOWN' ? '存在故障' :
                                                (env.status === 'DEGRADED' ? '服务受损' : '暂无机器')) }}
                                            </span>
                                        </div>
                                        <div class="env-desc-text">{{ env.description || '暂无环境描述说明' }}</div>
                                    </div>
                                </div>

                                <!-- 环境卡片主体统计 -->
                                <div class="env-dashboard-card-body">
                                    <!-- 机器与接口双栏指标 -->
                                    <div class="env-stat-subgrid">
                                        <!-- 机器节点小统计 -->
                                        <div class="env-substat-box">
                                            <div class="env-substat-title">
                                                <i class="fa-solid fa-server" style="color: #10b981;"></i>
                                                <span>机器节点</span>
                                            </div>
                                            <div v-if="env.machineTotal === 0" class="env-substat-value"
                                                style="color: #94a3b8; font-size: 14px;">
                                                <span>暂无机器</span>
                                            </div>
                                            <div v-else class="env-substat-value">
                                                <span>{{ env.machineTotal }}</span>
                                                <span
                                                    style="font-size: 11px; font-weight: normal; color: #64748b;">台</span>
                                                <div
                                                    style="font-size: 11.5px; margin-left: auto; display: flex; align-items: center; gap: 4px;">
                                                    <span style="color: #059669; font-weight: 600;">{{ env.machineOnline
                                                        }} 在线</span>
                                                    <span style="color: #cbd5e1;">/</span>
                                                    <span
                                                        :style="{ color: env.machineOffline > 0 ? '#dc2626' : '#64748b' }"
                                                        style="font-weight: 600;">
                                                        {{ env.machineOffline }} 离线
                                                    </span>
                                                </div>
                                            </div>
                                            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                                                <span v-if="env.machineTotal === 0"
                                                    style="color: #94a3b8;">未纳管机器节点</span>
                                                <span v-else>平均 TCP: {{ env.avgTcp ? env.avgTcp + ' ms' : '无握手'
                                                    }}</span>
                                            </div>
                                        </div>

                                        <!-- 接口探针小统计 -->
                                        <div class="env-substat-box">
                                            <div class="env-substat-title">
                                                <i class="fa-solid fa-code" style="color: #8b5cf6;"></i>
                                                <span>接口服务</span>
                                            </div>
                                            <div class="env-substat-value">
                                                <span>{{ env.apiTotal }}</span>
                                                <span
                                                    style="font-size: 11px; font-weight: normal; color: #64748b;">个</span>
                                                <span style="font-size: 11px; margin-left: auto;"
                                                    :style="{ color: env.apiDown > 0 ? '#dc2626' : '#059669' }">
                                                    {{ env.apiDown > 0 ? env.apiDown + ' 异常' : (env.apiTotal > 0 ?
                                                    '契约匹配' : '未挂载') }}
                                                </span>
                                            </div>
                                            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                                                平均响应: {{ env.avgHttp ? env.avgHttp + ' ms' : '无数据' }}
                                            </div>
                                        </div>
                                    </div>
                                    <!-- 环境综合可用率进度条 -->
                                    <div>
                                        <div
                                            style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 4px; color: #475569;">
                                            <span>环境综合健康可用率</span>
                                            <span v-if="env.machineTotal === 0"
                                                style="font-weight: 600; color: #94a3b8;">
                                                0% (暂无机器)
                                            </span>
                                            <span v-else style="font-weight: 700;"
                                                :style="{ color: env.slaRate >= 95 ? '#059669' : (env.slaRate >= 80 ? '#d97706' : '#dc2626') }">
                                                {{ env.slaRate }}%
                                            </span>
                                        </div>
                                        <el-progress :percentage="env.slaRate"
                                            :status="env.machineTotal === 0 ? '' : (env.slaRate >= 95 ? 'success' : (env.slaRate >= 80 ? 'warning' : 'exception'))"
                                            :color="env.machineTotal === 0 ? '#cbd5e1' : undefined" :stroke-width="6"
                                            :show-text="false">
                                        </el-progress>
                                    </div>
                                </div>

                                <!-- 环境卡片底部操作条 -->
                                <div class="env-dashboard-card-footer">
                                    <div style="display: flex; gap: 6px;">
                                        <el-button size="small" type="primary" plain @click="goToEnvApis(env.name)">
                                            <i class="fa-solid fa-code" style="margin-right: 4px;"></i>管理接口 ({{
                                            env.apiTotal }})
                                        </el-button>
                                        <el-button size="small" type="info" plain @click="goToEnvMachines(env.name)">
                                            <i class="fa-solid fa-server" style="margin-right: 4px;"></i>机器 ({{
                                            env.machineTotal }})
                                        </el-button>
                                    </div>
                                    <div>
                                        <el-button size="small" text type="primary" @click="openCreateApiDialog()">
                                            <i class="fa-solid fa-plus"></i> 新建接口
                                        </el-button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
</template>

<script>
import { inject } from 'vue'

// 共享工作台全局上下文 (后续可收敛为领域 composables)
export default {
    name: 'DashboardView',
    setup() {
        return inject('workbench')
    }
}
</script>
