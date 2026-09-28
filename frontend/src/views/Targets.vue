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

<!-- ================= 领域弹窗/抽屉 ================= -->
<el-dialog v-model="createDialogVisible" :title="editingTargetId ? '编辑监控目标' : '新建监控目标'" width="760px"
    destroy-on-close>
    <el-form :model="form" label-width="120px">
        <el-row :gutter="16">
            <el-col :span="12">
                <el-form-item label="所属环境" required>
                    <el-select v-model="form.group_name" filterable allow-create default-first-option
                        placeholder="选择或直接输入新环境" style="width: 100%;">
                        <el-option v-for="e in environmentList" :key="e.id"
                            :label="e.name + (e.description ? ' (' + e.description + ')' : '')"
                            :value="e.name"></el-option>
                        <template v-for="g in groupList" :key="g.name">
                            <el-option v-if="!environmentList.some(e => e.name === g.name)" :label="g.name"
                                :value="g.name"></el-option>
                        </template>
                    </el-select>
                </el-form-item>
            </el-col>
            <el-col :span="12">
                <el-form-item label="目标名称" required>
                    <el-input v-model="form.name" placeholder="例如: 认证中心服务"></el-input>
                </el-form-item>
            </el-col>
        </el-row>

        <el-row :gutter="16">
            <el-col :span="14">
                <el-form-item label="IP / 域名" required>
                    <el-input v-model="form.host" placeholder="例如: httpbin.org 或 192.168.1.10"></el-input>
                    <div v-if="currentEnvMachines.length > 0"
                        style="margin-top: 6px; font-size: 12px; color: var(--text-muted); display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
                        <span>快捷绑定已有机器:</span>
                        <el-tag v-for="m in currentEnvMachines" :key="m.id" size="small" type="info"
                            style="cursor: pointer;" @click="form.host = m.host; form.port = m.port;">
                            {{ m.name }} ({{ m.host }}:{{ m.port }})
                        </el-tag>
                    </div>
                </el-form-item>
            </el-col>
            <el-col :span="10">
                <el-form-item label="TCP 端口" required>
                    <el-input-number v-model="form.port" :min="1" :max="65535"
                        style="width: 100%;"></el-input-number>
                </el-form-item>
            </el-col>
        </el-row>

        <el-row :gutter="16">
            <el-col :span="14">
                <el-form-item label="HTTP 路径">
                    <el-input v-model="form.http_path" placeholder="/health 或 /get"></el-input>
                </el-form-item>
            </el-col>
            <el-col :span="10">
                <el-form-item label="周期(分钟)">
                    <el-input-number v-model="form.cron_interval_minutes" :min="1" :max="1440"
                        style="width: 100%;"></el-input-number>
                </el-form-item>
            </el-col>
        </el-row>

        <el-form-item label="告警邮箱">
            <el-input v-model="form.email_input"
                placeholder="多个邮箱用逗号分隔，例如: admin@company.com, ops@company.com"></el-input>
        </el-form-item>

        <!-- Schema 智能推导辅助卡片 (淡蓝底) -->
        <div
            style="background: #f0f7ff; padding: 14px; border-radius: 6px; border: 1px dashed #bfdbfe; margin-bottom: 16px;">
            <div
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 13px; font-weight: 600; color: #1d4ed8;">
                    <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 6px;"></i>从接口返回的真实 JSON 自动生成
                    Schema
                </span>
                <el-button size="small" type="primary" @click="handleInferSchema" :loading="inferring">
                    一键生成 Draft-7 规则
                </el-button>
            </div>
            <el-input v-model="sampleJsonText" type="textarea" :rows="3"
                placeholder="在此粘贴真实的 JSON 响应片段..."></el-input>
        </div>

        <el-form-item label="预设 Schema" required>
            <el-input v-model="form.schema_text" type="textarea" :rows="6"
                style="font-family: monospace;"></el-input>
        </el-form-item>
    </el-form>

    <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateTarget" :loading="submitting">
            {{ editingTargetId ? '保存修改' : '保存并启动监控' }}
        </el-button>
    </template>
</el-dialog>
<el-drawer v-model="drawerVisible" :title="activeTarget ? '接口时序排障报表 - ' + activeTarget.name : '时序排障'"
    size="68%">
    <div v-if="activeTarget">
        <!-- 接口专属档案信息卡片 -->
        <div
            style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 14px 18px; border-radius: 8px; border: 1px solid #cbd5e1; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <el-tag
                        :type="activeTarget.http_method === 'GET' ? 'success' : (activeTarget.http_method === 'POST' ? 'primary' : 'warning')"
                        effect="dark" style="font-weight: 700; font-size: 11.5px;">
                        {{ activeTarget.http_method || 'GET' }}
                    </el-tag>
                    <span style="font-size: 15.5px; font-weight: 700; color: #0f172a;">{{ activeTarget.name
                        }}</span>
                    <el-tag size="small" :type="getGroupTagType(activeTarget.group_name)" effect="light"
                        style="font-weight: 600;">
                        {{ activeTarget.group_name || '生产环境' }}
                    </el-tag>
                    <span v-if="activeTarget.current_status === 'CIRCUIT_BROKEN'"
                        class="status-badge circuit-broken" style="font-size: 11px;">
                        <i class="fa-solid fa-ban" style="margin-right: 3px;"></i>熔断挂起
                    </span>
                    <span v-else :class="getStatusBadgeClass(activeTarget.current_status)"
                        style="font-size: 11px;">
                        <i :class="getStatusIcon(activeTarget.current_status)" style="margin-right: 3px;"></i>
                        {{ activeTarget.current_status || '待探测' }}
                    </span>
                </div>
                <div style="font-size: 12px; color: #64748b;">
                    <i class="fa-solid fa-clock" style="margin-right: 4px; color: #8b5cf6;"></i>巡检周期: 
                    <span v-if="activeTarget.is_active === false" style="color: #ef4444; font-weight: 600;">已关闭自动探测 (手动/前置触发)</span>
                    <span v-else>每 {{ formatIntervalDisplay(activeTarget.cron_interval_minutes, true) }} 自动巡检</span>
                </div>
            </div>
            <div
                style="display: flex; gap: 16px; font-size: 12px; color: #334155; background: #ffffff; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0; flex-wrap: wrap; align-items: center;">
                <div>
                    <span style="color: #64748b;">所属宿主机:</span>
                    <b style="color: #0f172a; margin-left: 4px;"><i class="fa-solid fa-server"
                            style="color: #10b981; margin-right: 3px;"></i>{{ activeTarget.machine_name ||
                        (activeTarget.host + ':' + activeTarget.port) }}</b>
                </div>
                <div
                    style="flex: 1; min-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <span style="color: #64748b;">完整请求目标:</span>
                    <span class="code-pill" style="margin-left: 4px; font-size: 11.5px;">{{
                        activeTarget.full_url || (activeTarget.host + ':' + activeTarget.port +
                        activeTarget.http_path) }}</span>
                </div>
            </div>
        </div>

        <div
            style="background: #ffffff; padding: 18px 20px; border-radius: 8px; border: 1px solid #dbe5f0; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(37,99,235,0.03);">
            <div
                style="font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; justify-content: space-between; color: #0f172a;">
                <span><i class="fa-solid fa-chart-line"
                        style="color: #2563eb; margin-right: 6px;"></i>该接口历史响应延迟趋势 (近24小时)</span>
                <span style="font-size: 12px; color: #64748b; font-weight: normal;">专属时序点位</span>
            </div>
            <div id="chartContainer"></div>
        </div>

        <div
            style="font-weight: 600; font-size: 14px; margin-bottom: 10px; color: #0f172a; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <i class="fa-solid fa-clock-rotate-left"
                    style="color: #2563eb; margin-right: 6px;"></i>该接口专属探测日志 (展开行查看契约变更明细与报文现场)
            </div>
            <el-tag size="small" type="info" effect="plain">{{ historyList.length }} 条专属流水</el-tag>
        </div>
        <el-table :data="historyList" v-loading="loadingHistory" style="width: 100%" size="small"
            empty-text="当前接口暂无探测历史，可点击列表【拨测】立即生成探测流水">
            <el-table-column type="expand">
                <template #default="{ row }">
                    <div
                        style="padding: 12px 18px; background: #f4f8fd; border-radius: 6px; border: 1px solid #dbe5f0;">
                        <div v-if="row.schema_diff_detail && row.schema_diff_detail.length"
                            style="margin-bottom: 8px;">
                            <div style="font-weight: 600; color: #dc2626; margin-bottom: 6px;">⚠️ 捕获的破坏性结构变更：
                            </div>
                            <div v-for="(err, idx) in row.schema_diff_detail" :key="idx"
                                style="font-size: 12px; color: #b91c1c; margin-left: 10px;">
                                • <b>[{{ err.field }}]</b>: {{ err.message }}
                            </div>
                        </div>
                        <div v-else style="color: #059669; font-size: 12px; margin-bottom: 6px;">✓ Schema
                            结构完全符合预期。</div>
                        <div v-if="row.raw_response_snippet" style="font-size: 11px; color: var(--text-muted);">
                            <div>原始响应现场快照：</div>
                            <pre
                                style="margin-top: 4px; padding: 6px; background: #ffffff; border: 1px solid #dbe5f0; border-radius: 4px; color: #1e293b; overflow-x: auto;">{{ row.raw_response_snippet }}</pre>
                        </div>

                        <!-- DB 环境准备与销毁流水卡片 -->
                        <div v-if="row.db_fixture_summary" style="margin-top: 10px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 6px;">
                                <div style="font-weight: 600; font-size: 12px; color: #1e293b; display: flex; align-items: center; gap: 6px;">
                                    <i class="fa-solid fa-database" style="color: #3b82f6;"></i>
                                    <span>环境准备 (DB Fixture) 现场流水：</span>
                                    <el-tag size="small" :type="row.db_fixture_summary.success ? 'success' : 'danger'">
                                        {{ row.db_fixture_summary.success ? '准备成功' : '准备失败' }}
                                    </el-tag>
                                    <el-tag v-if="row.db_fixture_summary.cleaned_up" size="small" type="info">已逆序物理销毁</el-tag>
                                </div>
                                <div v-if="row.db_fixture_summary.cleanup_message" style="font-size: 11px; color: #64748b;">
                                    {{ row.db_fixture_summary.cleanup_message }}
                                </div>
                            </div>
                            <div v-if="row.db_fixture_summary.error" style="color: #ef4444; font-size: 11.5px; margin-bottom: 6px;">
                                <i class="fa-solid fa-triangle-exclamation" style="margin-right: 4px;"></i>{{ row.db_fixture_summary.error }}
                            </div>
                            <div v-if="row.db_fixture_summary.tables && row.db_fixture_summary.tables.length > 0">
                                <div v-for="(tItem, tIdx) in row.db_fixture_summary.tables" :key="tIdx"
                                    style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 10px; margin-top: 6px; font-size: 11.5px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span>
                                            <strong style="color: #0f172a;">{{ tIdx + 1 }}. {{ tItem.table_name }}</strong>
                                            <span style="color: #64748b; margin-left: 6px;">(主键: {{ tItem.primary_key_column }} = {{ tItem.primary_key_value || '-' }})</span>
                                        </span>
                                        <span :style="{ color: tItem.is_success ? '#16a34a' : '#dc2626', fontWeight: 600 }">
                                            {{ tItem.is_success ? (tItem.cleanup_done ? '✓ 写入成功并已销毁' : '✓ 写入成功') : '✗ 写入失败' }}
                                        </span>
                                    </div>
                                    <pre v-if="tItem.inserted_record" style="margin: 4px 0 0 0; padding: 4px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 3px; max-height: 100px; overflow-y: auto; font-size: 10.5px;">{{ JSON.stringify(tItem.inserted_record, null, 2) }}</pre>
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="probed_at" label="检测时间" width="160">
                <template #default="{ row }">{{ formatTime(row.probed_at) }}</template>
            </el-table-column>
            <el-table-column label="TCP 握手" width="105" align="center">
                <template #default="{ row }">
                    <span v-if="row.circuit_broken" style="color: #d97706; font-weight: 500;">熔断挂起</span>
                    <span v-else-if="row.tcp_ok" style="color: #059669; font-weight: 500;">✓ {{
                        row.tcp_latency_ms ? row.tcp_latency_ms + 'ms' : '正常' }}</span>
                    <span v-else style="color: #dc2626; font-weight: 500;">✗ 失败</span>
                </template>
            </el-table-column>
            <el-table-column label="DB 准备" width="115" align="center">
                <template #default="{ row }">
                    <template v-if="row.db_fixture_summary">
                        <el-tag v-if="row.db_fixture_summary.success" type="success" size="small" effect="plain"
                            :title="row.db_fixture_summary.cleanup_message || '前置写入成功，已逆序销毁'">
                            <i class="fa-solid fa-database" style="margin-right: 3px;"></i>已清理
                        </el-tag>
                        <el-tag v-else type="danger" size="small" effect="plain"
                            :title="row.db_fixture_summary.error || '前置写入失败'">
                            <i class="fa-solid fa-triangle-exclamation" style="margin-right: 3px;"></i>准备失败
                        </el-tag>
                    </template>
                    <span v-else style="color: var(--text-muted); font-size: 11px;">未启用</span>
                </template>
            </el-table-column>
            <el-table-column label="HTTP 状态" width="100" align="center">
                <template #default="{ row }">
                    <el-tag v-if="row.http_status_code === 200" type="success" size="small">{{
                        row.http_status_code }} OK</el-tag>
                    <el-tag v-else-if="row.http_status_code" type="danger" size="small">{{ row.http_status_code
                        }}</el-tag>
                    <span v-else style="color: var(--text-muted);">-</span>
                </template>
            </el-table-column>
            <el-table-column label="HTTP 耗时" width="110" align="center">
                <template #default="{ row }">
                    <span v-if="row.http_latency_ms" :class="getLatencyBadgeClass(row.http_latency_ms)">
                        {{ row.http_latency_ms }} ms
                    </span>
                    <span v-else style="color: var(--text-muted); font-size: 12px;">-</span>
                </template>
            </el-table-column>
            <el-table-column label="Schema 状态" width="115" align="center">
                <template #default="{ row }">
                    <el-tag v-if="row.schema_matched" type="success" size="small">完全匹配</el-tag>
                    <el-tag v-else type="danger" size="small">破坏性突变</el-tag>
                </template>
            </el-table-column>
            <el-table-column label="综合状态" width="100" align="center">
                <template #default="{ row }">
                    <span v-if="row.is_healthy" style="color: #059669; font-weight: 600;">HEALTHY</span>
                    <span v-else style="color: #dc2626; font-weight: 600;">FAIL</span>
                </template>
            </el-table-column>
        </el-table>
    </div>
</el-drawer>
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
