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
<!--                              直接注释掉这个刷新，这个位置的刷新和top的重复了，但没有去修改对应的函数，只是在前端不显示-->
<!--                                <el-button size="small" type="primary" plain @click="fetchData">-->
<!--                                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px;"></i>刷新-->
<!--                                </el-button>-->
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
                                    <el-tag v-else-if="!row.schema_configured" type="info" effect="plain"
                                        size="small">未配置</el-tag>
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

<!-- ================= 领域弹窗/抽屉 ================= -->
<el-dialog v-model="apiDialogVisible"
    :title="editingApiId ? '接口探测配置工作台 (Postman 风格)' : '新建接口探测 (Postman 风格工作台)'" width="980px" top="4vh"
    class="postman-dialog" destroy-on-close>
    <!-- 基础元数据设置区 -->
    <div
        style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px;">
        <el-row :gutter="16">
            <el-col :span="10">
                <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px;">
                    <span style="color: #ef4444; margin-right: 2px;">*</span>宿主机器节点 (Host Node)
                </div>
                <el-select v-model="apiForm.machine_id" placeholder="选择归属机器节点" style="width: 100%;">
                    <el-option v-for="m in machineList" :key="m.id"
                        :label="m.name + ' (' + (m.environment_name || '未指定') + ' | ' + m.host + ':' + m.port + ')'"
                        :value="m.id"></el-option>
                </el-select>
            </el-col>
            <el-col :span="14">
                <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px;">
                    <span style="color: #ef4444; margin-right: 2px;">*</span>接口业务名称 (API Name)
                </div>
                <el-input v-model="apiForm.name" placeholder="例如: 用户鉴权服务 / 实时订单聚合接口"></el-input>
            </el-col>
        </el-row>
        <el-row :gutter="16" style="margin-top: 10px;">
            <el-col :span="24">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 12px; font-weight: 600; color: #475569; display: flex; align-items: center; gap: 6px;">
                        <i class="fa-solid fa-clock-rotate-left" style="color: #2563eb;"></i>
                        <span>定时自动探测调度</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 11.5px; color: #64748b;">{{ apiForm.is_active ? '已启用自动探测' : '已关闭自动探测' }}</span>
                        <el-switch v-model="apiForm.is_active" inline-prompt active-text="开" inactive-text="关"
                            style="--el-switch-on-color: #10b981;"></el-switch>
                    </div>
                </div>

                <!-- 启用状态下：数值 + 单位下拉 + 快捷胶囊 -->
                <div v-if="apiForm.is_active">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <el-input-number v-model="apiIntervalValue" :min="1" :max="999999" controls-position="right"
                            style="width: 140px;" placeholder="周期数值"></el-input-number>
                        <el-select v-model="apiIntervalUnit" style="width: 115px;">
                            <el-option label="分钟 (m)" value="minutes"></el-option>
                            <el-option label="小时 (h)" value="hours"></el-option>
                            <el-option label="天 (d)" value="days"></el-option>
                        </el-select>
                        <span style="font-size: 11.5px; color: #64748b; margin-left: 2px;">
                            <span v-if="apiIntervalUnit === 'days'">折合 {{ apiIntervalValue * 1440 }} 分钟</span>
                            <span v-else-if="apiIntervalUnit === 'hours'">折合 {{ apiIntervalValue * 60 }} 分钟</span>
                            <span v-else>{{ apiIntervalValue }} 分钟</span>
                        </span>
                    </div>
                    <!-- 常用快捷周期预设 -->
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 6px; flex-wrap: wrap;">
                        <span style="font-size: 11px; color: #94a3b8;">快捷预设:</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(5, 'minutes')" style="font-size: 11px; padding: 0;">5m</el-button>
                        <span style="color: #cbd5e1; font-size: 10px;">|</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(15, 'minutes')" style="font-size: 11px; padding: 0;">15m</el-button>
                        <span style="color: #cbd5e1; font-size: 10px;">|</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(1, 'hours')" style="font-size: 11px; padding: 0;">1h</el-button>
                        <span style="color: #cbd5e1; font-size: 10px;">|</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(12, 'hours')" style="font-size: 11px; padding: 0;">12h</el-button>
                        <span style="color: #cbd5e1; font-size: 10px;">|</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(1, 'days')" style="font-size: 11px; padding: 0;">1天</el-button>
                        <span style="color: #cbd5e1; font-size: 10px;">|</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(7, 'days')" style="font-size: 11px; padding: 0;">7天</el-button>
                        <span style="color: #cbd5e1; font-size: 10px;">|</span>
                        <el-button size="small" link type="primary" @click="setQuickInterval(30, 'days')" style="font-size: 11px; padding: 0; font-weight: 700; color: #7c3aed;">30天 (长效)</el-button>
                    </div>
                </div>

                <!-- 停用状态下：提示文本 -->
                <div v-else style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 8px 10px; font-size: 11.5px; color: #64748b; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-circle-pause" style="color: #94a3b8; font-size: 13px;"></i>
                    <span>已关闭后台定时自动探测。该接口仅支持在控制台手动点击【拨测】或作为前置调用时触发。</span>
                </div>
            </el-col>
        </el-row>
    </div>

    <!-- 宿主机器与环境联动信息条 (支持环境变量查看与实时调用) -->
    <div
        style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; font-size: 12px; border: 1px solid #e2e8f0; flex-wrap: wrap; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="font-weight: 600; color: #475569;">
                <i class="fa-solid fa-server" style="color: #0284c7; margin-right: 4px;"></i>宿主机器:
            </span>
            <span style="font-weight: 600; color: #0f172a;">
                {{ selectedMachineDisplayName }}
            </span>
            <span style="color: #cbd5e1; margin: 0 4px;">|</span>
            <span style="font-weight: 600; color: #475569;">
                <i class="fa-solid fa-layer-group" style="color: #10b981; margin-right: 4px;"></i>所属环境:
            </span>
            <el-tag size="small" type="success" effect="plain" style="font-weight: 600;">
                {{ currentMachineEnvironment.name || '默认环境' }}
            </el-tag>

            <span style="color: #cbd5e1; margin: 0 4px;">|</span>
            <el-button size="small" type="warning" plain @click="openEnvDialog"
                       style="border-radius: 14px; padding: 2px 10px; height: 24px;">
              <i class="fa-solid fa-sliders" style="margin-right: 4px;"></i>环境变量 ({{ Object.keys(currentMachineEnvironment.variables || {}).length }})
            </el-button>
            <span style="color: #64748b;">
                机器默认地址:
                <code
                    style="background: #e2e8f0; color: #0284c7; padding: 2px 6px; border-radius: 4px; font-family: monospace;">{{ selectedMachineBaseUrl }}</code>
            </span>
            <el-tooltip content="点击将当前宿主机器的默认基准地址同步填入下方输入框" placement="top">
                <el-button size="small" link type="primary" @click="resetBaseUrlToMachine">
                    <i class="fa-solid fa-rotate-left" style="margin-right: 2px;"></i>恢复机器地址
                </el-button>
            </el-tooltip>
            <el-tooltip content="查看/编辑宿主机器所属环境的变量池, 节点配置中可用 {{变量名}} 宏直接引用" placement="top">
            </el-tooltip>
        </div>
        <div style="color: #64748b; font-size: 11.5px; display: flex; align-items: center; gap: 4px;">
            <i class="fa-solid fa-circle-info" style="color: #0284c7;"></i>
            <span>在 URL/Header/Body 中均可直接使用 <code v-pre>{{变量名}}</code> 引用环境变量</span>
        </div>
    </div>

    <!-- Postman 顶部 URL 请求栏 -->
    <div class="pm-url-bar">
        <el-select v-model="apiForm.http_method" class="pm-method-select"
            :class="'pm-method-' + apiForm.http_method.toLowerCase()">
            <el-option label="GET" value="GET" class="pm-method-get"></el-option>
            <el-option label="POST" value="POST" class="pm-method-post"></el-option>
            <el-option label="PUT" value="PUT" class="pm-method-put"></el-option>
            <el-option label="DELETE" value="DELETE" class="pm-method-delete"></el-option>
            <el-option label="PATCH" value="PATCH" class="pm-method-patch"></el-option>
        </el-select>
        <div class="pm-baseurl-wrapper" title="当前接口的前置服务基准地址 (支持 http:// 或 https://、域名或IP及端口)">
            <el-input v-model="apiForm.base_url" class="pm-baseurl-input"
                placeholder="http://host:port 或 https://api.domain.com" clearable>
                <template #prefix>
                    <i class="fa-solid fa-globe"
                        style="color: #64748b; font-size: 12px; margin-right: 2px;"></i>
                </template>
            </el-input>
        </div>
        <el-input v-model="apiForm.http_path" class="pm-path-input"
            placeholder="/api/v1/resource?query=val (支持直接粘贴完整URL)" @input="onPathInput">
        </el-input>
        <el-button type="primary" class="pm-send-btn" @click="handleTestRunApi" :loading="apiTestRunning">
            <i class="fa-solid fa-paper-plane"></i>
            <span>发送调试</span>
        </el-button>
    </div>

    <!-- Postman 核心配置工作区 (Tabs) -->
    <el-tabs v-model="apiActiveTab" class="pm-tabs">
        <!-- 1. Params 标签页 -->
        <el-tab-pane label="Params" name="params">
            <div
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 12px; color: #64748b;">
                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px; color: #3b82f6;"></i>参数与上方
                    URL Query 参数已双向实时同步 (勾选启用/禁用)
                </span>
                <el-button size="small" type="primary" plain @click="addParamRow">
                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加参数
                </el-button>
            </div>
            <table class="pm-kv-table">
                <thead>
                    <tr>
                        <th style="width: 45px; text-align: center;">启用</th>
                        <th style="width: 28%;">参数名 (Key)</th>
                        <th style="width: 36%;">参数值 (Value 支持宏)</th>
                        <th>参数说明 (Description)</th>
                        <th style="width: 50px; text-align: center;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(item, idx) in apiParamsList" :key="idx">
                        <td style="text-align: center;">
                            <el-checkbox v-model="item.enabled"></el-checkbox>
                        </td>
                        <td>
                            <el-input v-model="item.key" placeholder="参数名 如 page" size="small"></el-input>
                        </td>
                        <td>
                            <el-input v-model="item.value" placeholder="参数值 如 1 或 {{$timestamp}}"
                                size="small"></el-input>
                        </td>
                        <td>
                            <el-input v-model="item.description" placeholder="用途说明" size="small"></el-input>
                        </td>
                        <td style="text-align: center;">
                            <span class="pm-kv-action-btn" title="删除此行" @click="removeParamRow(idx)">
                                <i class="fa-solid fa-trash-can"></i>
                            </span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </el-tab-pane>

        <!-- 2. Headers 标签页 (Postman 风格: 系统默认自动填充 + 用户自定义扩展) -->
        <el-tab-pane label="Headers" name="headers">
            <div class="pm-headers-toolbar">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <el-button size="small" :type="showDefaultHeaders ? 'primary' : 'default'" text class="pm-hidden-headers-btn" @click="showDefaultHeaders = !showDefaultHeaders">
                        <i :class="showDefaultHeaders ? 'fa-solid fa-eye-slash' : 'fa-regular fa-eye'" style="margin-right: 5px;"></i>
                        <span v-if="showDefaultHeaders">隐藏系统默认请求头 ({{ activeDefaultHeadersCount }})</span>
                        <span v-else>{{ activeDefaultHeadersCount }} 个系统默认请求头 (已自动携带)</span>
                    </el-button>
                    <span style="font-size: 11px; color: #94a3b8;">
                        <i class="fa-solid fa-circle-info" style="margin-right: 3px;"></i>发包时系统将自动注入默认请求头，输入同名自定义请求头可直接覆盖
                    </span>
                </div>
                <el-button size="small" type="primary" plain @click="addHeaderRow">
                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加自定义请求头
                </el-button>
            </div>

            <!-- 默认请求头折叠时的 Postman 风格快捷提醒条 -->
            <div v-if="!showDefaultHeaders" class="pm-hidden-headers-tip" @click="showDefaultHeaders = true">
                <i class="fa-regular fa-eye" style="margin-right: 6px; color: #2563eb;"></i>
                <span>已自动启用 <strong>{{ activeDefaultHeadersCount }}</strong> 个 Postman 规范默认请求头 (User-Agent, Accept, Connection, Content-Type 等)</span>
                <span class="pm-tip-link">点击展开查看/修改</span>
            </div>

            <table class="pm-kv-table">
                <thead>
                    <tr>
                        <th style="width: 45px; text-align: center;">启用</th>
                        <th style="width: 32%;">请求头键 (Header Key)</th>
                        <th style="width: 36%;">请求头值 (Header Value)</th>
                        <th>说明 (Description)</th>
                        <th style="width: 50px; text-align: center;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Postman 系统默认请求头列表 (可取消勾选/同名自动覆盖/动态调整) -->
                    <tr v-if="showDefaultHeaders" v-for="(item, idx) in systemDefaultHeaders" :key="'sys_' + idx"
                        class="pm-header-row-sys" :class="{ 'pm-header-overridden': isHeaderOverridden(item.key) }">
                        <td style="text-align: center;">
                            <el-checkbox v-model="item.enabled" :disabled="isHeaderOverridden(item.key)"></el-checkbox>
                        </td>
                        <td>
                            <span :style="isHeaderOverridden(item.key) ? 'text-decoration: line-through; opacity: 0.6;' : 'font-weight: 600; color: #334155; font-family: monospace; font-size: 12.5px;'">
                                {{ item.key }}
                            </span>
                            <span class="pm-auto-tag">自动生成</span>
                            <el-tag v-if="isHeaderOverridden(item.key)" size="small" type="warning" effect="plain" class="pm-override-tag">
                                <i class="fa-solid fa-arrow-down" style="margin-right: 3px;"></i>已被自定义覆盖
                            </el-tag>
                        </td>
                        <td>
                            <span :style="isHeaderOverridden(item.key) ? 'text-decoration: line-through; opacity: 0.6;' : 'color: #0f172a; font-family: monospace; font-size: 12.5px;'">
                                {{ item.value }}
                            </span>
                        </td>
                        <td>
                            <span style="font-size: 12px; color: #64748b;">{{ item.description }}</span>
                        </td>
                        <td style="text-align: center;">
                            <i class="fa-solid fa-lock" style="color: #94a3b8; font-size: 12px;" title="系统默认预填请求头"></i>
                        </td>
                    </tr>

                    <!-- 用户自定义请求头列表 -->
                    <tr v-for="(item, idx) in apiHeadersList" :key="'custom_' + idx">
                        <td style="text-align: center;">
                            <el-checkbox v-model="item.enabled"></el-checkbox>
                        </td>
                        <td>
                            <el-input v-model="item.key" placeholder="如 Authorization / X-Custom-Header" size="small"></el-input>
                        </td>
                        <td>
                            <el-input v-model="item.value" placeholder="请求头内容或变量引用" size="small"></el-input>
                        </td>
                        <td>
                            <el-input v-model="item.description" placeholder="用途说明" size="small"></el-input>
                        </td>
                        <td style="text-align: center;">
                            <span class="pm-kv-action-btn" title="删除此行" @click="removeHeaderRow(idx)">
                                <i class="fa-solid fa-trash-can"></i>
                            </span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </el-tab-pane>

        <!-- 3. Body 标签页 -->
        <el-tab-pane label="Body" name="body">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
                <el-radio-group v-model="apiBodyType" size="small">
                    <el-radio-button label="none">none (无 Body)</el-radio-button>
                    <el-radio-button label="json">raw (JSON)</el-radio-button>
                    <el-radio-button label="form">x-www-form-urlencoded</el-radio-button>
                </el-radio-group>
                <div style="flex: 1;"></div>
                <div v-if="apiBodyType === 'json'" style="display: flex; gap: 6px;">
                    <el-button size="small" type="primary" plain @click="formatBodyJson">
                        <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>格式化 JSON
                    </el-button>
                    <el-button size="small" plain @click="minifyBodyJson" title="压缩为紧凑单行格式">
                        <i class="fa-solid fa-compress" style="margin-right: 4px;"></i>压缩
                    </el-button>
                    <el-button size="small" plain @click="clearBodyJson" title="清空请求体">
                        <i class="fa-solid fa-trash-can" style="margin-right: 4px;"></i>清空
                    </el-button>
                </div>
            </div>

            <div v-if="apiBodyType === 'none'"
                style="padding: 24px; text-align: center; color: #94a3b8; font-size: 13px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px;">
                <i class="fa-solid fa-ban" style="margin-right: 6px;"></i>该请求不携带任何 Body 请求体 (适用 GET/DELETE 等)
            </div>

            <div v-else-if="apiBodyType === 'json'" class="pm-code-box">
                <el-input v-model="apiBodyText" type="textarea" :rows="7"
                    placeholder="{\n  &quot;userId&quot;: 1001,\n  &quot;action&quot;: &quot;ping&quot;,\n  &quot;traceId&quot;: &quot;{{$uuid}}&quot;,\n  &quot;timestamp&quot;: &quot;{{$timestamp}}&quot;\n}"></el-input>
            </div>

            <div v-else-if="apiBodyType === 'form'" class="pm-code-box">
                <el-input v-model="apiBodyText" type="textarea" :rows="6"
                    placeholder="key1=value1&amp;key2={{$timestamp}}"></el-input>
            </div>
        </el-tab-pane>

        <!-- 4. 鉴权与预设宏 标签页 -->
        <el-tab-pane label="Auth" name="auth">
            <div style="margin-bottom: 14px;">
                <span
                    style="font-size: 12px; font-weight: 600; color: #475569; margin-right: 12px;">鉴权认证类型:</span>
                <el-radio-group v-model="apiAuthType" size="small">
                    <el-radio-button label="none">无鉴权 (No Auth)</el-radio-button>
                    <el-radio-button label="bearer">Bearer Token</el-radio-button>
                    <el-radio-button label="basic">Basic Auth</el-radio-button>
                    <el-radio-button label="custom_header">自定义请求头 (Custom Header)</el-radio-button>
                </el-radio-group>
            </div>

            <!-- Bearer Token 配置 -->
            <div v-if="apiAuthType === 'bearer'"
                style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    Bearer Token 令牌值
                    <span style="font-size: 11px; font-weight: normal; color: #64748b; margin-left: 6px;">支持静态
                        Token 或模板宏 (如 <code v-pre>{{TOKEN}}</code>)</span>
                </div>
                <el-input v-model="apiAuthConfig.token" placeholder="ey..." size="small"></el-input>
            </div>

            <!-- Basic Auth 配置 -->
            <div v-if="apiAuthType === 'basic'"
                style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                <el-row :gutter="12">
                    <el-col :span="12">
                        <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">用户名
                            (Username)</div>
                        <el-input v-model="apiAuthConfig.username" placeholder="admin" size="small"></el-input>
                    </el-col>
                    <el-col :span="12">
                        <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">密码
                            (Password)</div>
                        <el-input v-model="apiAuthConfig.password" type="password" show-password
                            placeholder="••••••" size="small"></el-input>
                    </el-col>
                </el-row>
            </div>

            <!-- Custom Header 配置 -->
            <div v-if="apiAuthType === 'custom_header'"
                style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                <el-row :gutter="12">
                    <el-col :span="8">
                        <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">自定义
                            Header 键名</div>
                        <el-input v-model="apiAuthConfig.header_key" placeholder="如 X-API-Token / X-Sign"
                            size="small"></el-input>
                    </el-col>
                    <el-col :span="16">
                        <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">自定义
                            Header 键值</div>
                        <el-input v-model="apiAuthConfig.header_value" placeholder="Header 对应值"
                            size="small"></el-input>
                    </el-col>
                </el-row>
            </div>

        </el-tab-pane>

        <!-- 5. 前置操作 (Pre-request) 标签页 -->
        <el-tab-pane label="前置操作" name="pre_actions">
            <div class="pm-preset-bar">
                <span style="font-size: 12px; color: #64748b; font-weight: 600;">快速预设:</span>
                <span class="pm-preset-tag" @click="applyPreActionPreset('js_script')"><i class="fa-brands fa-js" style="color: #f59e0b; margin-right: 3px;"></i>+ Postman JS 脚本</span>
                <span class="pm-preset-tag" @click="applyPreActionPreset('script')"><i class="fa-brands fa-python" style="color: #3b82f6; margin-right: 3px;"></i>+ Python 脚本</span>
                <div style="flex: 1;"></div>
                <el-button size="small" type="primary" plain @click="addPreActionRow">
                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加前置操作
                </el-button>
            </div>

            <table class="pm-kv-table">
                <thead>
                    <tr>
                        <th style="width: 45px; text-align: center;">启用</th>
                        <th style="width: 175px;">操作类型 (Action Type)</th>
                        <th style="width: 20%;">目标键名 (Key)</th>
                        <th style="width: 36%;">值 / 表达式 / 脚本代码 (Value 支持宏与 JS)</th>
                        <th>用途说明 (Description)</th>
                        <th style="width: 50px; text-align: center;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-if="apiPreActionsList.length === 0">
                        <td colspan="6" style="text-align: center; color: #94a3b8; padding: 20px;">
                            <i class="fa-solid fa-bolt"
                                style="margin-right: 6px; color: #cbd5e1;"></i>暂无前置操作。可点击上方【添加前置操作】或点击快速预设注入变量与请求头
                        </td>
                    </tr>
                    <tr v-for="(item, idx) in apiPreActionsList" :key="idx">
                        <td style="text-align: center;">
                            <el-checkbox v-model="item.enabled"></el-checkbox>
                        </td>
                        <td>
                            <el-select v-model="item.type" size="small" style="width: 100%;">
                                <el-option label="设置临时变量 (Set Var)" value="set_variable"></el-option>
                                <el-option label="注入请求头 (Inject Header)" value="inject_header"></el-option>
                                <el-option label="注入URL参数 (Inject Param)" value="inject_param"></el-option>
                                <el-option label="JavaScript 脚本 (Postman JS)" value="javascript"></el-option>
                                <el-option label="Python 脚本 (Python Script)" value="custom_script"></el-option>
                            </el-select>
                        </td>
                        <td>
                            <el-input v-if="item.type !== 'custom_script' && item.type !== 'javascript'" v-model="item.key"
                                placeholder="如 sign / X-Trace-Id" size="small"></el-input>
                            <span v-else-if="item.type === 'javascript'" style="font-size: 11.5px; color: #d97706; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                                <i class="fa-brands fa-js"></i>Postman JS 沙箱
                            </span>
                            <span v-else style="font-size: 11.5px; color: #2563eb; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                                <i class="fa-brands fa-python"></i>Python 执行器
                            </span>
                        </td>
                        <td>
                            <el-input v-if="item.type !== 'custom_script' && item.type !== 'javascript'" v-model="item.value"
                                placeholder="如 {{$timestamp}} 或常量" size="small"></el-input>
                            <el-input v-else-if="item.type === 'javascript'" v-model="item.value" type="textarea" :rows="3"
                                placeholder="const jsrsasign = require('jsrsasign');&#10;const CryptoJS = require('crypto-js');&#10;pm.variables.set('token', 'TOKEN_' + Date.now());&#10;pm.request.headers.add({ key: 'X-Sign', value: '...' });"
                                size="small"></el-input>
                            <el-input v-else v-model="item.value" type="textarea" :rows="2"
                                placeholder="variables['sign'] = 'val_' + str(int(time.time()))"
                                size="small"></el-input>
                        </td>
                        <td>
                            <el-input v-model="item.description" placeholder="说明" size="small"></el-input>
                        </td>
                        <td style="text-align: center;">
                            <span class="pm-kv-action-btn" title="删除此行" @click="removePreActionRow(idx)">
                                <i class="fa-solid fa-trash-can"></i>
                            </span>
                        </td>
                    </tr>
                </tbody>
            </table>

            <div
                style="margin-top: 10px; font-size: 11.5px; color: #64748b; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                <i class="fa-solid fa-circle-info" style="color: #2563eb;"></i>
                <span>前置操作定义的变量可在 URL 路径、Params、Headers、Body 及后续断言中通过 <code v-pre>{{变量名}}</code> 直接调用引用。</span>
                <span style="color: #d97706; margin-left: 8px; font-weight: 500;"><i class="fa-brands fa-js" style="margin-right: 3px;"></i>支持 Postman JS: <code>require('jsrsasign')</code>、<code>require('crypto-js')</code>、<code>Buffer</code>、<code>pm.variables.set</code></span>
            </div>
        </el-tab-pane>

        <!-- 6. 后置操作 (Post-response / 断言校验) 标签页 -->
        <el-tab-pane label="后置操作" name="post_actions">
            <div class="pm-preset-bar">
                <span style="font-size: 12px; color: #64748b; font-weight: 600;">快速断言预设:</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('status_200')">+ 状态码等于 200</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('status_2xx')">+ 状态码在 2xx 范围</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('latency_1000')">+ 耗时小于 1000ms</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('json_code')">+ JSON code 等于
                    200</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('contains_ok')">+ 文本包含 OK</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('extract_var')">+ 提取响应变量</span>
                <span class="pm-preset-tag" @click="applyPostActionPreset('js_test')"><i class="fa-brands fa-js" style="color: #f59e0b; margin-right: 3px;"></i>+ JS 脚本断言 (Postman Tests)</span>
                <div style="flex: 1;"></div>
                <el-button size="small" type="primary" plain @click="addPostActionRow">
                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加断言/操作
                </el-button>
            </div>

            <table class="pm-kv-table">
                <thead>
                    <tr>
                        <th style="width: 45px; text-align: center;">启用</th>
                        <th style="width: 22%;">断言名称 / 描述</th>
                        <th style="width: 175px;">类型 (Type)</th>
                        <th style="width: 24%;">提取表达式 / 脚本代码</th>
                        <th style="width: 115px;">运算符</th>
                        <th style="width: 18%;">期望值 / 变量名</th>
                        <th style="width: 50px; text-align: center;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-if="apiPostActionsList.length === 0">
                        <td colspan="7" style="text-align: center; color: #94a3b8; padding: 20px;">
                            <i class="fa-solid fa-flask"
                                style="margin-right: 6px; color: #cbd5e1;"></i>暂无后置操作断言。可点击上方【添加断言/操作】或快捷预设注入
                            HTTP 状态码、耗时、JSON 字段等校验规则
                        </td>
                    </tr>
                    <tr v-for="(item, idx) in apiPostActionsList" :key="idx">
                        <td style="text-align: center;">
                            <el-checkbox v-model="item.enabled"></el-checkbox>
                        </td>
                        <td>
                            <el-input v-model="item.name" placeholder="如 验证响应成功" size="small"></el-input>
                        </td>
                        <td>
                            <el-select v-model="item.type" size="small" style="width: 100%;"
                                @change="onPostActionTypeChange(item)">
                                <el-option label="HTTP 状态码断言" value="assert_status_code"></el-option>
                                <el-option label="响应耗时断言" value="assert_latency"></el-option>
                                <el-option label="JSON 字段断言" value="assert_json_path"></el-option>
                                <el-option label="响应头校验" value="assert_header"></el-option>
                                <el-option label="文本内容包含" value="assert_body_contains"></el-option>
                                <el-option label="从响应提取变量" value="extract_variable"></el-option>
                                <el-option label="JavaScript 脚本 / 断言 (Postman Tests)" value="javascript"></el-option>
                            </el-select>
                        </td>

                        <!-- 当类型为 javascript 脚本时，占据宽敞的 3 列并使用代码编辑器字体 -->
                        <td v-if="item.type === 'javascript'" colspan="3">
                            <div style="margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 11px; font-weight: 600; color: #d97706; display: inline-flex; align-items: center; gap: 4px;">
                                    <i class="fa-brands fa-js"></i>Postman Tests / Apifox 后置 JS 脚本沙箱
                                </span>
                                <span style="font-size: 10.5px; color: #94a3b8;">支持 pm.response.json()、pm.environment.set()、pm.test() 等</span>
                            </div>
                            <el-input v-model="item.value" type="textarea" :rows="4"
                                style="font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; line-height: 1.5;"
                                placeholder="const res = pm.response.json();&#10;if (res.code === 0 && res.data) {&#10;    pm.environment.set('token', res.data.accessToken);&#10;}&#10;pm.test('Status is 200', function () { pm.response.to.have.status(200); });"
                                size="small"></el-input>
                        </td>

                        <!-- 其它普通断言规则显示 3 列 -->
                        <template v-else>
                            <td>
                                <el-input
                                    v-if="['assert_json_path', 'assert_header', 'extract_variable'].includes(item.type)"
                                    v-model="item.expression" placeholder="如 code 或 data.id"
                                    size="small"></el-input>
                                <span v-else style="font-size: 11.5px; color: #94a3b8;">自动比对</span>
                            </td>
                            <td>
                                <el-select v-if="item.type !== 'extract_variable'" v-model="item.operator"
                                    size="small" style="width: 100%;">
                                    <el-option label="等于 (==)" value="equals"></el-option>
                                    <el-option label="不等于 (!=)" value="not_equals"></el-option>
                                    <el-option v-if="item.type === 'assert_status_code'" label="2xx 范围"
                                        value="in_2xx"></el-option>
                                    <el-option v-if="['assert_latency', 'assert_status_code'].includes(item.type)"
                                        label="小于 (<=)" value="less_than"></el-option>
                                    <el-option v-if="['assert_latency', 'assert_status_code'].includes(item.type)"
                                        label="大于 (>)" value="greater_than"></el-option>
                                    <el-option
                                        v-if="['assert_json_path', 'assert_header', 'assert_body_contains'].includes(item.type)"
                                        label="包含 (contains)" value="contains"></el-option>
                                    <el-option v-if="item.type === 'assert_json_path'" label="非空校验"
                                        value="not_empty"></el-option>
                                </el-select>
                                <span v-else
                                    style="font-size: 11.5px; color: #0284c7; font-weight: 600;">提取存储</span>
                            </td>
                            <td>
                                <el-input v-if="item.operator !== 'in_2xx' && item.operator !== 'not_empty'"
                                    v-model="item.target_value"
                                    :placeholder="item.type === 'extract_variable' ? '存入变量名 如 token' : '期望值 如 200'"
                                    size="small"></el-input>
                                <span v-else style="font-size: 11.5px; color: #94a3b8;">无需输入期望值</span>
                            </td>
                        </template>
                        <td style="text-align: center;">
                            <span class="pm-kv-action-btn" title="删除此行" @click="removePostActionRow(idx)">
                                <i class="fa-solid fa-trash-can"></i>
                            </span>
                        </td>
                    </tr>
                </tbody>
            </table>

            <div
                style="margin-top: 10px; font-size: 11.5px; color: #64748b; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                <i class="fa-solid fa-circle-check" style="color: #10b981;"></i>
                <span>后置断言将在请求完成后自动逐项校验，任何一项未通过均会判定探测异常并记录在时序流水与告警邮件中。</span>
                <span style="color: #d97706; margin-left: 8px; font-weight: 500;"><i class="fa-brands fa-js" style="margin-right: 3px;"></i>支持 Postman JS: <code>pm.test()</code>、<code>pm.expect()</code>、<code>pm.response.json()</code></span>
            </div>
        </el-tab-pane>

        <!-- 7. 预期 Schema 契约 标签页 -->
        <el-tab-pane label="Schema" name="schema">
            <div
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                <span style="font-size: 12px; color: #64748b;">
                    标准的 JSON Schema 规范 (Draft-7)，拨测时将自动验证真实响应是否破坏此契约
                </span>
                <div style="display: flex; gap: 8px;">
                    <el-button size="small" type="primary" plain @click="formatSchemaJson">
                        <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>格式化 Schema
                    </el-button>
                    <el-button size="small" type="primary" plain @click="inferSchemaFromTestResult"
                        :disabled="!apiTestResult || !apiTestResult.response_data">
                        <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>从当前响应推导
                    </el-button>
                </div>
            </div>
            <div class="pm-code-box">
                <el-input v-model="apiForm.schema_text" type="textarea" :rows="8"
                    placeholder="默认留空（不强校验 Schema）。可在上方发送调试请求后，点击【从当前响应推导】一键自动填入 Draft-7 契约规则"></el-input>
            </div>

            <!-- 备选手动推导折叠卡片 -->
            <div
                style="margin-top: 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px;">
                <div
                    style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <span><i class="fa-solid fa-code" style="margin-right: 4px; color: #64748b;"></i>从自定义 JSON
                        样本辅助推导</span>
                    <div style="display: flex; gap: 6px;">
                        <el-button size="small" text type="primary" @click="formatSampleJson"
                            :disabled="!apiSampleJson || !apiSampleJson.trim()">
                            <i class="fa-solid fa-align-left" style="margin-right: 4px;"></i>格式化样本
                        </el-button>
                        <el-button size="small" text type="primary" @click="handleInferApiSchema"
                            :loading="apiInferring">
                            <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>执行推导
                        </el-button>
                    </div>
                </div>
                <el-input v-model="apiSampleJson" type="textarea" :rows="2"
                    placeholder="在此粘贴外部已有的响应 JSON 文本，点击执行推导即可覆盖上方 Schema 规则"></el-input>
            </div>
        </el-tab-pane>
    </el-tabs>

    <!-- 实时调试响应预览面板 (Live Response Inspector) -->
    <div class="pm-response-card">
        <div class="pm-response-header">
            <div class="pm-response-meta">
                <span style="font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                    <i class="fa-solid fa-terminal" style="color: #2563eb;"></i>
                    调试响应面板 (Response Preview)
                </span>

                <template v-if="apiTestResult">
                    <span class="pm-badge-status"
                        :class="apiTestResult.status_code >= 200 && apiTestResult.status_code < 300 ? 'pm-badge-2xx' : (apiTestResult.status_code >= 400 && apiTestResult.status_code < 500 ? 'pm-badge-4xx' : 'pm-badge-5xx')">
                        {{ apiTestResult.status_code ? apiTestResult.status_code + ' OK' : 'ERR' }}
                    </span>
                    <span class="pm-badge-latency">
                        <i class="fa-regular fa-clock" style="margin-right: 3px;"></i>{{
                        apiTestResult.latency_ms || 0 }} ms
                    </span>
                    <span v-if="apiTestResult.schema_matched" class="pm-badge-schema-ok">
                        <i class="fa-solid fa-circle-check"></i> 契约校验通过
                    </span>
                    <span v-else-if="apiTestResult.schema_matched === false" class="pm-badge-schema-err"
                        :title="apiTestResult.schema_error">
                        <i class="fa-solid fa-circle-exclamation"></i> 契约不匹配
                    </span>
                    <span v-else class="pm-badge-schema-plain" style="color: #94a3b8;">
                        <i class="fa-solid fa-circle-minus"></i> 契约未配置 (可点击「从当前响应推导」生成)
                    </span>
                    <span v-if="apiTestResult.assertions_summary"
                        :class="apiTestResult.assertions_summary.all_passed ? 'pm-badge-schema-ok' : 'pm-badge-schema-err'"
                        :title="'共执行 ' + apiTestResult.assertions_summary.total + ' 项断言，通过 ' + apiTestResult.assertions_summary.passed_count + ' 项'">
                        <i
                            :class="apiTestResult.assertions_summary.all_passed ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i>
                        断言 {{ apiTestResult.assertions_summary.passed_count }}/{{
                        apiTestResult.assertions_summary.total }}
                    </span>
                </template>
            </div>

            <div v-if="apiTestResult" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <el-radio-group v-model="apiResponseTab" size="small">
                    <el-radio-button label="body">响应体 (Response)</el-radio-button>
                    <el-radio-button label="req_body">发送请求体 (Request Body)</el-radio-button>
                    <el-radio-button label="headers">响应头 (Headers)</el-radio-button>
                    <el-radio-button label="assertions">
                        断言结果 ({{ apiTestResult.assertions_result ? apiTestResult.assertions_result.length : 0
                        }})
                    </el-radio-button>
                </el-radio-group>
                <el-button size="small" plain @click="copyResponseBody"
                    :disabled="!apiTestResult.response_data">
                    <i class="fa-regular fa-copy" style="margin-right: 4px;"></i>复制响应
                </el-button>
                <el-button size="small" type="success" plain @click="inferSchemaFromTestResult"
                    :disabled="!apiTestResult.response_data">
                    <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>一键推导 Schema
                </el-button>
            </div>
        </div>

        <!-- 响应内容渲染 -->
        <div v-if="!apiTestResult" class="pm-response-empty">
            <i class="fa-solid fa-paper-plane"
                style="font-size: 24px; color: #cbd5e1; margin-bottom: 8px; display: block;"></i>
            点击上方【发送调试】按钮，发起实时探测并在此查看状态码、延迟、真实响应、后置断言与契约匹配详情
        </div>
        <div v-else>
            <div v-if="apiResponseTab === 'body'">
                <pre class="pm-response-body">{{ JSON.stringify(apiTestResult.response_data, null, 2) }}</pre>
            </div>
            <div v-else-if="apiResponseTab === 'req_body'">
                <div v-if="apiTestResult.rendered_body" style="padding: 10px 0;">
                    <div style="font-size: 11.5px; color: #64748b; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <span><i class="fa-solid fa-circle-check" style="color: #10b981; margin-right: 4px;"></i>经前置操作参数与宏插值解析后的实际发送 Body 请求体:</span>
                        <el-button size="small" text type="primary" @click="copyText(apiTestResult.rendered_body)">
                            <i class="fa-regular fa-copy" style="margin-right: 4px;"></i>复制发送请求体
                        </el-button>
                    </div>
                    <pre class="pm-response-body">{{ formatIfJson(apiTestResult.rendered_body) }}</pre>
                </div>
                <div v-else style="text-align: center; color: #94a3b8; padding: 24px;">
                    <i class="fa-solid fa-ban" style="margin-right: 6px;"></i>该请求未发送任何 Body 请求体 (适用 GET 请求或无 Body 接口)
                </div>
            </div>
            <div v-else-if="apiResponseTab === 'headers'">
                <pre
                    class="pm-response-body">{{ JSON.stringify(apiTestResult.response_headers || {}, null, 2) }}</pre>
            </div>
            <div v-else-if="apiResponseTab === 'assertions'" class="pm-assert-list">
                <div v-if="!apiTestResult.assertions_result || apiTestResult.assertions_result.length === 0"
                    style="text-align: center; color: #94a3b8; padding: 24px;">
                    <i class="fa-solid fa-circle-info" style="margin-right: 6px;"></i>本次请求未配置或未触发后置断言规则
                </div>
                <div v-else>
                    <div v-for="(assertItem, aIdx) in apiTestResult.assertions_result" :key="aIdx"
                        class="pm-assert-item" :class="assertItem.passed ? 'pass' : 'fail'">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span :class="assertItem.passed ? 'pm-assert-tag-pass' : 'pm-assert-tag-fail'">
                                <i :class="assertItem.passed ? 'fa-solid fa-check' : 'fa-solid fa-xmark'"></i>
                                {{ assertItem.passed ? 'PASS' : 'FAIL' }}
                            </span>
                            <div>
                                <div style="font-weight: 600; color: #1e293b; font-size: 12.5px;">
                                    {{ assertItem.name }}
                                </div>
                                <div style="color: #64748b; font-size: 11px; margin-top: 2px;">
                                    {{ assertItem.message }}
                                </div>
                            </div>
                        </div>
                        <div style="font-size: 11.5px; text-align: right;">
                            <div style="color: #475569;">
                                期望: <code
                                    style="background: #f1f5f9; padding: 1px 4px; border-radius: 3px;">{{ assertItem.expected !== undefined ? assertItem.expected : '-' }}</code>
                            </div>
                            <div style="color: #64748b; margin-top: 2px;">
                                实际: <code
                                    :style="{ color: assertItem.passed ? '#059669' : '#dc2626', background: '#f8fafc', padding: '1px 4px', borderRadius: '3px' }">{{ assertItem.actual !== null && assertItem.actual !== undefined ? assertItem.actual : '空' }}</code>
                            </div>
                        </div>
                    </div>

                    <!-- 提取变量展示 -->
                    <div v-if="apiTestResult.extracted_variables && Object.keys(apiTestResult.extracted_variables).length > 0"
                        style="margin-top: 12px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 8px 12px;">
                        <div style="font-size: 12px; font-weight: 700; color: #1e40af; margin-bottom: 4px;">
                            <i class="fa-solid fa-key" style="margin-right: 4px;"></i>已从响应成功提取的变量：
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                            <span v-for="(vVal, vKey) in apiTestResult.extracted_variables" :key="vKey"
                                class="pm-var-badge">
                                <strong style="color: #0284c7;">{{ vKey }}</strong>: {{ vVal }}
                            </span>
                        </div>
                    </div>

                    <!-- 环境变量持久化回写同步提示条 (Apifox 风格) -->
                    <div v-if="apiTestResult.environment && apiTestResult.environment.updated_variables && Object.keys(apiTestResult.environment.updated_variables).length > 0"
                        style="margin-top: 12px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 6px; padding: 10px 14px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; flex-wrap: wrap; gap: 6px;">
                            <div style="font-size: 12.5px; font-weight: 700; color: #166534; display: flex; align-items: center; gap: 6px;">
                                <i class="fa-solid fa-cloud-arrow-up" style="color: #15803d;"></i>
                                已自动同步持久化至环境 [{{ apiTestResult.environment.name }}] 变量池:
                            </div>
                            <el-button size="small" type="success" link @click="openEnvDialog">
                                <i class="fa-solid fa-sliders" style="margin-right: 4px;"></i>查看环境变量列表
                            </el-button>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            <div v-for="(uVal, uKey) in apiTestResult.environment.updated_variables" :key="uKey"
                                style="background: #ffffff; border: 1px solid #bbf7d0; border-radius: 4px; padding: 3px 8px; font-size: 12px; display: flex; align-items: center; gap: 6px;">
                                <span style="font-weight: 600; color: #15803d;">{{ uKey }}</span>
                                <span style="color: #94a3b8;">=</span>
                                <span style="color: #334155; font-family: monospace; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ uVal }}</span>
                                <el-tooltip content="点击一键复制引用语法" placement="top">
                                    <el-button size="small" link type="primary" @click="copyEnvVarRef(uKey)">
                                        <i class="fa-regular fa-copy"></i>
                                    </el-button>
                                </el-tooltip>
                            </div>
                        </div>
                        <div style="font-size: 11px; color: #15803d; margin-top: 6px;">
                            💡 提示：该环境下的后续接口可直接使用 <code v-pre>{{变量名}}</code> 引用上述变量。
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <template #footer>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <div style="font-size: 12px; color: #64748b;">
                <i class="fa-solid fa-shield-halved" style="color: #10b981; margin-right: 4px;"></i>
                接口已绑定宿主节点，当机器离线时调度器将自动熔断并静默抑制误报
            </div>
            <div style="display: flex; gap: 10px;">
                <el-button @click="apiDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="submitApiForm" :loading="apiSubmitting">
                    {{ editingApiId ? '保存修改并更新调度' : '确认创建并接入调度' }}
                </el-button>
            </div>
        </div>
    </template>
</el-dialog>
<el-dialog v-model="postmanImportDialogVisible"
    :title="'从 Postman 导入接口资产' + (postmanImportMachine ? (' - ' + postmanImportMachine.name) : '')"
    width="920px" top="5vh" destroy-on-close :close-on-click-modal="false">
    
    <!-- 导入成功结果视图 -->
    <div v-if="postmanImportSuccessResult" style="padding: 20px 10px; text-align: center;">
        <el-result icon="success" title="Postman 接口导入成功！"
            :sub-title="'已成功为宿主机器 [' + (postmanImportMachine ? postmanImportMachine.name : '') + '] 接入 ' + postmanImportSuccessResult.total_imported + ' 个接口探针任务'">
            <template #extra>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 0 auto 20px auto; max-width: 650px; text-align: left;">
                    <div style="font-weight: 600; color: #0f172a; margin-bottom: 10px; font-size: 14px;">
                        <i class="fa-solid fa-circle-check" style="color: #10b981; margin-right: 6px;"></i>导入处理明细：
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px; color: #475569;">
                        <div>• 新增创建接口：<strong style="color: #059669;">{{ postmanImportSuccessResult.created_count || postmanImportSuccessResult.total_imported }}</strong> 个</div>
                        <div>• 覆盖更新接口：<strong>{{ postmanImportSuccessResult.updated_count || 0 }}</strong> 个</div>
                        <div>• 跳过已有接口：<strong>{{ postmanImportSuccessResult.skipped_count || 0 }}</strong> 个</div>
                        <div>• 环境变量同步：<strong>{{ postmanImportSuccessResult.env_vars_synced_count || 0 }}</strong> 个已存入环境</div>
                    </div>
                    <div v-if="postmanImportSuccessResult.machine_base_url_updated" style="margin-top: 10px; font-size: 12.5px; color: #0284c7; background: #f0f9ff; padding: 6px 10px; border-radius: 4px;">
                        <i class="fa-solid fa-link" style="margin-right: 4px;"></i>已将机器【服务基准地址 (Base URL)】自动对齐为：<code>{{ postmanImportSuccessResult.machine_base_url }}</code>
                    </div>
                </div>

                <div style="display: flex; justify-content: center; gap: 14px;">
                    <el-button type="primary" size="large" @click="goToImportedApisView">
                        <i class="fa-solid fa-arrow-up-right-from-square" style="margin-right: 6px;"></i>前往【接口管理】查看导入的接口
                    </el-button>
                    <el-button size="large" @click="resetPostmanImport">
                        <i class="fa-solid fa-rotate-left" style="margin-right: 6px;"></i>继续导入其他文件
                    </el-button>
                    <el-button size="large" plain @click="postmanImportDialogVisible = false">
                        关闭
                    </el-button>
                </div>
            </template>
        </el-result>
    </div>

    <!-- 主导入操作面板 (上传/解析/选择) -->
    <div v-else v-loading="postmanImportLoading" element-loading-text="正在智能解析 Postman 协议资产...">
        <!-- 1. 目标宿主机器选择栏 -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-weight: 600; font-size: 13.5px; color: #1e293b;">
                    <i class="fa-solid fa-server" style="color: #10b981; margin-right: 6px;"></i>目标宿主机器：
                </span>
                <el-select v-model="postmanImportMachineId" placeholder="请选择宿主机器" size="small" style="width: 260px;" @change="onPostmanImportMachineChange">
                    <el-option v-for="m in machineList" :key="m.id" :label="m.name + ' (' + m.host + ':' + m.port + ')'" :value="m.id">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>{{ m.name }}</span>
                            <span style="font-size: 11px; color: #94a3b8;">{{ m.environment_name || '默认环境' }}</span>
                        </div>
                    </el-option>
                </el-select>
            </div>

            <div v-if="postmanImportMachine" style="font-size: 12px; color: #64748b; display: flex; align-items: center; gap: 8px;">
                <span>归属环境: <strong style="color: #0f172a;">{{ postmanImportMachine.environment_name || '默认环境' }}</strong></span>
                <span style="color: #cbd5e1;">|</span>
                <span>服务地址: <code class="code-pill">{{ postmanImportMachine.base_url || ('http://' + postmanImportMachine.host + ':' + postmanImportMachine.port) }}</code></span>
            </div>
        </div>

        <!-- 2. 数据来源选择卡片 (未解析状态) -->
        <div v-if="!postmanPreviewData">
            <el-tabs v-model="postmanImportActiveTab" class="pm-sub-tabs">
                <el-tab-pane label="📁 上传 Postman 文件或 ZIP 压缩包" name="upload">
                    <div style="padding: 10px 0;">
                        <el-upload
                            drag
                            action="#"
                            :auto-upload="false"
                            :show-file-list="false"
                            :on-change="handlePostmanFileChange"
                            accept=".zip,.json"
                            style="width: 100%;">
                            <i class="fa-solid fa-cloud-arrow-up" style="font-size: 46px; color: #8b5cf6; margin-bottom: 12px;"></i>
                            <div class="el-upload__text" style="font-size: 14px; color: #334155;">
                                将 Postman 导出的 <strong>.zip</strong> 压缩包或 <strong>.json</strong> 文件拖拽至此处，或 <em>点击选取上传</em>
                            </div>
                            <template #tip>
                                <div style="font-size: 12px; color: #64748b; line-height: 1.6; margin-top: 10px; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 10px 14px; border-radius: 6px;">
                                    <i class="fa-solid fa-circle-info" style="color: #16a34a; margin-right: 4px;"></i>
                                    <strong>格式兼容说明：</strong>
                                    <ul style="margin: 4px 0 0 18px; padding: 0;">
                                        <li><strong>ZIP 压缩包 (如 table.zip)</strong>：系统自动合并集合与环境变量，将 <code>{{baseUrl}}</code> 自动对齐到宿主机器！</li>
                                        <li><strong>单个 Collection JSON (v2.0 / v2.1)</strong>：包含接口路径、Headers、Pre-request 脚本、Tests 断言等。</li>
                                        <li><strong>Pre-request / Tests 脚本无损兼容</strong>：Postman 中的 <code>jsrsasign</code> RSA 加密、动态时间戳及断言均可完整保留并迁移！</li>
                                    </ul>
                                </div>
                            </template>
                        </el-upload>
                    </div>
                </el-tab-pane>

                <el-tab-pane label="📝 粘贴 Postman JSON 文本" name="text">
                    <div style="padding: 10px 0;">
                        <el-input
                            v-model="postmanRawJsonText"
                            type="textarea"
                            :rows="12"
                            placeholder="请在此粘贴从 Postman 导出的 Collection JSON 文本（必须满足 Postman Collection v2.0 或 v2.1 格式规范）..."
                            style="font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                        </el-input>
                        <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
                            <el-button type="primary" @click="handlePostmanTextParse" :disabled="!postmanRawJsonText.trim()">
                                <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 6px;"></i>开始解析 JSON 文本
                            </el-button>
                        </div>
                    </div>
                </el-tab-pane>
            </el-tabs>
        </div>

        <!-- 3. 解析结果预览与导入选项配置区 -->
        <div v-else>
            <!-- 解析统计摘要横幅 -->
            <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #86efac; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-circle-check" style="font-size: 20px; color: #16a34a;"></i>
                    <div>
                        <div style="font-size: 14px; font-weight: 700; color: #14532d;">
                            {{ postmanPreviewData.collection_name || 'Postman Collection' }}
                        </div>
                        <div style="font-size: 12px; color: #15803d; margin-top: 2px;">
                            共解析出 <strong>{{ postmanPreviewData.apis.length }}</strong> 个接口，识别出 <strong>{{ Object.keys(postmanPreviewData.environment_variables || {}).length }}</strong> 个环境变量
                            <span v-if="postmanPreviewData.base_url">，检测到 Base URL: <code>{{ postmanPreviewData.base_url }}</code></span>
                        </div>
                    </div>
                </div>
                <el-button size="small" plain @click="resetPostmanImport">
                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px;"></i>重新选择文件
                </el-button>
            </div>

            <!-- 导入配置项控制卡片 -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px;">
                <div style="font-weight: 600; font-size: 13px; color: #334155; margin-bottom: 8px;">
                    <i class="fa-solid fa-sliders" style="margin-right: 6px; color: #6366f1;"></i>导入选项与策略：
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px; font-size: 13px;">
                    <div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap;">
                        <el-checkbox v-model="postmanSyncEnvVars" style="margin: 0;">
                            <span>同步 Postman 环境变量至宿主机器所属环境 ({{ postmanImportMachine ? postmanImportMachine.environment_name : '默认环境' }})</span>
                        </el-checkbox>
                        <el-checkbox v-if="postmanPreviewData.base_url" v-model="postmanUpdateBaseUrl" style="margin: 0;">
                            <span>将 Postman 基准地址写入宿主机器的 <code>base_url</code></span>
                        </el-checkbox>
                    </div>

                    <div v-if="postmanSyncEnvVars && Object.keys(postmanPreviewData.environment_variables || {}).length > 0"
                        style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 6px 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="font-size: 11.5px; color: #64748b;">待同步变量 ({{ Object.keys(postmanPreviewData.environment_variables).length }} 个):</span>
                        <el-tag v-for="(v, k) in postmanPreviewData.environment_variables" :key="k" size="small" type="info" effect="plain" style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">
                            {{ k }}
                        </el-tag>
                    </div>

                    <div style="display: flex; align-items: center; gap: 24px; margin-top: 4px; flex-wrap: wrap;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 12.5px; color: #64748b;">重名处理策略:</span>
                            <el-radio-group v-model="postmanConflictPolicy" size="small">
                                <el-radio-button label="rename">重命名并存 (推荐)</el-radio-button>
                                <el-radio-button label="overwrite">覆盖同名接口</el-radio-button>
                                <el-radio-button label="skip">跳过已存在</el-radio-button>
                            </el-radio-group>
                        </div>

                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 12.5px; color: #64748b;">巡检周期:</span>
                            <el-input-number v-model="postmanCronInterval" :min="1" :max="1440" size="small" style="width: 110px;"></el-input-number>
                            <span style="font-size: 12px; color: #94a3b8;">分钟</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 接口勾选与预览表格 -->
            <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                <div style="background: #f8fafc; padding: 8px 14px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <el-button size="small" type="primary" link @click="toggleSelectAllPostmanApis">
                            {{ postmanSelectedApis.length === postmanPreviewData.apis.length ? '取消全选' : '全部选择' }}
                        </el-button>
                        <span style="font-size: 12px; color: #64748b;">
                            已勾选 <strong>{{ postmanSelectedApis.length }}</strong> / {{ postmanPreviewData.apis.length }} 个接口
                        </span>
                    </div>
                    <span style="font-size: 11.5px; color: #94a3b8;">
                        <i class="fa-solid fa-code-compare" style="margin-right: 4px;"></i>已自动从 URL 中剥离 {{baseUrl}} 适配宿主机器基准地址
                    </span>
                </div>

                <div style="max-height: 280px; overflow-y: auto;">
                    <table class="pm-table" style="width: 100%;">
                        <thead>
                            <tr>
                                <th style="width: 45px; text-align: center;">选择</th>
                                <th style="width: 75px; text-align: center;">请求方法</th>
                                <th style="width: 220px;">接口名称</th>
                                <th>相对路径 (Http Path)</th>
                                <th style="width: 130px; text-align: center;">脚本与断言</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(item, idx) in postmanPreviewData.apis" :key="idx"
                                :style="isPostmanApiSelected(item) ? 'background-color: #f0fdf4;' : ''"
                                @click="togglePostmanApiSelection(item)" style="cursor: pointer;">
                                <td style="text-align: center;" @click.stop>
                                    <el-checkbox :model-value="isPostmanApiSelected(item)" @change="togglePostmanApiSelection(item)"></el-checkbox>
                                </td>
                                <td style="text-align: center;">
                                    <el-tag size="small"
                                        :type="item.http_method === 'GET' ? 'success' : (item.http_method === 'POST' ? 'primary' : (item.http_method === 'DELETE' ? 'danger' : 'warning'))"
                                        effect="dark" style="font-weight: 700; font-size: 10.5px;">
                                        {{ item.http_method }}
                                    </el-tag>
                                </td>
                                <td>
                                    <div style="font-weight: 600; color: #0f172a; font-size: 12.5px;">{{ item.name }}</div>
                                    <div v-if="item.description" style="font-size: 11px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px;">
                                        {{ item.description }}
                                    </div>
                                </td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                        <span class="code-pill" style="font-size: 11.5px;">{{ item.http_path }}</span>
                                        <el-tag v-if="item.http_params && item.http_params.some(p => p.description && p.description.includes('路径参数'))"
                                            size="small" type="info" effect="plain" style="font-size: 10.5px; height: 19px; padding: 0 4px; border-color: #cbd5e1; color: #475569;">
                                            <i class="fa-solid fa-code-merge" style="margin-right: 2px;"></i>路径参数
                                        </el-tag>
                                        <el-tag v-if="item.auth_type && item.auth_type !== 'none'"
                                            size="small" type="primary" effect="plain" style="font-size: 10.5px; height: 19px; padding: 0 4px;">
                                            <i class="fa-solid fa-key" style="margin-right: 2px;"></i>{{ item.auth_type === 'custom_header' ? 'Header鉴权' : (item.auth_type === 'bearer' ? 'Bearer' : 'Basic') }}
                                        </el-tag>
                                    </div>
                                </td>
                                <td style="text-align: center;">
                                    <div style="display: flex; justify-content: center; gap: 6px;">
                                        <el-tooltip v-if="item.pre_actions && item.pre_actions.length > 0"
                                            :content="'包含 ' + item.pre_actions.length + ' 个前置脚本/操作 (如 RSA 签名等)'" placement="top">
                                            <el-tag size="small" type="warning" effect="plain" style="font-size: 10.5px; height: 20px; padding: 0 5px;">
                                                <i class="fa-solid fa-bolt" style="margin-right: 2px;"></i>前置脚本
                                            </el-tag>
                                        </el-tooltip>
                                        <el-tooltip v-if="item.post_actions && item.post_actions.length > 0"
                                            :content="'包含 ' + item.post_actions.length + ' 个后置断言/提取操作'" placement="top">
                                            <el-tag size="small" type="success" effect="plain" style="font-size: 10.5px; height: 20px; padding: 0 5px;">
                                                <i class="fa-solid fa-vial-circle-check" style="margin-right: 2px;"></i>测试断言
                                            </el-tag>
                                        </el-tooltip>
                                        <span v-if="(!item.pre_actions || item.pre_actions.length === 0) && (!item.post_actions || item.post_actions.length === 0)"
                                            style="color: #cbd5e1; font-size: 11px;">无脚本</span>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <template #footer>
        <div v-if="!postmanImportSuccessResult" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <div style="font-size: 12px; color: #64748b;">
                <span v-if="postmanPreviewData">
                    已就绪，导入后调度引擎将自动接管监控
                </span>
                <span v-else>
                    支持 Postman Collection v2.0 / v2.1 规范及包含环境变量的 ZIP 打包文件
                </span>
            </div>
            <div style="display: flex; gap: 10px;">
                <el-button @click="postmanImportDialogVisible = false">取消</el-button>
                <el-button v-if="postmanPreviewData" type="primary"
                    :disabled="postmanSelectedApis.length === 0 || !postmanImportMachineId"
                    :loading="postmanImportLoading"
                    @click="executeConfirmPostmanImport">
                    <i class="fa-solid fa-cloud-arrow-down" style="margin-right: 6px;"></i>
                    确认导入已选 ({{ postmanSelectedApis.length }}) 个接口
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
    name: 'ApiManagementView',
    setup() {
        return inject('workbench')
    }
}
</script>
