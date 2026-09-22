<template>
                <div v-show="currentNav === 'scenario_probe'">
                    <!-- 顶部场景指标卡片 -->
                    <div class="kpi-grid"
                        style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 16px;">
                        <div class="kpi-box">
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center;">
                                <span>场景总数</span>
                                <el-tag v-if="selectedScenarioEnv !== 'ALL'" size="small" type="primary" effect="plain" style="font-size: 10.5px; height: 18px; padding: 0 5px;">{{ selectedScenarioEnv }}</el-tag>
                            </div>
                            <div class="kpi-num">{{ scenarioTotalCount }} <span style="font-size: 12px; color: #64748b; font-weight: normal;">Scenarios</span></div>
                        </div>
                        <div class="kpi-box kpi-success">
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                <span>已启用自动拨测</span>
                            </div>
                            <div class="kpi-num" style="color: #059669;">{{ scenarioActiveCount }} <span style="font-size: 12px; color: #64748b; font-weight: normal;">Active</span></div>
                        </div>
                        <div class="kpi-box kpi-info">
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                <span>含清理步骤 (闭环保障)</span>
                            </div>
                            <div class="kpi-num" style="color: #0284c7;">{{ scenarioCleanupCount }} <span style="font-size: 12px; color: #64748b; font-weight: normal;">With Cleanup</span></div>
                        </div>
                        <div class="kpi-box">
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
                                <span>业务链路节点总数</span>
                            </div>
                            <div class="kpi-num">{{ scenarioStepTotalCount }} <span style="font-size: 12px; color: #64748b; font-weight: normal;">Steps</span></div>
                        </div>
                    </div>

                    <!-- 场景资产管理表格卡片 (与接口管理列表样式完全一致) -->
                    <div class="wb-card">
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <div
                                    style="font-size: 15px; font-weight: 600; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-route" style="color: #f97316;"></i>
                                    <span>业务链路场景列表</span>
                                </div>
                                <el-radio-group v-model="selectedScenarioEnv" size="small">
                                    <el-radio-button label="ALL">全部环境</el-radio-button>
                                    <el-radio-button v-for="env in environmentList" :key="env.id" :label="env.name">{{
                                        env.name }}</el-radio-button>
                                </el-radio-group>
                                <el-select v-model="selectedScenarioMachine" placeholder="所属机器" size="small"
                                    style="width: 170px;">
                                    <el-option label="全部机器节点" value="ALL"></el-option>
                                    <el-option v-for="m in scenarioMachineOptions" :key="m.id"
                                        :label="m.name + ' (' + m.host + ':' + m.port + ')'" :value="m.id"></el-option>
                                </el-select>
                                <el-select v-model="selectedScenarioStatus" placeholder="状态过滤" size="small"
                                    style="width: 130px;">
                                    <el-option label="全部状态" value="ALL"></el-option>
                                    <el-option label="HEALTHY" value="HEALTHY"></el-option>
                                    <el-option label="DOWN" value="DOWN"></el-option>
                                    <el-option label="UNKNOWN" value="UNKNOWN"></el-option>
                                </el-select>
                                <el-tag size="small" type="info" effect="plain">{{ filteredScenarios.length }} 个场景</el-tag>
                                <el-input v-model="scenarioSearchQuery" placeholder="搜索场景名称、描述、机器..." clearable size="small"
                                    style="width: 210px;">
                                    <template #prefix><i class="fa-solid fa-magnifying-glass"
                                            style="color: #94a3b8;"></i></template>
                                </el-input>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <el-button size="small" type="primary" @click="openCreateScenarioDialog()">
                                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>新建场景
                                </el-button>
                            </div>
                        </div>

                        <!-- 批量操作工具栏 (选中项 >= 1 时显示) -->
                        <transition name="el-fade-in">
                            <div v-if="selectedScenarioRows.length > 0"
                                style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px 16px; margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.06);">
                                <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #1e40af; font-weight: 600;">
                                    <span style="display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; background: #2563eb; color: #ffffff; border-radius: 50%; font-size: 12px;">
                                        <i class="fa-solid fa-check"></i>
                                    </span>
                                    <span>已勾选 <b style="color: #1d4ed8; font-size: 15px;">{{ selectedScenarioRows.length }}</b> 个场景</span>
                                    <span style="font-size: 11.5px; color: #64748b; font-weight: normal;">(共 {{ filteredScenarios.length }} 个)</span>
                                </div>

                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <!-- 批量关闭探测周期 -->
                                    <el-button size="small" type="warning" plain :loading="isScenarioBatchOperating" @click="handleBatchToggleScenarioActive(false)">
                                        <i class="fa-solid fa-pause" style="margin-right: 4px;"></i>批量关闭探测周期
                                    </el-button>

                                    <!-- 批量开启探测周期 -->
                                    <el-button size="small" type="success" plain :loading="isScenarioBatchOperating" @click="handleBatchToggleScenarioActive(true)">
                                        <i class="fa-solid fa-play" style="margin-right: 4px;"></i>批量开启探测周期
                                    </el-button>

                                    <!-- 批量调整周期 -->
                                    <el-dropdown trigger="click" @command="handleBatchSetScenarioInterval" :disabled="isScenarioBatchOperating">
                                        <el-button size="small" type="info" plain>
                                            <i class="fa-solid fa-clock" style="margin-right: 4px;"></i>批量修改周期
                                            <i class="fa-solid fa-angle-down" style="margin-left: 4px; font-size: 10px;"></i>
                                        </el-button>
                                        <template #dropdown>
                                            <el-dropdown-menu>
                                                <div style="padding: 5px 12px; font-size: 11px; font-weight: 700; color: #475569; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                                                    设置所选场景的拨测执行间隔:
                                                </div>
                                                <el-dropdown-item :command="1">1 分钟 (高频验证)</el-dropdown-item>
                                                <el-dropdown-item :command="5">5 分钟 (生产标准)</el-dropdown-item>
                                                <el-dropdown-item :command="15">15 分钟</el-dropdown-item>
                                                <el-dropdown-item :command="30">30 分钟</el-dropdown-item>
                                                <el-dropdown-item :command="60">1 小时</el-dropdown-item>
                                                <el-dropdown-item :command="1440">1 天</el-dropdown-item>
                                            </el-dropdown-menu>
                                        </template>
                                    </el-dropdown>

                                    <!-- 批量删除 -->
                                    <el-popconfirm :title="'确定要批量删除已选中的 ' + selectedScenarioRows.length + ' 个场景及其历史时序流水吗？此操作不可逆！'"
                                        confirm-button-text="确定删除" cancel-button-text="取消" confirm-button-type="danger"
                                        @confirm="handleBatchDeleteScenarios">
                                        <template #reference>
                                            <el-button size="small" type="danger" :loading="isScenarioBatchOperating">
                                                <i class="fa-solid fa-trash-can" style="margin-right: 4px;"></i>批量删除 ({{ selectedScenarioRows.length }})
                                            </el-button>
                                        </template>
                                    </el-popconfirm>

                                    <!-- 清除勾选 -->
                                    <el-button size="small" text @click="clearScenarioSelection" style="color: #64748b;">
                                        取消选择
                                    </el-button>
                                </div>
                            </div>
                        </transition>

                        <el-table ref="scenarioTableRef" :data="paginatedScenarios" row-key="id" v-loading="scenarioLoading" @selection-change="handleScenarioSelectionChange" style="width: 100%"
                            empty-text="暂无拨测场景，可点击右上角【新建场景】创建业务链路">
                            <el-table-column type="selection" :reserve-selection="true" width="45" align="center" />
                            <el-table-column prop="id" label="ID" width="50" align="center"></el-table-column>
                            <el-table-column label="场景名称" min-width="160">
                                <template #default="{ row }">
                                    <div style="display: flex; flex-direction: column;">
                                        <div style="display: flex; align-items: center; gap: 6px;">
                                            <span style="font-weight: 600; color: #0f172a; font-size: 13.5px;">{{ row.name }}</span>
                                            <el-tag v-if="row.variables && Object.keys(row.variables).length"
                                                size="small" type="primary" effect="plain"
                                                style="font-size: 10px; height: 18px; padding: 0 4px; border-radius: 4px;"
                                                title="已配置场景专属变量 (隔离生效)">
                                                <i class="fa-solid fa-cube" style="margin-right: 2px;"></i>{{ Object.keys(row.variables).length }} 个变量
                                            </el-tag>
                                        </div>
                                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                                            <i class="fa-solid fa-server" style="color: #10b981; margin-right: 4px;"></i>{{ row.machine_name || ('机器#' + row.machine_id) }}
                                            <span v-if="row.description" style="color: #94a3b8; margin-left: 6px;">· {{ row.description }}</span>
                                        </div>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="所属环境" width="100" align="center">
                                <template #default="{ row }">
                                    <el-tag size="small" :type="getGroupTagType(row.environment_name)" effect="light"
                                        style="font-weight: 600;">
                                        {{ row.environment_name || '默认环境' }}
                                    </el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column min-width="280">
                                <template #header>
                                    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                                        <span>业务链路步骤</span>
                                        <el-button link type="primary" size="small"
                                            style="font-size: 11px; font-weight: normal; padding: 0 4px;"
                                            @click="toggleAllScenarioStepsExpand">
                                            <i :class="isAllScenarioStepsExpanded ? 'fa-solid fa-compress' : 'fa-solid fa-expand'"
                                                style="margin-right: 3px; font-size: 10px;"></i>
                                            {{ isAllScenarioStepsExpanded ? '全部收起' : '全部展开' }}
                                        </el-button>
                                    </div>
                                </template>
                                <template #default="{ row }">
                                    <div style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap; line-height: 1.4;">
                                        <!-- 步骤节点列表：若未展开则至多显示前 2 个节点；若已展开则平铺显示全部 -->
                                        <template v-for="(step, idx) in (isScenarioStepsExpanded(row.id) ? (row.steps || []) : (row.steps || []).slice(0, 2))" :key="idx">
                                            <el-tooltip placement="top" :enterable="false">
                                                <template #content>
                                                    <div style="font-weight: 600;">节点 {{ idx + 1 }}: [{{ step.http_method }}] {{ step.name || step.http_path }}</div>
                                                    <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">路径: {{ step.http_path }}</div>
                                                    <template v-if="(row.last_steps_detail || [])[idx]">
                                                        <div style="font-size: 11px; margin-top: 4px;">
                                                            执行结果: <b :style="{ color: (row.last_steps_detail[idx].ok ? '#4ade80' : '#f87171') }">
                                                                {{ (row.last_steps_detail[idx].ok ? '通过' : ((row.last_steps_detail[idx].skipped ? '已跳过' : '未通过'))) }}
                                                                (HTTP {{ row.last_steps_detail[idx].status_code ?? '-' }})
                                                            </b>
                                                            <span style="margin-left: 6px;">耗时: {{ row.last_steps_detail[idx].latency_ms || 0 }}ms</span>
                                                        </div>
                                                        <div style="font-size: 11px; margin-top: 2px;">
                                                            契约校验:
                                                            <span v-if="(row.last_steps_detail[idx].schema_configured)">
                                                                <span v-if="row.last_steps_detail[idx].schema_matched === true" style="color: #4ade80; font-weight: 600;">一致 (通过)</span>
                                                                <span v-else style="color: #f87171; font-weight: 600;">突变 ({{ (row.last_steps_detail[idx].schema_errors || []).map(e => e.message).join('; ') || '不匹配' }})</span>
                                                            </span>
                                                            <span v-else style="color: #94a3b8;">未配置契约</span>
                                                        </div>
                                                    </template>
                                                    <template v-else>
                                                        <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                                                            契约状态: {{ step.expected_schema && Object.keys(step.expected_schema).length ? '已配置契约 (待拨测)' : '未配置契约' }}
                                                        </div>
                                                    </template>
                                                </template>
                                                <span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; border-radius: 4px; font-size: 11.5px; cursor: default; max-width: 170px;"
                                                    :style="getMethodBadgeStyle(step.http_method)">
                                                    <b style="flex-shrink: 0;">{{ step.http_method }}</b>
                                                    <span style="color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="step.name || step.http_path">{{ step.name || step.http_path }}</span>
                                                    <!-- 步骤契约状态图标 -->
                                                    <template v-if="(row.last_steps_detail || [])[idx] && (row.last_steps_detail || [])[idx].schema_configured">
                                                        <i v-if="(row.last_steps_detail || [])[idx].schema_matched === true"
                                                            class="fa-solid fa-circle-check" style="color: #059669; font-size: 10px; flex-shrink: 0;" title="契约一致"></i>
                                                        <i v-else-if="(row.last_steps_detail || [])[idx].schema_matched === false"
                                                            class="fa-solid fa-triangle-exclamation" style="color: #dc2626; font-size: 10px; flex-shrink: 0;" title="契约突变"></i>
                                                    </template>
                                                    <template v-else-if="step.expected_schema && Object.keys(step.expected_schema).length">
                                                        <i class="fa-solid fa-shield-halved" style="color: #64748b; font-size: 10px; flex-shrink: 0;" title="已配置契约(待校验)"></i>
                                                    </template>
                                                    <el-tooltip v-if="step.is_cleanup" content="清理步骤: 拨测引擎将保证其无论成败均执行" placement="top">
                                                        <i class="fa-solid fa-broom" style="color: #d97706; flex-shrink: 0;"></i>
                                                    </el-tooltip>
                                                </span>
                                            </el-tooltip>
                                            <i v-if="idx < (isScenarioStepsExpanded(row.id) ? (row.steps || []).length - 1 : Math.min((row.steps || []).length - 1, 1))"
                                                class="fa-solid fa-arrow-right" style="font-size: 9px; color: #cbd5e1;"></i>
                                        </template>

                                        <!-- 多步骤折叠控制胶囊与悬浮全景预览 -->
                                        <template v-if="(row.steps || []).length > 2">
                                            <template v-if="!isScenarioStepsExpanded(row.id)">
                                                <i class="fa-solid fa-arrow-right" style="font-size: 9px; color: #cbd5e1;"></i>
                                                <el-popover placement="bottom-start" :width="380" trigger="hover">
                                                    <template #reference>
                                                        <el-tag size="small" type="info" effect="light" class="step-collapse-tag"
                                                            style="cursor: pointer; font-size: 11px; font-weight: 600; user-select: none; border-color: #cbd5e1;"
                                                            @click.stop="toggleScenarioStepsExpand(row.id)">
                                                            +{{ (row.steps || []).length - 2 }} 步骤
                                                            <i class="fa-solid fa-chevron-down" style="font-size: 10px; margin-left: 2px;"></i>
                                                        </el-tag>
                                                    </template>
                                                    <!-- 浮层全景展示 -->
                                                    <div style="font-size: 12px;">
                                                        <div style="font-weight: 700; color: #0f172a; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                                                            <span><i class="fa-solid fa-route" style="color: #f97316; margin-right: 5px;"></i>完整业务链路节点 (共 {{ row.steps.length }} 步)</span>
                                                            <el-button link type="primary" size="small" @click.stop="toggleScenarioStepsExpand(row.id)">
                                                                展开到表格
                                                            </el-button>
                                                        </div>
                                                        <div style="display: flex; flex-direction: column; gap: 6px; max-height: 280px; overflow-y: auto;">
                                                            <div v-for="(s, sIdx) in (row.steps || [])" :key="sIdx"
                                                                style="display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;">
                                                                <div style="display: flex; align-items: center; gap: 6px; overflow: hidden;">
                                                                    <span style="font-size: 11px; color: #94a3b8; font-weight: 600;">#{{ sIdx + 1 }}</span>
                                                                    <span style="font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px;"
                                                                        :style="getMethodBadgeStyle(s.http_method)">{{ s.http_method }}</span>
                                                                    <span style="font-weight: 600; color: #1e293b; font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 170px;" :title="s.name || s.http_path">
                                                                        {{ s.name || s.http_path }}
                                                                    </span>
                                                                    <el-tag v-if="s.is_cleanup" size="small" type="warning" effect="plain" style="font-size: 10px; height: 18px; padding: 0 4px;">
                                                                        清理
                                                                    </el-tag>
                                                                </div>
                                                                <div style="display: flex; align-items: center; gap: 4px; font-size: 11px; margin-left: 8px; flex-shrink: 0;">
                                                                    <template v-if="(row.last_steps_detail || [])[sIdx]">
                                                                        <span :style="{ color: (row.last_steps_detail[sIdx].ok ? '#059669' : '#dc2626'), fontWeight: '600' }">
                                                                            {{ (row.last_steps_detail[sIdx].ok ? '✓ 通过' : '✗ 失败') }}
                                                                        </span>
                                                                        <span v-if="(row.last_steps_detail[sIdx].schema_configured)" style="margin-left: 3px;">
                                                                            <el-tag size="small" :type="(row.last_steps_detail[sIdx].schema_matched ? 'success' : 'danger')" effect="plain" style="font-size: 10px; height: 18px; padding: 0 4px;">
                                                                                {{ row.last_steps_detail[sIdx].schema_matched ? '契约一致' : '契约突变' }}
                                                                            </el-tag>
                                                                        </span>
                                                                    </template>
                                                                    <span v-else style="color: #94a3b8;">待拨测</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </el-popover>
                                            </template>
                                            <template v-else>
                                                <el-tag size="small" type="info" effect="plain" class="step-collapse-tag"
                                                    style="cursor: pointer; font-size: 11px; margin-left: 4px; user-select: none;"
                                                    @click.stop="toggleScenarioStepsExpand(row.id)">
                                                    收起 <i class="fa-solid fa-chevron-up" style="font-size: 10px; margin-left: 2px;"></i>
                                                </el-tag>
                                            </template>
                                        </template>
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
                            <el-table-column label="整链耗时" width="110" align="center">
                                <template #default="{ row }">
                                    <div
                                        v-if="row.last_total_latency_ms !== null && row.last_total_latency_ms !== undefined">
                                        <span :class="getLatencyBadgeClass(row.last_total_latency_ms)">
                                            {{ row.last_total_latency_ms }} ms
                                        </span>
                                    </div>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">待拨测</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="契约校验" width="90" align="center">
                                <template #default="{ row }">
                                    <el-tooltip v-if="row.last_schema_matched === true" placement="top">
                                        <template #content>
                                            <div style="font-weight: 600; margin-bottom: 2px;">整链各节点契约校验均通过:</div>
                                            <div v-for="(d, di) in (row.last_steps_detail || []).filter(x => x.schema_configured)" :key="di" style="font-size: 11px;">
                                                · 节点 {{ (d.step_index ?? di) + 1 }} [{{ d.name }}]: 契约一致
                                            </div>
                                        </template>
                                        <el-tag type="success" size="small" style="cursor: pointer;">一致</el-tag>
                                    </el-tooltip>
                                    <el-tooltip v-else-if="row.last_schema_matched === false" placement="top">
                                        <template #content>
                                            <div style="font-weight: 600; color: #fecaca; margin-bottom: 2px;">检测到接口响应契约突变:</div>
                                            <div v-for="(d, di) in (row.last_steps_detail || []).filter(x => x.schema_matched === false)" :key="di" style="font-size: 11px;">
                                                · 节点 {{ (d.step_index ?? di) + 1 }} [{{ d.name }}]: {{ (d.schema_errors || []).map(e => e.message).join('; ') || '结构不匹配' }}
                                            </div>
                                        </template>
                                        <el-tag type="danger" size="small" style="cursor: pointer;">突变</el-tag>
                                    </el-tooltip>
                                    <el-tag v-else-if="!row.schema_configured" type="info" effect="plain" size="small">未配置</el-tag>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">未校验</span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="cron_interval_minutes" label="探测周期" width="95" align="center">
                                <template #default="{ row }">
                                    <el-tooltip :content="getIntervalTooltip(row.cron_interval_minutes, row.is_active)" placement="top">
                                        <el-tag v-if="row.is_active === false" size="small" type="info" effect="plain"
                                            class="probe-interval-tag"
                                            style="cursor: pointer; font-size: 11px;" @click="toggleScenarioActive(row)">
                                            <i class="fa-solid fa-pause" style="margin-right: 3px;"></i>已关闭
                                        </el-tag>
                                        <el-tag v-else size="small" type="primary" effect="plain"
                                            class="probe-interval-tag"
                                            style="cursor: pointer; font-weight: 600; font-size: 11px;" @click="toggleScenarioActive(row)">
                                            <i class="fa-solid fa-clock" style="margin-right: 3px; font-size: 10px;"></i>{{ formatIntervalDisplay(row.cron_interval_minutes, row.is_active) }}
                                        </el-tag>
                                    </el-tooltip>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="200" align="center" fixed="right">
                                <template #default="{ row }">
                                    <div class="api-action-grid">
                                        <el-button size="small" type="success" plain :loading="scenarioRunningId === row.id"
                                            @click="handleRunScenario(row)">
                                            <i class="fa-solid fa-bolt" style="margin-right: 4px;"></i>拨测
                                        </el-button>
                                        <el-button size="small" type="info" plain @click="openScenarioMetricsDrawer(row)">
                                            <i class="fa-solid fa-chart-line" style="margin-right: 4px;"></i>时序
                                        </el-button>
                                        <el-button size="small" type="primary" plain @click="openEditScenarioDialog(row)">
                                            <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                        </el-button>
                                        <el-popconfirm :title="'确定删除场景 [' + row.name + '] 吗？'" confirm-button-text="确定"
                                            cancel-button-text="取消" @confirm="handleDeleteScenario(row)">
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

                        <!-- 表格底部选择与分页状态栏 -->
                        <div v-if="filteredScenarios.length > 0"
                            style="margin-top: 14px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #64748b; padding-top: 12px; border-top: 1px solid #f1f5f9; flex-wrap: wrap; gap: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <div v-if="selectedScenarioRows.length > 0" style="color: #2563eb; font-weight: 600;">
                                    <i class="fa-solid fa-check-double" style="margin-right: 4px;"></i>已选择 {{ selectedScenarioRows.length }} 项 (共 {{ filteredScenarios.length }} 项)
                                </div>
                                <div v-else>
                                    共 {{ filteredScenarios.length }} 个场景，勾选左侧复选框可开启批量操作
                                </div>

                                <div v-if="selectedScenarioRows.length > 0" style="display: flex; gap: 8px;">
                                    <el-button size="small" link type="warning" @click="handleBatchToggleScenarioActive(false)">
                                        批量关闭探测
                                    </el-button>
                                    <el-button size="small" link type="success" @click="handleBatchToggleScenarioActive(true)">
                                        批量开启探测
                                    </el-button>
                                    <el-button size="small" link type="danger" @click="handleBatchDeleteScenarios">
                                        批量删除
                                    </el-button>
                                    <el-button size="small" link @click="clearScenarioSelection" style="color: #64748b;">
                                        取消选择
                                    </el-button>
                                </div>
                            </div>

                            <!-- 分页控制器 -->
                            <el-pagination
                                v-model:current-page="scenarioCurrentPage"
                                v-model:page-size="scenarioPageSize"
                                :page-sizes="[10, 20, 50, 100]"
                                :total="filteredScenarios.length"
                                layout="total, sizes, prev, pager, next, jumper"
                                size="small"
                                background
                            />
                        </div>
                    </div>

                    <!-- ================= 新建/编辑场景对话框 (原接口探测工作台界面 + 业务链路步骤节点流) ================= -->
                    <el-dialog v-model="scenarioDialogVisible"
                        :title="editingScenarioId ? '编辑拨测场景 (业务链路编排)' : '新建拨测场景 (业务链路编排)'" width="980px" top="4vh"
                        class="postman-dialog" destroy-on-close>
                        <!-- 基础元数据设置区 (与接口探测工作台一致) -->
                        <div
                            style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px;">
                            <el-row :gutter="16">
                                <el-col :span="10">
                                    <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px;">
                                        <span style="color: #ef4444; margin-right: 2px;">*</span>宿主机器节点 (Host Node)
                                    </div>
                                    <el-select v-model="scenarioForm.machine_id" placeholder="选择归属机器节点" style="width: 100%;">
                                        <el-option v-for="m in scenarioMachineOptions" :key="m.id"
                                            :label="m.name + ' (' + (m.environment_name || '未指定') + ' | ' + m.host + ':' + m.port + ')'"
                                            :value="m.id"></el-option>
                                    </el-select>
                                </el-col>
                                <el-col :span="14">
                                    <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px;">
                                        <span style="color: #ef4444; margin-right: 2px;">*</span>场景名称 (Scenario Name)
                                    </div>
                                    <el-input v-model="scenarioForm.name" placeholder="例如: 订单创建-查询-删除闭环拨测"></el-input>
                                </el-col>
                            </el-row>
                            <el-row :gutter="16" style="margin-top: 10px;">
                                <el-col :span="24">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                        <div style="font-size: 12px; font-weight: 600; color: #475569; display: flex; align-items: center; gap: 6px;">
                                            <i class="fa-solid fa-clock-rotate-left" style="color: #2563eb;"></i>
                                            <span>定时自动拨测调度</span>
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 6px;">
                                            <span style="font-size: 11.5px; color: #64748b;">{{ scenarioForm.is_active ? '已启用自动拨测' : '已关闭自动拨测' }}</span>
                                            <el-switch v-model="scenarioForm.is_active" inline-prompt active-text="开" inactive-text="关"
                                                style="--el-switch-on-color: #10b981;"></el-switch>
                                        </div>
                                    </div>

                                    <!-- 启用状态下：数值 + 单位下拉 + 快捷胶囊 -->
                                    <div v-if="scenarioForm.is_active">
                                        <div style="display: flex; gap: 8px; align-items: center;">
                                            <el-input-number v-model="scenarioIntervalValue" :min="1" :max="999999" controls-position="right"
                                                style="width: 140px;" placeholder="周期数值"></el-input-number>
                                            <el-select v-model="scenarioIntervalUnit" style="width: 115px;">
                                                <el-option label="分钟 (m)" value="minutes"></el-option>
                                                <el-option label="小时 (h)" value="hours"></el-option>
                                                <el-option label="天 (d)" value="days"></el-option>
                                            </el-select>
                                            <span style="font-size: 11.5px; color: #64748b; margin-left: 2px;">
                                                <span v-if="scenarioIntervalUnit === 'days'">折合 {{ scenarioIntervalValue * 1440 }} 分钟</span>
                                                <span v-else-if="scenarioIntervalUnit === 'hours'">折合 {{ scenarioIntervalValue * 60 }} 分钟</span>
                                                <span v-else>{{ scenarioIntervalValue }} 分钟</span>
                                            </span>
                                        </div>
                                        <!-- 常用快捷周期预设 -->
                                        <div style="display: flex; align-items: center; gap: 6px; margin-top: 6px; flex-wrap: wrap;">
                                            <span style="font-size: 11px; color: #94a3b8;">快捷预设:</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(5, 'minutes')" style="font-size: 11px; padding: 0;">5m</el-button>
                                            <span style="color: #cbd5e1; font-size: 10px;">|</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(15, 'minutes')" style="font-size: 11px; padding: 0;">15m</el-button>
                                            <span style="color: #cbd5e1; font-size: 10px;">|</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(1, 'hours')" style="font-size: 11px; padding: 0;">1h</el-button>
                                            <span style="color: #cbd5e1; font-size: 10px;">|</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(12, 'hours')" style="font-size: 11px; padding: 0;">12h</el-button>
                                            <span style="color: #cbd5e1; font-size: 10px;">|</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(1, 'days')" style="font-size: 11px; padding: 0;">1天</el-button>
                                            <span style="color: #cbd5e1; font-size: 10px;">|</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(7, 'days')" style="font-size: 11px; padding: 0;">7天</el-button>
                                            <span style="color: #cbd5e1; font-size: 10px;">|</span>
                                            <el-button size="small" link type="primary" @click="setQuickScenarioInterval(30, 'days')" style="font-size: 11px; padding: 0; font-weight: 700; color: #7c3aed;">30天 (长效)</el-button>
                                        </div>
                                    </div>

                                    <!-- 停用状态下：提示文本 -->
                                    <div v-else style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 8px 10px; font-size: 11.5px; color: #64748b; display: flex; align-items: center; gap: 6px;">
                                        <i class="fa-solid fa-circle-pause" style="color: #94a3b8; font-size: 13px;"></i>
                                        <span>已关闭后台定时自动拨测。该场景仅支持手动触发执行。</span>
                                    </div>
                                </el-col>
                            </el-row>
                            <el-row :gutter="16" style="margin-top: 10px;">
                                <el-col :span="24">
                                    <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px;">场景描述</div>
                                    <el-input v-model="scenarioForm.description" placeholder="一句话描述该业务链路场景的目的, 例如: 验证订单创建后可查询, 并自动清理测试数据"></el-input>
                                </el-col>
                            </el-row>
                        </div>

                        <!-- ★ 业务链路步骤节点流 (位于定时调度下方) -->
                        <div style="margin-bottom: 16px; border: 1px solid #fed7aa; background: #fff7ed; border-radius: 8px; padding: 12px 14px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 6px;">
                                <div style="font-size: 12.5px; font-weight: 700; color: #9a3412; display: flex; align-items: center; gap: 6px;">
                                    <i class="fa-solid fa-diagram-project" style="color: #f97316;"></i>
                                    业务链路步骤 (Scenario Steps)
                                    <el-tag size="small" type="warning" effect="plain">{{ scenarioSteps.length }} 个节点</el-tag>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                    <span style="font-size: 11px; color: #9a3412; opacity: 0.75;">
                                        点击节点切换配置 · <i class="fa-solid fa-broom" style="color: #d97706;"></i> 清理步骤无论成败均执行 (拨测闭环保障)
                                    </span>
                                    <el-tooltip content="从接口管理选取已有接口, 自动填充节点配置, 无需重复手写" placement="top">
                                        <el-button size="small" type="warning" plain @click="openApiImportDialog">
                                            <i class="fa-solid fa-file-import" style="margin-right: 4px;"></i>从接口管理导入
                                        </el-button>
                                    </el-tooltip>
                                </div>
                            </div>

                            <!-- 节点流: 节点卡片 + 箭头 + 添加节点 -->
                            <div style="display: flex; align-items: stretch; gap: 0; overflow-x: auto; padding: 4px 2px 6px;">
                                <template v-for="(step, idx) in scenarioSteps" :key="idx">
                                    <!-- 节点卡片 -->
                                    <div @click="selectScenarioStep(idx)"
                                        style="position: relative; min-width: 132px; max-width: 132px; padding: 10px 10px 8px; border-radius: 8px; cursor: pointer; transition: all 0.15s; border: 1.5px solid; background: #ffffff; flex-shrink: 0;"
                                        :style="activeStepIndex === idx
                                            ? { borderColor: step.is_cleanup ? '#d97706' : '#f97316', background: step.is_cleanup ? '#fffbeb' : '#fff7ed', boxShadow: '0 2px 8px rgba(249, 115, 22, 0.18)' }
                                            : { borderColor: step.is_cleanup ? '#fde68a' : '#e2e8f0', background: step.is_cleanup ? '#fffdf5' : '#ffffff' }">
                                        <!-- 删除节点按钮 -->
                                        <el-popconfirm :title="`确定删除节点 ${idx + 1} 吗？`" confirm-button-text="删除" cancel-button-text="取消"
                                            @confirm="removeScenarioStep(idx)">
                                            <template #reference>
                                                <span @click.stop
                                                    style="position: absolute; top: -8px; right: -8px; width: 18px; height: 18px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 9px; border: 1px solid #fecaca; z-index: 2;">
                                                    <i class="fa-solid fa-xmark"></i>
                                                </span>
                                            </template>
                                        </el-popconfirm>
                                        <div style="font-size: 10px; color: #94a3b8; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
                                            <span>节点 {{ idx + 1 }}</span>
                                            <div style="display: flex; align-items: center; gap: 3px;">
                                                <span v-if="step.expected_schema && Object.keys(step.expected_schema).length"
                                                    style="font-size: 9px; color: #0284c7; background: #e0f2fe; padding: 1px 3px; border-radius: 3px;" title="已配置响应契约校验">
                                                    <i class="fa-solid fa-shield-halved"></i> 契约
                                                </span>
                                                <el-tooltip v-if="step.is_cleanup" content="清理步骤 (finally 语义)" placement="top">
                                                    <i class="fa-solid fa-broom" style="color: #d97706;"></i>
                                                </el-tooltip>
                                            </div>
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 5px; margin-bottom: 4px;">
                                            <span style="font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px;" :style="getMethodBadgeStyle(step.http_method)">{{ step.http_method }}</span>
                                        </div>
<!--                                        <div style="font-size: 11.5px; font-weight: 600; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">-->
<!--                                            {{ step.name || '未命名节点' }}-->
<!--                                        </div>-->

                                        <div
                                            v-if="editingStepIndex !== idx"
                                            style="display: flex; align-items: center; gap: 4px;"
                                        >
                                          <div
                                              @dblclick="startEditStep(idx)"
                                              style="
                                              font-size: 11.5px;
                                              font-weight: 600;
                                              color: #0f172a;
                                              white-space: nowrap;
                                              overflow: hidden;
                                              text-overflow: ellipsis;
                                              flex: 1;
                                              min-width: 0;"
                                          >
                                            {{ step.name || '未命名节点' }}
                                          </div>
                                          <i
                                              class="fa-solid fa-pen-to-square"
                                              @click.stop="startEditStep(idx)"
                                              title="编辑节点名称"
                                              style="
                                              font-size: 10px;
                                              color: #94a3b8;
                                              cursor: pointer;
                                              flex-shrink: 0;
                                              opacity: 0.6;
                                              transition: opacity 0.15s, color 0.15s;"
                                              @mouseenter="e => { e.target.style.opacity = '1'; e.target.style.color = '#f97316' }"
                                              @mouseleave="e => { e.target.style.opacity = '0.6'; e.target.style.color = '#94a3b8' }"
                                          ></i>
                                        </div>

                                        <input
                                            v-else
                                            :ref="el => { if (el) stepNameInputRefs[idx] = el }"
                                            v-model="step.name"
                                            @blur="finishEditStep"
                                            @keyup.enter="finishEditStep"
                                            @keyup.esc="cancelEditStep(idx)"
                                            style="
                                            font-size: 11.5px;
                                            font-weight: 600;
                                            color: #0f172a;
                                            width: 100%;
                                            padding: 0;
                                            margin: 0;
                                            border: none;
                                            border-bottom: 1px solid #f97316;
                                            background: transparent;
                                            outline: none;
                                            font-family: inherit;
                                            line-height: 1.4;
                                            box-sizing: border-box;
                                          " />

                                        <div style="font-size: 10px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                            {{ step.http_path || '/' }}
                                        </div>
                                        <div v-if="step._testResult" style="margin-top: 4px; font-size: 9.5px;">
                                            <span v-if="step._testResult.schema_matched === true" style="color: #059669; font-weight: 600;">
                                                <i class="fa-solid fa-circle-check"></i> 契约通过
                                            </span>
                                            <span v-else-if="step._testResult.schema_matched === false" style="color: #dc2626; font-weight: 600;">
                                                <i class="fa-solid fa-triangle-exclamation"></i> 契约突变
                                            </span>
                                            <span v-else-if="step._testResult.ok" style="color: #059669;">
                                                <i class="fa-solid fa-circle-check"></i> HTTP {{ step._testResult.status_code }}
                                            </span>
                                            <span v-else style="color: #dc2626;">
                                                <i class="fa-solid fa-circle-xmark"></i> 调试失败
                                            </span>
                                        </div>
                                    </div>
                                    <!-- 箭头连接 -->
                                    <div style="display: flex; align-items: center; padding: 0 6px; flex-shrink: 0;">
                                        <i class="fa-solid fa-angles-right" style="color: #fdba74; font-size: 13px;"></i>
                                    </div>
                                </template>

                                <!-- 添加节点 -->
                                <div @click="addScenarioStep"
                                    style="min-width: 108px; border: 1.5px dashed #fdba74; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; cursor: pointer; color: #ea580c; transition: all 0.15s; flex-shrink: 0; padding: 10px; background: #fffbf7;"
                                    onmouseover="this.style.borderColor='#f97316'; this.style.color='#c2410c';"
                                    onmouseout="this.style.borderColor='#fdba74'; this.style.color='#ea580c';">
                                    <i class="fa-solid fa-circle-plus" style="font-size: 18px;"></i>
                                    <span style="font-size: 12px; font-weight: 600;">添加节点</span>
                                </div>
                            </div>
                        </div>

                        <!-- 以下接口配置区与【接口探测工作台】完全一致, 数据源切换为当前选中节点 -->
                        <template v-if="activeStep">
                            <!-- 宿主机器与环境联动信息条 -->
                            <div
                                style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; font-size: 12px; border: 1px solid #e2e8f0; flex-wrap: wrap; gap: 8px;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    <span style="font-weight: 600; color: #475569;">
                                        <i class="fa-solid fa-server" style="color: #0284c7; margin-right: 3px;"></i>宿主机器:
                                    </span>
                                    <span style="font-weight: 600; color: #0f172a;">
                                        {{ scenarioMachineDisplayName }}
                                    </span>
                                    <span style="color: #cbd5e1; margin: 0 3px;">|</span>
                                    <span style="font-weight: 600; color: #475569;">
                                        <i class="fa-solid fa-layer-group" style="color: #10b981; margin-right: 3px;"></i>所属环境:
                                    </span>
                                    <el-tag size="small" type="success" effect="plain" style="font-weight: 600;">
                                        {{ currentMachineEnvironment.name || '默认环境' }}
                                    </el-tag>
                                    <span style="color: #cbd5e1; margin: 0 4px;">|</span>
                                    <el-button size="small" type="warning" plain @click="openEnvDialog"
                                               style="border-radius: 14px; padding: 2px 6px; height: 24px;">
                                      <i class="fa-solid fa-sliders" style="margin-right: 3px;"></i>环境变量 ({{ Object.keys(currentMachineEnvironment.variables || {}).length }})
                                    </el-button>
                                    <span style="color: #cbd5e1; margin: 0 4px;">|</span>
                                    <el-button size="small" type="primary" plain @click="scenarioVariablesDrawerVisible = true"
                                               style="border-radius: 14px; padding: 2px 8px; height: 24px; font-weight: 600; border-color: #3b82f6; color: #1d4ed8; background: #eff6ff;">
                                      <i class="fa-solid fa-cube" style="margin-right: 4px;"></i>场景专属变量 ({{ scenarioVariablesCount }})
                                    </el-button>
                                    <span style="color: #64748b;">
                                        机器默认地址:
                                        <co
                                            style="background: #e2e8f0; color: #0284c7; padding: 2px 6px; border-radius: 4px; font-family: monospace;">{{ scenarioForm.base_url }}</co>
                                    </span>
                                    <el-tooltip content="点击将当前宿主机器的默认基准地址同步填入下方输入框" placement="top">
                                        <el-button size="small" link type="primary" @click="resetScenarioBaseUrlToMachine">
                                            <i class="fa-solid fa-rotate-left" style="margin-right: 2px;"></i>恢复机器地址
                                        </el-button>
                                    </el-tooltip>
                                    <el-tooltip content="查看/编辑宿主机器所属环境的变量池, 节点配置中可用 {{变量名}} 宏直接引用" placement="top">
                                    </el-tooltip>
                                </div>
                                <div style="color: #64748b; font-size: 11.5px; display: flex; align-items: center; gap: 4px;">
                                    <i class="fa-solid fa-circle-info" style="color: #0284c7;"></i>
                                    <span>正在配置: <b style="color: #c2410c;">节点 {{ activeStepIndex + 1 }}</b> (切换节点仅更换数据, 界面保持不变)</span>
                                </div>
                            </div>

                            <!-- 场景专属变量快速参考与一键引用栏 (支持点击一键插入 Body/URL/Params/Headers) -->
                            <div v-if="scenarioVariablesList.length > 0"
                                style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; margin-bottom: 8px; font-size: 11.5px; flex-wrap: wrap;">
                                <span style="font-weight: 600; color: #1d4ed8; display: flex; align-items: center; gap: 4px; font-size: 11.5px;">
                                    <i class="fa-solid fa-cube"></i>场景专属变量:
                                </span>
                                <el-dropdown trigger="click" v-for="item in scenarioVariablesList" :key="item.key" v-show="item.key">
                                    <span
                                        style="cursor: pointer; background: #ffffff; border: 1px solid #93c5fd; color: #2563eb; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; display: inline-flex; align-items: center; gap: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);"
                                        :title="'变量值: ' + (item.value || '空')">
                                        <span>&#123;&#123;{{ item.key }}&#125;&#125;</span>
                                        <i class="fa-solid fa-caret-down" style="font-size: 9px; opacity: 0.6;"></i>
                                    </span>
                                    <template #dropdown>
                                        <el-dropdown-menu>
                                            <div style="padding: 5px 12px; font-size: 11px; color: #475569; background: #f8fafc; border-bottom: 1px solid #e2e8f0; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                                当前值: <b style="color: #0284c7; font-family: monospace;">{{ item.value || '（空）' }}</b>
                                            </div>
                                            <el-dropdown-item @click="copyVariableMacro(item.key)">
                                                <i class="fa-regular fa-copy" style="margin-right: 6px; color: #64748b;"></i>复制宏 &#123;&#123;{{ item.key }}&#125;&#125;
                                            </el-dropdown-item>
                                            <el-dropdown-item @click="insertScenarioVarToStepBody(item.key)">
                                                <i class="fa-solid fa-code" style="margin-right: 6px; color: #10b981;"></i>插入到请求 Body (JSON)
                                            </el-dropdown-item>
                                            <el-dropdown-item @click="insertScenarioVarToStepPath(item.key)">
                                                <i class="fa-solid fa-link" style="margin-right: 6px; color: #3b82f6;"></i>追加到 URL 路径
                                            </el-dropdown-item>
                                            <el-dropdown-item @click="insertScenarioVarToStepParam(item.key)">
                                                <i class="fa-solid fa-list-check" style="margin-right: 6px; color: #f59e0b;"></i>添加为 URL Query 参数
                                            </el-dropdown-item>
                                            <el-dropdown-item @click="insertScenarioVarToStepHeader(item.key, 'bearer')">
                                                <i class="fa-solid fa-key" style="margin-right: 6px; color: #8b5cf6;"></i>设为 Authorization Bearer
                                            </el-dropdown-item>
                                        </el-dropdown-menu>
                                    </template>
                                </el-dropdown>
                                <div style="margin-left: auto; display: flex; align-items: center; gap: 8px;">
                                    <span style="color: #64748b; font-size: 10.5px;">
                                        点击变量可直接插入 Body / URL / 参数
                                    </span>
                                    <el-button size="small" link type="primary" @click="scenarioVariablesDrawerVisible = true" style="font-size: 11px;">
                                        <i class="fa-solid fa-sliders" style="margin-right: 3px;"></i>管理变量 ({{ scenarioVariablesCount }})
                                    </el-button>
                                </div>
                            </div>

                            <!-- Postman 顶部 URL 请求栏 -->
                            <div class="pm-url-bar">
                                <el-select v-model="activeStep.http_method" class="pm-method-select"
                                    :class="'pm-method-' + activeStep.http_method.toLowerCase()">
                                    <el-option label="GET" value="GET" class="pm-method-get"></el-option>
                                    <el-option label="POST" value="POST" class="pm-method-post"></el-option>
                                    <el-option label="PUT" value="PUT" class="pm-method-put"></el-option>
                                    <el-option label="DELETE" value="DELETE" class="pm-method-delete"></el-option>
                                    <el-option label="PATCH" value="PATCH" class="pm-method-patch"></el-option>
                                </el-select>
                                <div class="pm-baseurl-wrapper" title="当前场景的前置服务基准地址 (支持 http:// 或 https://、域名或IP及端口)">
                                    <el-input v-model="scenarioForm.base_url" class="pm-baseurl-input"
                                        placeholder="http://host:port 或 https://api.domain.com" clearable>
                                        <template #prefix>
                                            <i class="fa-solid fa-globe"
                                                style="color: #64748b; font-size: 12px; margin-right: 2px;"></i>
                                        </template>
                                    </el-input>
                                </div>
                                <el-input v-model="activeStep.http_path" class="pm-path-input"
                                    placeholder="/api/v1/resource?query=val (支持直接粘贴完整URL)" @input="onStepPathInput">
                                </el-input>
                                <el-button type="primary" class="pm-send-btn" :loading="stepTestRunning" @click="handleTestRunStep">
                                    <i class="fa-solid fa-paper-plane"></i>
                                    <span>发送调试</span>
                                </el-button>
                            </div>

                            <!-- Postman 核心配置工作区 (Tabs, 与接口管理一致) -->
                            <el-tabs v-model="stepActiveTab" class="pm-tabs">
                                <!-- 1. Params 标签页 -->
                                <el-tab-pane label="Params" name="params">
                                    <div
                                        style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="font-size: 12px; color: #64748b;">
                                            <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px; color: #3b82f6;"></i>参数与上方
                                            URL Query 参数已双向实时同步 (勾选启用/禁用)
                                        </span>
                                        <div style="display: flex; gap: 6px;">
                                            <el-dropdown trigger="click" @command="insertScenarioVarToStepParam" v-if="scenarioVariablesList.length > 0">
                                                <el-button size="small" type="success" plain title="一键将场景专属变量添加为 URL Query 参数">
                                                    <i class="fa-solid fa-cube" style="margin-right: 4px;"></i>+ 插入场景变量
                                                    <i class="fa-solid fa-angle-down" style="margin-left: 4px; font-size: 10px;"></i>
                                                </el-button>
                                                <template #dropdown>
                                                    <el-dropdown-menu>
                                                        <div style="padding: 5px 12px; font-size: 11px; font-weight: 700; color: #1e40af; background: #eff6ff; border-bottom: 1px solid #dbeafe;">
                                                            选择要添加为 Query 参数的场景变量:
                                                        </div>
                                                        <el-dropdown-item v-for="v in scenarioVariablesList" :key="v.key" :command="v.key" :disabled="!v.key">
                                                            <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; min-width: 200px;">
                                                                <code style="color: #2563eb; font-weight: 700;">{{ v.key }}=&#123;&#123;{{ v.key }}&#125;&#125;</code>
                                                                <span style="color: #64748b; font-size: 11px;">{{ v.value ? '值: ' + v.value : '' }}</span>
                                                            </div>
                                                        </el-dropdown-item>
                                                    </el-dropdown-menu>
                                                </template>
                                            </el-dropdown>
                                            <el-button size="small" type="primary" plain @click="addStepParamRow">
                                                <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加参数
                                            </el-button>
                                        </div>
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
                                            <tr v-for="(item, idx) in activeStep.http_params" :key="idx">
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
                                                    <span class="pm-kv-action-btn" title="删除此行" @click="removeStepParamRow(idx)">
                                                        <i class="fa-solid fa-trash-can"></i>
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </el-tab-pane>

                                <!-- 2. Headers 标签页 -->
                                <el-tab-pane label="Headers" name="headers">
                                    <div class="pm-headers-toolbar">
                                        <div style="display: flex; align-items: center; gap: 8px;">
                                            <el-button size="small" :type="showStepDefaultHeaders ? 'primary' : 'default'" text class="pm-hidden-headers-btn" @click="showStepDefaultHeaders = !showStepDefaultHeaders">
                                                <i :class="showStepDefaultHeaders ? 'fa-solid fa-eye-slash' : 'fa-regular fa-eye'" style="margin-right: 5px;"></i>
                                                <span v-if="showStepDefaultHeaders">隐藏系统默认请求头 ({{ activeScenarioDefaultHeadersCount }})</span>
                                                <span v-else>{{ activeScenarioDefaultHeadersCount }} 个系统默认请求头 (已自动携带)</span>
                                            </el-button>
                                            <span style="font-size: 11px; color: #94a3b8;">
                                                <i class="fa-solid fa-circle-info" style="margin-right: 3px;"></i>发包时系统将自动注入默认请求头，输入同名自定义请求头可直接覆盖
                                            </span>
                                        </div>
                                        <div style="display: flex; gap: 6px;">
                                            <el-dropdown trigger="click" @command="(cmd) => insertScenarioVarToStepHeader(cmd.key, cmd.type)" v-if="scenarioVariablesList.length > 0">
                                                <el-button size="small" type="success" plain title="一键将提取的场景变量应用到请求头 (如 Authorization Bearer)">
                                                    <i class="fa-solid fa-cube" style="margin-right: 4px;"></i>+ 引用场景变量
                                                    <i class="fa-solid fa-angle-down" style="margin-left: 4px; font-size: 10px;"></i>
                                                </el-button>
                                                <template #dropdown>
                                                    <el-dropdown-menu>
                                                        <div style="padding: 5px 12px; font-size: 11px; font-weight: 700; color: #1e40af; background: #eff6ff; border-bottom: 1px solid #dbeafe;">
                                                            选择要引用到请求头的场景变量:
                                                        </div>
                                                        <template v-for="v in scenarioVariablesList" :key="v.key">
                                                            <el-dropdown-item :command="{ key: v.key, type: 'bearer' }">
                                                                <i class="fa-solid fa-key" style="color: #f59e0b; margin-right: 6px;"></i>
                                                                <span>Authorization: Bearer &#123;&#123;{{ v.key }}&#125;&#125;</span>
                                                            </el-dropdown-item>
                                                            <el-dropdown-item :command="{ key: v.key, type: 'token' }">
                                                                <i class="fa-solid fa-ticket" style="color: #0284c7; margin-right: 6px;"></i>
                                                                <span>token: &#123;&#123;{{ v.key }}&#125;&#125;</span>
                                                            </el-dropdown-item>
                                                            <el-dropdown-item :command="{ key: v.key, type: 'custom' }">
                                                                <i class="fa-solid fa-heading" style="color: #3b82f6; margin-right: 6px;"></i>
                                                                <span>{{ v.key }}: &#123;&#123;{{ v.key }}&#125;&#125;</span>
                                                            </el-dropdown-item>
                                                        </template>
                                                    </el-dropdown-menu>
                                                </template>
                                            </el-dropdown>
                                            <el-button size="small" type="primary" plain @click="addStepHeaderRow">
                                                <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加自定义请求头
                                            </el-button>
                                        </div>
                                    </div>

                                    <!-- 默认请求头折叠时的 Postman 风格快捷提醒条 -->
                                    <div v-if="!showStepDefaultHeaders" class="pm-hidden-headers-tip" @click="showStepDefaultHeaders = true">
                                        <i class="fa-regular fa-eye" style="margin-right: 6px; color: #2563eb;"></i>
                                        <span>已自动启用 <strong>{{ activeScenarioDefaultHeadersCount }}</strong> 个 Postman 规范默认请求头 (User-Agent, Accept, Connection, Content-Type 等)</span>
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
                                            <!-- 系统默认请求头列表 (可取消勾选/同名自动覆盖/动态调整) -->
                                            <tr v-if="showStepDefaultHeaders" v-for="(item, idx) in scenarioSystemDefaultHeaders" :key="'sys_' + idx"
                                                class="pm-header-row-sys" :class="{ 'pm-header-overridden': isStepHeaderOverridden(item.key) }">
                                                <td style="text-align: center;">
                                                    <el-checkbox v-model="item.enabled" :disabled="isStepHeaderOverridden(item.key)"></el-checkbox>
                                                </td>
                                                <td>
                                                    <span :style="isStepHeaderOverridden(item.key) ? 'text-decoration: line-through; opacity: 0.6;' : 'font-weight: 600; color: #334155; font-family: monospace; font-size: 12.5px;'">
                                                        {{ item.key }}
                                                    </span>
                                                    <span class="pm-auto-tag">自动生成</span>
                                                    <el-tag v-if="isStepHeaderOverridden(item.key)" size="small" type="warning" effect="plain" class="pm-override-tag">
                                                        <i class="fa-solid fa-arrow-down" style="margin-right: 3px;"></i>已被自定义覆盖
                                                    </el-tag>
                                                </td>
                                                <td>
                                                    <span v-if="item.isCalculated" style="font-size: 12px; color: #64748b; font-style: italic;">&lt;{{ item.value.replace(/[<>]/g, '') }}&gt;</span>
                                                    <el-input v-else v-model="item.value" size="small"></el-input>
                                                </td>
                                                <td>
                                                    <span style="font-size: 11.5px; color: #94a3b8;">{{ item.description }}</span>
                                                </td>
                                                <td></td>
                                            </tr>
                                            <!-- 自定义请求头列表 -->
                                            <tr v-for="(item, idx) in activeStep.http_headers" :key="'cus_' + idx">
                                                <td style="text-align: center;">
                                                    <el-checkbox v-model="item.enabled"></el-checkbox>
                                                </td>
                                                <td>
                                                    <el-input v-model="item.key" placeholder="如 X-Request-Id" size="small"></el-input>
                                                </td>
                                                <td>
                                                    <el-input v-model="item.value" placeholder="如 {{$uuid}} 或固定值" size="small"></el-input>
                                                </td>
                                                <td>
                                                    <el-input v-model="item.description" placeholder="用途说明" size="small"></el-input>
                                                </td>
                                                <td style="text-align: center;">
                                                    <span class="pm-kv-action-btn" title="删除此行" @click="removeStepHeaderRow(idx)">
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
                                        <el-radio-group v-model="activeStep.http_body_type" size="small">
                                            <el-radio-button label="none">none (无 Body)</el-radio-button>
                                            <el-radio-button label="json">raw (JSON)</el-radio-button>
                                            <el-radio-button label="form">x-www-form-urlencoded</el-radio-button>
                                        </el-radio-group>
                                        <div style="flex: 1;"></div>
                                        <div v-if="activeStep.http_body_type === 'json'" style="display: flex; gap: 6px;">
                                            <el-dropdown trigger="click" @command="insertScenarioVarToStepBody" v-if="scenarioVariablesList.length > 0">
                                                <el-button size="small" type="success" plain title="在请求 Body 中一键插入或追加前面步骤提取的场景专属变量">
                                                    <i class="fa-solid fa-cube" style="margin-right: 4px;"></i>+ 插入场景变量
                                                    <i class="fa-solid fa-angle-down" style="margin-left: 4px; font-size: 10px;"></i>
                                                </el-button>
                                                <template #dropdown>
                                                    <el-dropdown-menu>
                                                        <div style="padding: 5px 12px; font-size: 11px; font-weight: 700; color: #1e40af; background: #eff6ff; border-bottom: 1px solid #dbeafe;">
                                                            <i class="fa-solid fa-shield-halved" style="margin-right: 4px;"></i>场景专属变量 (可直接用于 Body)
                                                        </div>
                                                        <el-dropdown-item v-for="v in scenarioVariablesList" :key="v.key" :command="v.key" :disabled="!v.key">
                                                            <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; min-width: 220px;">
                                                                <code style="color: #2563eb; font-weight: 700;">&#123;&#123;{{ v.key }}&#125;&#125;</code>
                                                                <span style="color: #64748b; font-size: 11px; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                                                    {{ v.value ? '值: ' + v.value : '（空值）' }}
                                                                </span>
                                                            </div>
                                                        </el-dropdown-item>
                                                        <el-dropdown-item divided @click="scenarioVariablesDrawerVisible = true">
                                                            <span style="color: #64748b; font-size: 11.5px;"><i class="fa-solid fa-sliders" style="margin-right: 4px;"></i>管理全部场景变量...</span>
                                                        </el-dropdown-item>
                                                    </el-dropdown-menu>
                                                </template>
                                            </el-dropdown>
                                            <el-button size="small" type="primary" plain @click="formatStepBodyJson">
                                                <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>格式化 JSON
                                            </el-button>
                                            <el-button size="small" plain @click="minifyStepBodyJson" title="压缩为紧凑单行格式">
                                                <i class="fa-solid fa-compress" style="margin-right: 4px;"></i>压缩
                                            </el-button>
                                            <el-button size="small" plain @click="clearStepBodyJson" title="清空请求体">
                                                <i class="fa-solid fa-trash-can" style="margin-right: 4px;"></i>清空
                                            </el-button>
                                        </div>
                                        <div v-else-if="activeStep.http_body_type === 'form'" style="display: flex; gap: 6px;">
                                            <el-dropdown trigger="click" @command="insertScenarioVarToStepBody" v-if="scenarioVariablesList.length > 0">
                                                <el-button size="small" type="success" plain title="在表单中一键追加场景专属变量">
                                                    <i class="fa-solid fa-cube" style="margin-right: 4px;"></i>+ 插入场景变量
                                                    <i class="fa-solid fa-angle-down" style="margin-left: 4px; font-size: 10px;"></i>
                                                </el-button>
                                                <template #dropdown>
                                                    <el-dropdown-menu>
                                                        <el-dropdown-item v-for="v in scenarioVariablesList" :key="v.key" :command="v.key" :disabled="!v.key">
                                                            &#123;&#123;{{ v.key }}&#125;&#125;
                                                        </el-dropdown-item>
                                                    </el-dropdown-menu>
                                                </template>
                                            </el-dropdown>
                                        </div>
                                    </div>

                                    <div v-if="activeStep.http_body_type === 'none'"
                                        style="padding: 24px; text-align: center; color: #94a3b8; font-size: 13px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px;">
                                        <i class="fa-solid fa-ban" style="margin-right: 6px;"></i>该请求不携带任何 Body 请求体 (适用 GET/DELETE 等)
                                    </div>

                                    <div v-else-if="activeStep.http_body_type === 'json'" class="pm-code-box">
                                        <el-input v-model="activeStep.http_body" type="textarea" :rows="7"
                                            placeholder="{\n  &quot;userId&quot;: 1001,\n  &quot;action&quot;: &quot;ping&quot;,\n  &quot;traceId&quot;: &quot;{{$uuid}}&quot;,\n  &quot;timestamp&quot;: &quot;{{$timestamp}}&quot;\n}"></el-input>
                                    </div>

                                    <div v-else-if="activeStep.http_body_type === 'form'" class="pm-code-box">
                                        <el-input v-model="activeStep.http_body" type="textarea" :rows="6"
                                            placeholder="key1=value1&amp;key2={{$timestamp}}"></el-input>
                                    </div>
                                </el-tab-pane>

                                <!-- 4. 鉴权与预设宏 标签页 -->
                                <el-tab-pane label="Auth" name="auth">
                                    <div style="margin-bottom: 14px;">
                                        <span
                                            style="font-size: 12px; font-weight: 600; color: #475569; margin-right: 12px;">鉴权认证类型:</span>
                                        <el-radio-group v-model="activeStep.auth_type" size="small">
                                            <el-radio-button label="none">无鉴权 (No Auth)</el-radio-button>
                                            <el-radio-button label="bearer">Bearer Token</el-radio-button>
                                            <el-radio-button label="basic">Basic Auth</el-radio-button>
                                            <el-radio-button label="custom_header">自定义请求头 (Custom Header)</el-radio-button>
                                        </el-radio-group>
                                    </div>

                                    <!-- Bearer Token 配置 -->
                                    <div v-if="activeStep.auth_type === 'bearer'"
                                        style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                                        <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                                            Bearer Token 令牌值
                                            <span style="font-size: 11px; font-weight: normal; color: #64748b; margin-left: 6px;">支持静态
                                                Token 或模板宏 (如 <code v-pre>{{TOKEN}}</code>)</span>
                                        </div>
                                        <el-input v-model="activeStep.auth_config.token" placeholder="ey..." size="small"></el-input>
                                    </div>

                                    <!-- Basic Auth 配置 -->
                                    <div v-if="activeStep.auth_type === 'basic'"
                                        style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                                        <el-row :gutter="12">
                                            <el-col :span="12">
                                                <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">用户名
                                                    (Username)</div>
                                                <el-input v-model="activeStep.auth_config.username" placeholder="admin" size="small"></el-input>
                                            </el-col>
                                            <el-col :span="12">
                                                <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">密码
                                                    (Password)</div>
                                                <el-input v-model="activeStep.auth_config.password" type="password" show-password
                                                    placeholder="••••••" size="small"></el-input>
                                            </el-col>
                                        </el-row>
                                    </div>

                                    <!-- Custom Header 配置 -->
                                    <div v-if="activeStep.auth_type === 'custom_header'"
                                        style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px; margin-bottom: 12px;">
                                        <el-row :gutter="12">
                                            <el-col :span="8">
                                                <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">自定义
                                                    Header 键名</div>
                                                <el-input v-model="activeStep.auth_config.header_key" placeholder="如 X-API-Token / X-Sign"
                                                    size="small"></el-input>
                                            </el-col>
                                            <el-col :span="16">
                                                <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px;">自定义
                                                    Header 键值</div>
                                                <el-input v-model="activeStep.auth_config.header_value" placeholder="Header 对应值"
                                                    size="small"></el-input>
                                            </el-col>
                                        </el-row>
                                    </div>
                                </el-tab-pane>

                                <!-- 5. 前置操作 (Pre-request) 标签页 -->
                                <el-tab-pane label="前置操作" name="pre_actions">
                                    <div class="pm-preset-bar">
                                        <span style="font-size: 12px; color: #64748b; font-weight: 600;">快速预设:</span>
                                        <span class="pm-preset-tag" @click="applyStepPreActionPreset('js_script')"><i class="fa-brands fa-js" style="color: #f59e0b; margin-right: 3px;"></i>+ Postman JS 脚本</span>
                                        <span class="pm-preset-tag" @click="applyStepPreActionPreset('script')"><i class="fa-brands fa-python" style="color: #3b82f6; margin-right: 3px;"></i>+ Python 脚本</span>
                                        <div style="flex: 1;"></div>
                                        <el-button size="small" type="primary" plain @click="addStepPreActionRow">
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
                                            <tr v-if="activeStep.pre_actions.length === 0">
                                                <td colspan="6" style="text-align: center; color: #94a3b8; padding: 20px;">
                                                    <i class="fa-solid fa-bolt"
                                                        style="margin-right: 6px; color: #cbd5e1;"></i>暂无前置操作。可点击上方【添加前置操作】或点击快速预设注入变量与请求头
                                                </td>
                                            </tr>
                                            <tr v-for="(item, idx) in activeStep.pre_actions" :key="idx">
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
                                                    <span class="pm-kv-action-btn" title="删除此行" @click="removeStepPreActionRow(idx)">
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
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('status_200')">+ 状态码等于 200</span>
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('status_2xx')">+ 状态码在 2xx 范围</span>
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('latency_1000')">+ 耗时小于 1000ms</span>
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('json_code')">+ JSON code 等于
                                            200</span>
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('contains_ok')">+ 文本包含 OK</span>
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('extract_var')">+ 提取变量</span>
                                        <span class="pm-preset-tag" @click="applyStepPostActionPreset('js_test')">+ JS 断言</span>
                                        <div style="flex: 1;"></div>
                                        <el-button size="small" type="primary" plain @click="addStepPostActionRow">
                                            <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加后置操作
                                        </el-button>
                                    </div>

                                    <table class="pm-kv-table">
                                        <thead>
                                            <tr>
                                                <th style="width: 45px; text-align: center;">启用</th>
                                                <th style="width: 140px;">断言名称 (Name)</th>
                                                <th style="width: 150px;">断言类型 (Type)</th>
                                                <th style="width: 18%;">表达式 (Expression)</th>
                                                <th style="width: 110px;">操作符 (Operator)</th>
                                                <th>目标值 (Target)</th>
                                                <th style="width: 50px; text-align: center;">操作</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-if="activeStep.post_actions.length === 0">
                                                <td colspan="7" style="text-align: center; color: #94a3b8; padding: 20px;">
                                                    <i class="fa-solid fa-clipboard-check"
                                                        style="margin-right: 6px; color: #cbd5e1;"></i>暂无后置断言。点击上方快速预设或【添加后置操作】配置自动化校验
                                                </td>
                                            </tr>
                                            <tr v-for="(item, idx) in activeStep.post_actions" :key="idx">
                                                <td style="text-align: center;">
                                                    <el-checkbox v-model="item.enabled"></el-checkbox>
                                                </td>
                                                <td>
                                                    <el-input v-model="item.name" placeholder="如 验证响应成功" size="small"></el-input>
                                                </td>
                                                <td>
                                                    <el-select v-model="item.type" size="small" style="width: 100%;"
                                                        @change="onStepPostActionTypeChange(item)">
                                                        <el-option label="状态码断言" value="assert_status_code"></el-option>
                                                        <el-option label="耗时断言" value="assert_latency"></el-option>
                                                        <el-option label="JSON字段断言" value="assert_json_path"></el-option>
                                                        <el-option label="响应头断言" value="assert_header"></el-option>
                                                        <el-option label="内容包含断言" value="assert_body_contains"></el-option>
                                                        <el-option label="提取变量 (Chaining)" value="extract_variable"></el-option>
                                                        <el-option label="JS 脚本断言" value="javascript"></el-option>
                                                    </el-select>
                                                </td>
                                                <td v-if="item.type === 'javascript'" colspan="3">
                                                    <el-input v-model="item.value" type="textarea" :rows="4"
                                                        placeholder="const res = pm.response.json();&#10;if (res.code === 0 && res.data) {&#10;    pm.environment.set('token', res.data.accessToken);&#10;}&#10;pm.test('Status is 200', function () { pm.response.to.have.status(200); });"
                                                        size="small"></el-input>
                                                    <div style="margin-top: 4px;">
                                                        <span style="font-size: 10.5px; color: #94a3b8;">支持 pm.response.json()、pm.environment.set()、pm.test() 等</span>
                                                    </div>
                                                </td>
                                                <template v-else>
                                                    <td>
                                                        <el-input
                                                            v-if="['assert_json_path', 'assert_header', 'extract_variable'].includes(item.type)"
                                                            v-model="item.expression" placeholder="如 code 或 data.id"
                                                            size="small"></el-input>
                                                        <span v-else style="color: #cbd5e1;">—</span>
                                                    </td>
                                                    <td>
                                                        <el-select v-if="item.type !== 'extract_variable'" v-model="item.operator"
                                                            size="small" style="width: 100%;">
                                                            <el-option v-if="item.type === 'assert_status_code'" label="等于" value="equals"></el-option>
                                                            <el-option v-if="item.type === 'assert_status_code'" label="2xx 范围"
                                                                value="in_2xx"></el-option>
                                                            <el-option v-if="['assert_latency', 'assert_status_code'].includes(item.type)"
                                                                label="大于" value="greater_than"></el-option>
                                                            <el-option v-if="['assert_latency', 'assert_status_code'].includes(item.type)"
                                                                label="小于" value="less_than"></el-option>
                                                            <el-option
                                                                v-if="['assert_json_path', 'assert_header', 'assert_body_contains'].includes(item.type)"
                                                                label="包含" value="contains"></el-option>
                                                            <el-option v-if="item.type === 'assert_json_path'" label="非空校验"
                                                                value="not_empty"></el-option>
                                                            <el-option v-if="item.type === 'assert_json_path'" label="类型校验"
                                                                value="type"></el-option>
                                                        </el-select>
                                                        <el-tag v-else size="small" type="success" effect="plain" style="width: 100%; justify-content: center;">提取 → 存入变量</el-tag>
                                                    </td>
                                                    <td>
                                                        <el-input v-model="item.target_value"
                                                            :placeholder="item.type === 'extract_variable' ? '存入变量名 如 token' : '期望值 如 200'"
                                                            size="small"></el-input>
                                                    </td>
                                                </template>
                                                <td style="text-align: center;">
                                                    <span class="pm-kv-action-btn" title="删除此行" @click="removeStepPostActionRow(idx)">
                                                        <i class="fa-solid fa-trash-can"></i>
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>

                                    <div
                                        style="margin-top: 10px; font-size: 11.5px; color: #64748b; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                        <i class="fa-solid fa-circle-info" style="color: #2563eb;"></i>
                                        <span>【提取变量】可将响应数据 (如 <code>data.id</code>) 存入变量, 供后续节点通过 <code v-pre>{{targetId}}</code> 引用, 实现链路参数传递。</span>
                                        <span style="color: #d97706; margin-left: 8px; font-weight: 500;"><i class="fa-brands fa-js" style="margin-right: 3px;"></i>支持 Postman JS: <code>pm.test()</code>、<code>pm.expect()</code>、<code>pm.response.json()</code></span>
                                    </div>
                                </el-tab-pane>
                                <!-- 6. Schema 契约标签页 -->
                                <el-tab-pane label="Schema" name="schema">
                                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                                          <span style="font-size: 12px; color: #64748b;">
                                              标准的 JSON Schema 规范 (Draft-7)，拨测时将自动验证该节点真实响应是否破坏此契约
                                          </span>
                                    <div style="display: flex; gap: 8px;">
                                      <el-button size="small" type="primary" plain @click="formatStepSchemaJson">
                                        <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>格式化 Schema
                                      </el-button>
                                      <el-button size="small" type="primary" plain @click="inferStepSchemaFromTestResult"
                                                 :disabled="!stepTestResult || !stepTestResult.response_data">
                                        <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>从当前响应推导
                                      </el-button>
                                    </div>
                                  </div>
                                  <div class="pm-code-box">
                                    <el-input v-model="activeStep.schema_text" type="textarea" :rows="8"
                                              placeholder="默认留空（不强校验 Schema）。可先发送调试请求后，点击【从当前响应推导】一键自动填入 Draft-7 契约规则"></el-input>
                                  </div>

                                  <!-- 备选手动推导折叠卡片 -->
                                  <div style="margin-top: 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px;">
                                    <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                                      <span><i class="fa-solid fa-code" style="margin-right: 4px; color: #64748b;"></i>从自定义 JSON 样本辅助推导</span>
                                      <div style="display: flex; gap: 6px;">
                                        <el-button size="small" text type="primary" @click="stepSchemaSampleJson = safeFormatJson(stepSchemaSampleJson)"
                                                   :disabled="!stepSchemaSampleJson || !stepSchemaSampleJson.trim()">
                                          <i class="fa-solid fa-align-left" style="margin-right: 4px;"></i>格式化样本
                                        </el-button>
                                        <el-button size="small" text type="primary" @click="inferStepSchemaFromSample" :loading="stepInferring">
                                          <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>执行推导
                                        </el-button>
                                      </div>
                                    </div>
                                    <el-input v-model="stepSchemaSampleJson" type="textarea" :rows="2"
                                              placeholder="在此粘贴外部已有的响应 JSON 文本，点击执行推导即可覆盖上方 Schema 规则"></el-input>
                                  </div>
                                </el-tab-pane>
                            </el-tabs>

                            <!-- 单节点实时调试响应面板 (Live Response Inspector) -->
                            <div class="pm-response-card">
                                <div class="pm-response-header">
                                    <div class="pm-response-meta">
                                        <span style="font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                                            <i class="fa-solid fa-terminal" style="color: #2563eb;"></i>
                                            节点调试响应面板 (Response Preview)
                                        </span>
                                        <template v-if="stepTestResult">
                                            <span class="pm-badge-status"
                                                :class="stepTestResult.status_code >= 200 && stepTestResult.status_code < 300 ? 'pm-badge-2xx' : (stepTestResult.status_code >= 400 && stepTestResult.status_code < 500 ? 'pm-badge-4xx' : (stepTestResult.status_code >= 500 ? 'pm-badge-5xx' : 'pm-badge-5xx'))">
                                                {{ stepTestResult.status_code ? stepTestResult.status_code + ' OK' : 'ERR' }}
                                            </span>
                                            <span class="pm-badge-latency">
                                                <i class="fa-regular fa-clock" style="margin-right: 3px;"></i>{{ stepTestResult.latency_ms || 0 }} ms
                                            </span>
                                            <span v-if="stepTestResult.schema_matched" class="pm-badge-schema-ok">
                                                <i class="fa-solid fa-circle-check"></i> 契约校验通过
                                            </span>
                                            <span v-else-if="stepTestResult.schema_matched === false" class="pm-badge-schema-err"
                                                :title="(stepTestResult.schema_errors || []).map(e => e.message).join('; ')">
                                                <i class="fa-solid fa-circle-exclamation"></i> 契约不匹配
                                            </span>
                                            <span v-else class="pm-badge-schema-plain" style="color: #94a3b8;">
                                                <i class="fa-solid fa-circle-minus"></i> 契约未配置 (可在 Schema 标签页从响应推导)
                                            </span>
                                            <span v-if="stepTestResult.assertions_summary"
                                                :class="stepTestResult.assertions_summary.all_passed ? 'pm-badge-schema-ok' : 'pm-badge-schema-err'"
                                                :title="'共执行 ' + stepTestResult.assertions_summary.total + ' 项断言, 通过 ' + stepTestResult.assertions_summary.passed_count + ' 项'">
                                                <i :class="stepTestResult.assertions_summary.all_passed ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i>
                                                断言 {{ stepTestResult.assertions_summary.passed_count }}/{{ stepTestResult.assertions_summary.total }}
                                            </span>
                                        </template>
                                    </div>

                                    <!-- 响应视图切换: 响应体 vs 提取场景变量 -->
                                    <div v-if="stepTestResult" style="display: flex; align-items: center; gap: 8px;">
                                        <el-radio-group v-model="stepResponseTab" size="small">
                                            <el-radio-button label="body">
                                                <i class="fa-solid fa-file-code" style="margin-right: 4px;"></i>响应体 (Body)
                                            </el-radio-button>
                                            <el-radio-button label="extract">
                                                <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px; color: #3b82f6;"></i>提取场景变量
                                                <span v-if="stepExtractableFields.length"
                                                    style="background: #2563eb; color: #fff; padding: 1px 6px; border-radius: 10px; font-size: 10px; margin-left: 4px;">
                                                    {{ stepExtractableFields.length }}
                                                </span>
                                            </el-radio-button>
                                        </el-radio-group>
                                        <el-button v-if="stepResponseTab === 'body'" size="small" type="primary" plain
                                            @click="stepResponseTab = 'extract'" :disabled="!stepExtractableFields.length"
                                            title="解析响应 JSON，一键将返回字段存为场景专属变量">
                                            <i class="fa-solid fa-cube" style="margin-right: 4px;"></i>从响应提取场景变量
                                        </el-button>
                                    </div>
                                </div>

                                <div v-if="!stepTestResult" class="pm-response-empty">
                                    <i class="fa-solid fa-paper-plane" style="font-size: 24px; color: #cbd5e1; margin-bottom: 8px; display: block;"></i>
                                    点击上方【发送调试】对当前节点即时发包, 查看状态码、耗时、完整响应结果，并直接从响应中提取场景专属变量
                                </div>
                                <template v-else>
                                    <div v-if="stepTestResult.request_url" style="padding: 8px 14px 0; font-size: 11px; color: #64748b; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                        <i class="fa-solid fa-globe" style="color: #0284c7;"></i>
                                        实际请求: <code style="background: #f1f5f9; color: #0284c7; padding: 2px 6px; border-radius: 4px; word-break: break-all;">{{ stepTestResult.request_url }}</code>
                                    </div>
                                    <div v-if="stepTestResult.error" style="margin: 8px 14px 0; padding: 8px 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; font-size: 12px; color: #dc2626;">
                                        <i class="fa-solid fa-circle-exclamation" style="margin-right: 4px;"></i>{{ stepTestResult.error }}
                                    </div>

                                    <!-- 视图 1: 完整响应体 -->
                                    <div v-if="stepResponseTab === 'body'">
                                        <!-- 已提取变量提示栏 -->
                                        <div v-if="stepTestResult.extracted_variables && Object.keys(stepTestResult.extracted_variables).length > 0"
                                            style="margin: 8px 14px 0; padding: 6px 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                                            <div style="display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: #15803d; font-weight: 600;">
                                                <i class="fa-solid fa-circle-check"></i>
                                                <span>本节点已提取变量:</span>
                                                <span v-for="(val, k) in stepTestResult.extracted_variables" :key="k"
                                                    style="background: #dcfce7; border: 1px solid #86efac; color: #166534; padding: 1px 6px; border-radius: 4px; font-family: monospace;">
                                                    &#123;&#123;{{ k }}&#125;&#125;
                                                </span>
                                            </div>
                                            <el-button size="small" link type="success" @click="stepResponseTab = 'extract'">
                                                <i class="fa-solid fa-plus" style="margin-right: 2px;"></i>提取更多字段
                                            </el-button>
                                        </div>

                                        <pre class="pm-response-body">{{ getStepResponseFormattedBody }}</pre>

                                        <div v-if="stepTestResult.assertions_result && stepTestResult.assertions_result.length" style="padding: 0 14px 12px;">
                                            <div style="font-size: 11.5px; font-weight: 600; color: #475569; margin-bottom: 6px;">断言明细:</div>
                                            <div v-for="(a, ai) in stepTestResult.assertions_result" :key="ai"
                                                style="display: flex; align-items: center; gap: 6px; font-size: 11.5px; padding: 2px 0;">
                                                <i :class="a.passed ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"
                                                    :style="{ color: a.passed ? '#10b981' : '#ef4444' }"></i>
                                                <span style="color: #334155;">{{ a.name || a.type }}</span>
                                                <span v-if="!a.passed && a.message" style="color: #dc2626;">{{ a.message }}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- 视图 2: 从当前响应提取场景专属变量 -->
                                    <div v-else-if="stepResponseTab === 'extract'" style="padding: 12px 14px;">
                                        <!-- 说明横幅 -->
                                        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 12px; color: #1e40af; display: flex; align-items: flex-start; gap: 8px;">
                                            <i class="fa-solid fa-circle-info" style="color: #2563eb; margin-top: 2px;"></i>
                                            <div style="line-height: 1.5;">
                                                <b>场景变量提取助手</b>：从下方当前节点的真实响应数据中，点选需要的字段并点击【设为场景变量】。
                                                切换至<b>下一个接口</b>时，即可在 <b>Body、Params、Headers、URL</b> 中一键引用 <code>&#123;&#123;变量名&#125;&#125;</code>，数据完全隔离防污染。
                                            </div>
                                        </div>

                                        <!-- 自定义路径提取行 (针对数组下标或复杂结构) -->
                                        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
                                            <div style="font-size: 11.5px; font-weight: 700; color: #475569; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                                                <i class="fa-solid fa-code-fork" style="color: #3b82f6;"></i>
                                                <span>自定义路径提取 (支持如 <code>data.token</code> 或 <code>data.items[0].id</code>)</span>
                                            </div>
                                            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                                                <el-input v-model="customExtractPath" placeholder="提取字段路径，如 data.token 或 list[0].id" size="small" style="width: 260px;"></el-input>
                                                <el-input v-model="customExtractVarName" placeholder="保存为场景变量名，如 token" size="small" style="width: 180px;"></el-input>
                                                <div v-if="customExtractPreview !== null" style="font-size: 11.5px; color: #0284c7; background: #e0f2fe; padding: 3px 8px; border-radius: 4px; font-family: monospace;">
                                                    实时预览: <b>{{ String(customExtractPreview).length > 25 ? String(customExtractPreview).slice(0, 25) + '...' : customExtractPreview }}</b>
                                                </div>
                                                <el-button size="small" type="primary" @click="addCustomExtractToScenarioVariable" :disabled="!customExtractPath || !customExtractVarName">
                                                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加并设为场景变量
                                                </el-button>
                                            </div>
                                        </div>

                                        <!-- 响应叶子字段解析表 -->
                                        <div style="margin-bottom: 6px; font-size: 12px; font-weight: 600; color: #334155; display: flex; align-items: center; justify-content: space-between;">
                                            <span>
                                                <i class="fa-solid fa-list-check" style="margin-right: 4px; color: #10b981;"></i>
                                                响应字段列表 (点击【设为场景变量】即完成配置，后续节点一键引用)
                                            </span>
                                            <span style="font-size: 11px; color: #64748b;">共发现 {{ stepExtractableFields.length }} 个数据字段</span>
                                        </div>

                                        <div v-if="!stepExtractableFields.length" style="text-align: center; color: #94a3b8; padding: 24px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; font-size: 12px;">
                                            当前响应不是标准 JSON 对象或未解析出字段，可使用上方【自定义路径提取】。
                                        </div>

                                        <el-table v-else :data="stepExtractableFields" size="small" border style="width: 100%; max-height: 240px; overflow-y: auto;">
                                            <el-table-column label="字段路径 (JSONPath)" prop="path" min-width="160">
                                                <template #default="{ row }">
                                                    <code style="font-weight: 600; color: #0f172a; font-size: 11.5px;">{{ row.path }}</code>
                                                </template>
                                            </el-table-column>
                                            <el-table-column label="当前返回值 (Sample Value)" min-width="170">
                                                <template #default="{ row }">
                                                    <span style="font-family: monospace; font-size: 11.5px; color: #0284c7; word-break: break-all;">
                                                        {{ typeof row.value === 'object' ? JSON.stringify(row.value) : String(row.value ?? 'null') }}
                                                    </span>
                                                </template>
                                            </el-table-column>
                                            <el-table-column label="存入场景变量名 (可修改)" min-width="170">
                                                <template #default="{ row }">
                                                    <el-input v-model="stepExtractedVarNames[row.path]" size="small"
                                                        placeholder="如 token 或 userId" style="font-family: monospace;">
                                                        <template #prepend><span style="font-size: 10px;">&#123;&#123;</span></template>
                                                        <template #append><span style="font-size: 10px;">&#125;&#125;</span></template>
                                                    </el-input>
                                                </template>
                                            </el-table-column>
                                            <el-table-column label="操作" width="160" align="center">
                                                <template #default="{ row }">
                                                    <div v-if="isFieldExtractedInActiveStep(row.path, stepExtractedVarNames[row.path])" style="display: flex; align-items: center; justify-content: center; gap: 6px;">
                                                        <el-tag size="small" type="success" effect="plain" style="font-weight: 600;">
                                                            <i class="fa-solid fa-check" style="margin-right: 2px;"></i>已设为变量
                                                        </el-tag>
                                                        <el-button size="small" link type="primary" @click="copyVariableMacro(stepExtractedVarNames[row.path])" title="复制宏到剪贴板">
                                                            复制宏
                                                        </el-button>
                                                    </div>
                                                    <el-button v-else size="small" type="primary" plain @click="quickExtractFieldToScenarioVariable(row)">
                                                        <i class="fa-solid fa-plus" style="margin-right: 3px;"></i>设为场景变量
                                                    </el-button>
                                                </template>
                                            </el-table-column>
                                        </el-table>
                                    </div>
                                </template>
                            </div>
                        </template>
                        <div v-else
                            style="padding: 24px; text-align: center; color: #94a3b8; font-size: 13px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px;">
                            <i class="fa-solid fa-hand-pointer" style="margin-right: 6px;"></i>请先在上方业务链路步骤中添加并选中一个节点
                        </div>

                        <template #footer>
                            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                                <div style="font-size: 12px; color: #64748b;">
                                    <i class="fa-solid fa-shield-halved" style="color: #10b981; margin-right: 4px;"></i>
                                    场景已绑定宿主节点，拨测执行引擎将按节点顺序调用并保证清理步骤执行
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <el-button @click="scenarioDialogVisible = false">取消</el-button>
                                    <el-button type="primary" @click="submitScenarioForm" :loading="scenarioSubmitting">
                                        {{ editingScenarioId ? '保存修改' : '创建场景' }}
                                    </el-button>
                                </div>
                            </div>
                        </template>
                    </el-dialog>

                    <!-- ================= 场景专属变量管理弹窗 (仅限本场景生效, 隔离防污染) ================= -->
                    <el-dialog v-model="scenarioVariablesDrawerVisible" title="场景专属变量管理" width="760px"
                        class="postman-dialog" append-to-body destroy-on-close>
                        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;">
                            <div style="font-size: 13px; font-weight: 700; color: #1e40af; margin-bottom: 5px; display: flex; align-items: center; gap: 6px;">
                                <i class="fa-solid fa-shield-halved" style="color: #2563eb;"></i>
                                <span>场景变量作用域与隔离保护说明</span>
                                <el-tag size="small" type="primary" effect="plain" style="margin-left: 4px; font-weight: 600;">仅本场景生效 · 隔离防污染</el-tag>
                            </div>
                            <div style="font-size: 12px; color: #1d4ed8; line-height: 1.6;">
                                <div><b>1. 场景内链路传递</b>: 此处定义的变量仅在当前场景执行过程中生效。步骤 1 后置提取（<code>extract_variable</code>）的数据会自动写入本变量池，步骤 2 及后续步骤可在请求路径、参数、请求头或 Body 中通过 <code>&#123;&#123;变量名&#125;&#125;</code> 宏直接引用。</div>
                                <div style="margin-top: 3px;"><b>2. 绝对隔离防污染</b>: 场景整链执行与单步调试过程中的变量更新严格局限于本场景运行时，<b>绝不回写、修改或污染全局环境变量，也绝不影响其他接口与其他拨测场景</b>。</div>
                            </div>
                        </div>

                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <div style="font-size: 12.5px; font-weight: 600; color: #334155; display: flex; align-items: center; gap: 6px;">
                                <i class="fa-solid fa-cube" style="color: #3b82f6;"></i>
                                <span>当前场景变量列表</span>
                                <el-tag size="small" type="info" effect="plain">{{ scenarioVariablesCount }} 个已配置</el-tag>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <el-button size="small" type="primary" plain @click="addScenarioVariableRow">
                                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加变量
                                </el-button>
                                <el-button size="small" type="danger" plain @click="clearScenarioVariables" :disabled="!scenarioVariablesList.length">
                                    <i class="fa-solid fa-trash" style="margin-right: 4px;"></i>清空全部
                                </el-button>
                            </div>
                        </div>

                        <el-table :data="scenarioVariablesList" size="small" border style="width: 100%;" empty-text="暂无场景专属变量，可点击右上角【添加变量】，或在节点调试中通过后置提取自动注入">
                            <el-table-column label="启用" width="55" align="center">
                                <template #default="{ row }">
                                    <el-checkbox v-model="row.enabled"></el-checkbox>
                                </template>
                            </el-table-column>
                            <el-table-column label="变量名 (Key)" min-width="170">
                                <template #default="{ row }">
                                    <el-input v-model="row.key" placeholder="如: userId, token" size="small"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="默认初始值 (Value)" min-width="200">
                                <template #default="{ row }">
                                    <el-input v-model="row.value" placeholder="初始默认值 (可选)" size="small"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="说明 (Description)" min-width="150">
                                <template #default="{ row }">
                                    <el-input v-model="row.description" placeholder="用途说明 (可选)" size="small"></el-input>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="90" align="center">
                                <template #default="{ row, $index }">
                                    <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                        <el-button link type="primary" size="small" @click="copyVariableMacro(row.key)" :disabled="!row.key" title="复制宏 {{变量名}}">
                                            <i class="fa-regular fa-copy"></i>
                                        </el-button>
                                        <el-button link type="danger" size="small" @click="removeScenarioVariableRow($index)" title="删除该变量">
                                            <i class="fa-solid fa-trash-can"></i>
                                        </el-button>
                                    </div>
                                </template>
                            </el-table-column>
                        </el-table>

                        <template #footer>
                            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                                <div style="font-size: 11.5px; color: #64748b;">
                                    <i class="fa-solid fa-lightbulb" style="color: #f59e0b; margin-right: 3px;"></i>
                                    在后续节点中直接写入 <code style="background: #f1f5f9; color: #2563eb; padding: 1px 4px; border-radius: 3px;">&#123;&#123;变量名&#125;&#125;</code> 即可插值替换
                                </div>
                                <el-button type="primary" @click="scenarioVariablesDrawerVisible = false">完成</el-button>
                            </div>
                        </template>
                    </el-dialog>

                    <!-- ================= 从接口管理导入接口为链路节点 ================= -->
                    <el-dialog v-model="apiImportDialogVisible" title="从接口管理导入" width="780px" top="8vh"
                        class="postman-dialog" append-to-body destroy-on-close>
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;">
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <el-input v-model="apiImportSearch" size="small" placeholder="搜索接口名称 / 路径 / 机器" clearable style="width: 220px;">
                                    <template #prefix><i class="fa-solid fa-magnifying-glass" style="color: #94a3b8;"></i></template>
                                </el-input>
                                <el-select v-model="apiImportMethodFilter" size="small" style="width: 110px;">
                                    <el-option label="全部方法" value="ALL"></el-option>
                                    <el-option label="GET" value="GET"></el-option>
                                    <el-option label="POST" value="POST"></el-option>
                                    <el-option label="PUT" value="PUT"></el-option>
                                    <el-option label="DELETE" value="DELETE"></el-option>
                                    <el-option label="PATCH" value="PATCH"></el-option>
                                </el-select>
                            </div>
                            <span style="font-size: 11.5px; color: #64748b;">
                                共 <b style="color: #0f172a;">{{ importableApis.length }}</b> 个接口 · 已选 <b style="color: #c2410c;">{{ apiImportSelection.length }}</b> 个
                            </span>
                        </div>

                        <el-table ref="apiImportTableRef" :data="importableApis" row-key="id" size="small" max-height="380"
                            @selection-change="handleApiImportSelectionChange"
                            empty-text="接口管理中暂无接口，请先在【接口管理】页面创建">
                            <el-table-column type="selection" :reserve-selection="true" width="42"></el-table-column>
                            <el-table-column label="方法" width="80">
                                <template #default="{ row }">
                                    <span style="font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 3px; display: inline-block;"
                                        :style="getMethodBadgeStyle(row.http_method)">{{ row.http_method }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="接口名称" min-width="140">
                                <template #default="{ row }">
                                    <span style="font-weight: 600; color: #0f172a; font-size: 12.5px;">{{ row.name }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="请求路径" min-width="190">
                                <template #default="{ row }">
                                    <code style="font-size: 11px; color: #0284c7; background: #f1f5f9; padding: 1px 6px; border-radius: 4px; word-break: break-all;">{{ row.http_path }}</code>
                                </template>
                            </el-table-column>
                            <el-table-column label="契约校验" width="90" align="center">
                                <template #default="{ row }">
                                    <el-tag v-if="row.last_schema_matched === true" type="success" size="small">一致</el-tag>
                                    <el-tag v-else-if="row.last_schema_matched === false" type="danger" size="small">突变</el-tag>
                                    <el-tag v-else-if="!row.schema_configured" type="info" effect="plain" size="small">未配置</el-tag>
                                    <span v-else style="color: var(--text-muted); font-size: 12px;">未校验</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="归属" width="150">
                                <template #default="{ row }">
                                    <div style="font-size: 11.5px; color: #475569;">{{ row.machine_name }}</div>
                                    <div style="font-size: 10.5px; color: #94a3b8;">{{ row.environment_name }}</div>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="110" fixed="right">
                                <template #default="{ row }">
                                    <el-tooltip content="用该接口的配置覆盖填充当前选中的链路节点" placement="top">
                                        <el-button size="small" link type="primary" @click="fillActiveStepFromApi(row)">填入当前节点</el-button>
                                    </el-tooltip>
                                </template>
                            </el-table-column>
                        </el-table>

                        <div style="margin-top: 10px; font-size: 11.5px; color: #64748b; display: flex; align-items: flex-start; gap: 6px;">
                            <i class="fa-solid fa-circle-info" style="color: #2563eb; margin-top: 1px;"></i>
                            <span>导入将完整复制接口的路径、Params、Headers、Body、鉴权与前置/后置操作配置；请求地址将使用当前场景的基准地址 (宿主机器)。批量导入时 DELETE 接口将自动标记为清理步骤。</span>
                        </div>

                        <template #footer>
                            <div style="display: flex; justify-content: flex-end; gap: 10px;">
                                <el-button @click="apiImportDialogVisible = false">取消</el-button>
                                <el-button type="primary" :disabled="apiImportSelection.length === 0" @click="confirmImportApisAsSteps">
                                    <i class="fa-solid fa-circle-plus" style="margin-right: 4px;"></i>添加为节点 ({{ apiImportSelection.length }})
                                </el-button>
                            </div>
                        </template>
                    </el-dialog>

                    <!-- ================= 场景拨测执行结果抽屉 ================= -->
                    <el-drawer v-model="scenarioResultVisible" size="520px"
                        :title="scenarioResult ? '拨测执行详情' : '拨测执行详情'">
                        <template v-if="scenarioResult">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap;">
                                <span class="pm-badge-status" :class="scenarioResult.is_success ? 'pm-badge-2xx' : 'pm-badge-5xx'">
                                    <i :class="scenarioResult.is_success ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'" style="margin-right: 4px;"></i>
                                    {{ scenarioResult.is_success ? '链路拨测通过' : '链路存在失败节点' }}
                                </span>
                                <span class="pm-badge-latency">
                                    <i class="fa-regular fa-clock" style="margin-right: 3px;"></i>总耗时 {{ scenarioResult.total_latency_ms || 0 }} ms
                                </span>
                                <el-tag size="small" :type="scenarioResult.trigger === 'manual' ? 'primary' : 'info'" effect="plain">
                                    {{ scenarioResult.trigger === 'manual' ? '手动触发' : '定时调度' }}
                                </el-tag>
                                <span style="font-size: 11.5px; color: #94a3b8;">{{ (scenarioResult.probed_at || '').replace('T', ' ').slice(0, 19) }}</span>
                            </div>
                            <div v-if="scenarioResult.error_message"
                                style="margin-bottom: 12px; padding: 8px 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; font-size: 12px; color: #dc2626;">
                                <i class="fa-solid fa-circle-exclamation" style="margin-right: 4px;"></i>{{ scenarioResult.error_message }}
                            </div>

                            <!-- 场景运行时变量池快照 (隔离生效) -->
                            <div v-if="scenarioResult.scenario_variables && Object.keys(scenarioResult.scenario_variables).length"
                                style="margin-bottom: 14px; padding: 10px 12px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;">
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                                    <div style="font-size: 12px; font-weight: 700; color: #1e40af; display: flex; align-items: center; gap: 5px;">
                                        <i class="fa-solid fa-cube" style="color: #2563eb;"></i>
                                        <span>场景运行时变量池快照</span>
                                    </div>
                                    <el-tag size="small" type="primary" effect="plain" style="font-size: 10px; font-weight: 600;">隔离保护生效中</el-tag>
                                </div>
                                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                                    <el-tag v-for="(v, k) in scenarioResult.scenario_variables" :key="k" size="small" type="primary" effect="light">
                                        <span style="font-weight: 700;">{{ k }}</span> = {{ v }}
                                    </el-tag>
                                </div>
                            </div>

                            <!-- 节点执行时间线 -->
                            <div v-for="(d, idx) in scenarioResult.steps_detail" :key="idx"
                                style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; background: #ffffff;">
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">
                                    <span style="font-size: 10.5px; color: #94a3b8;">节点 {{ (d.step_index ?? idx) + 1 }}</span>
                                    <span style="font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 3px;"
                                        :style="getMethodBadgeStyle(d.http_method)">{{ d.http_method }}</span>
                                    <span style="font-weight: 600; color: #0f172a; font-size: 12.5px;">{{ d.name }}</span>
                                    <el-tag v-if="d.is_cleanup" size="small" type="warning" effect="plain">
                                        <i class="fa-solid fa-broom" style="margin-right: 2px;"></i>清理步骤
                                    </el-tag>
                                    <span style="font-size: 10.5px; font-weight: 700; padding: 1px 8px; border-radius: 10px; margin-left: auto;"
                                        :style="getStepResultBadge(d).style">{{ getStepResultBadge(d).text }}</span>
                                </div>
                                <div style="font-size: 11px; color: #64748b; margin-bottom: 6px; word-break: break-all;">
                                    <code style="background: #f1f5f9; color: #0284c7; padding: 1px 6px; border-radius: 4px;">{{ d.http_path }}</code>
                                    <template v-if="d.status_code !== null && d.status_code !== undefined">
                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                        HTTP <b :style="{ color: d.ok ? '#059669' : '#dc2626' }">{{ d.status_code }}</b>
                                    </template>
                                    <template v-if="d.latency_ms !== null && d.latency_ms !== undefined">
                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                        {{ d.latency_ms }} ms
                                    </template>
                                    <template v-if="d.schema_configured">
                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                        <span v-if="d.schema_matched" style="color: #059669; font-weight: 600;">
                                            <i class="fa-solid fa-circle-check" style="margin-right: 2px;"></i>契约通过
                                        </span>
                                        <span v-else style="color: #dc2626; font-weight: 600;">
                                            <i class="fa-solid fa-circle-exclamation" style="margin-right: 2px;"></i>契约突变
                                        </span>
                                    </template>
                                    <template v-else>
                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                        <span style="color: #94a3b8; font-size: 11px;">契约未配置</span>
                                    </template>
                                </div>
                                <div v-if="d.schema_matched === false && (d.schema_errors || []).length"
                                    style="font-size: 11px; color: #dc2626; margin-bottom: 4px;">
                                    <span v-for="(se, sei) in d.schema_errors.slice(0, 3)" :key="sei" style="display: block; padding-left: 2px;">
                                        · {{ se.field }}: {{ se.message }}
                                    </span>
                                </div>
                                <div v-if="d.error" style="font-size: 11.5px; color: #dc2626; margin-bottom: 4px;">
                                    <i class="fa-solid fa-circle-exclamation" style="margin-right: 3px;"></i>{{ d.error }}
                                </div>
                                <div v-if="d.skipped" style="font-size: 11.5px; color: #94a3b8;">
                                    <i class="fa-solid fa-forward" style="margin-right: 3px;"></i>前序节点失败, 该节点未执行
                                </div>
                                <div v-if="d.assertions_summary && d.assertions_summary.total > 0" style="font-size: 11.5px; margin-bottom: 4px;">
                                    <i :class="d.assertions_summary.all_passed ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"
                                        :style="{ color: d.assertions_summary.all_passed ? '#10b981' : '#ef4444', marginRight: '3px' }"></i>
                                    <span :style="{ color: d.assertions_summary.all_passed ? '#059669' : '#dc2626' }">
                                        断言 {{ d.assertions_summary.passed_count }}/{{ d.assertions_summary.total }} 通过
                                    </span>
                                    <span v-for="(a, ai) in (d.assertions_result || []).filter(x => !x.passed)" :key="ai"
                                        style="display: block; color: #dc2626; padding-left: 16px;">
                                        · {{ a.name }}: {{ a.message || '未通过' }}
                                    </span>
                                </div>
                                <div v-if="d.extracted_variables && Object.keys(d.extracted_variables).length"
                                    style="font-size: 11.5px; color: #1d4ed8; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                    <i class="fa-solid fa-link" style="color: #2563eb;"></i>提取变量:
                                    <el-tag v-for="(v, k) in d.extracted_variables" :key="k" size="small" effect="plain" type="primary">
                                        {{ k }} = {{ v }}
                                    </el-tag>
                                </div>
                                <div v-if="d.response_snippet" style="margin-top: 6px;">
                                    <pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; font-size: 10.5px; color: #475569; max-height: 140px; overflow: auto; margin: 0; white-space: pre-wrap; word-break: break-all;">{{ d.response_snippet }}</pre>
                                </div>
                            </div>
                        </template>
                        <div v-else style="text-align: center; color: #94a3b8; padding: 40px 0; font-size: 13px;">
                            <i class="fa-solid fa-clipboard-check" style="font-size: 26px; margin-bottom: 10px; display: block;"></i>
                            暂无执行数据
                        </div>
                    </el-drawer>

                    <!-- ================= 场景时序排障报表与历史流水抽屉 ================= -->
                    <el-drawer v-model="scenarioMetricsDrawerVisible"
                        :title="activeScenarioMetrics ? '场景专属时序排障报表 - ' + activeScenarioMetrics.name : '场景时序排障'"
                        size="70%" destroy-on-close>
                        <div v-if="activeScenarioMetrics" v-loading="scenarioMetricsLoading">
                            <!-- 场景专属档案信息卡片 -->
                            <div
                                style="background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%); padding: 14px 18px; border-radius: 8px; border: 1px solid #fed7aa; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(249,115,22,0.06);">
                                <div
                                    style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                        <el-tag type="warning" effect="dark" style="font-weight: 700; font-size: 11.5px;">
                                            <i class="fa-solid fa-diagram-project" style="margin-right: 4px;"></i>业务链路
                                        </el-tag>
                                        <span style="font-size: 15.5px; font-weight: 700; color: #0f172a;">{{ activeScenarioMetrics.name }}</span>
                                        <el-tag size="small" type="primary" effect="light" style="font-weight: 600;">
                                            {{ activeScenarioMetrics.environment_name || '默认环境' }}
                                        </el-tag>
                                        <span :class="getScenarioStatusBadgeClass(activeScenarioMetrics.last_status)" style="font-size: 11px;">
                                            <i :class="activeScenarioMetrics.last_status === 'HEALTHY' ? 'fa-solid fa-circle-check' : (activeScenarioMetrics.last_status === 'FAIL' || activeScenarioMetrics.last_status === 'DOWN' ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-clock')"
                                                style="margin-right: 3px;"></i>
                                            {{ getScenarioStatusText(activeScenarioMetrics.last_status) }}
                                        </span>
                                    </div>
                                    <div style="font-size: 12px; color: #64748b;">
                                        <i class="fa-solid fa-clock" style="margin-right: 4px; color: #f97316;"></i>巡检周期:
                                        <span v-if="activeScenarioMetrics.is_active === false" style="color: #ef4444; font-weight: 600;">已关闭自动拨测 (仅手动)</span>
                                        <span v-else>每 {{ activeScenarioMetrics.cron_interval_minutes }} 分钟自动巡检</span>
                                    </div>
                                </div>
                                <div
                                    style="display: flex; gap: 16px; font-size: 12px; color: #334155; background: #ffffff; padding: 8px 12px; border-radius: 6px; border: 1px solid #fed7aa; flex-wrap: wrap; align-items: center;">
                                    <div>
                                        <span style="color: #64748b;">绑定宿主机:</span>
                                        <b style="color: #0f172a; margin-left: 4px;">
                                            <i class="fa-solid fa-server" style="color: #10b981; margin-right: 3px;"></i>{{ activeScenarioMetrics.machine_name || ('机器#' + activeScenarioMetrics.machine_id) }}
                                        </b>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">链路节点数:</span>
                                        <b style="color: #0f172a; margin-left: 4px;">{{ activeScenarioMetrics.step_count || (activeScenarioMetrics.steps ? activeScenarioMetrics.steps.length : 0) }} 个节点</b>
                                    </div>
                                    <div v-if="activeScenarioMetrics.last_latency_ms !== null && activeScenarioMetrics.last_latency_ms !== undefined">
                                        <span style="color: #64748b;">最近整链耗时:</span>
                                        <b style="color: #ea580c; margin-left: 4px;">{{ activeScenarioMetrics.last_latency_ms }} ms</b>
                                    </div>
                                    <div>
                                        <span style="color: #64748b;">契约状态:</span>
                                        <span v-if="activeScenarioMetrics.last_schema_matched === true" style="color: #059669; font-weight: 600; margin-left: 4px;">
                                            <i class="fa-solid fa-circle-check" style="margin-right: 2px;"></i>契约一致
                                        </span>
                                        <span v-else-if="activeScenarioMetrics.last_schema_matched === false" style="color: #dc2626; font-weight: 600; margin-left: 4px;">
                                            <i class="fa-solid fa-triangle-exclamation" style="margin-right: 2px;"></i>契约突变
                                        </span>
                                        <span v-else style="color: #94a3b8; margin-left: 4px;">
                                            {{ activeScenarioMetrics.schema_configured ? '待首次校验' : '未配置契约' }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <!-- ECharts 趋势图表卡片 -->
                            <div
                                style="background: #ffffff; padding: 18px 20px; border-radius: 8px; border: 1px solid #fed7aa; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(249,115,22,0.04);">
                                <div
                                    style="font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; color: #0f172a;">
                                    <span>
                                        <i class="fa-solid fa-chart-line" style="color: #f97316; margin-right: 6px;"></i>该场景历史耗时与执行趋势 (最近100次)
                                    </span>
                                    <span style="font-size: 12px; color: #64748b; font-weight: normal;">支持悬浮查看触发源、节点状态与契约结果</span>
                                </div>
                                <div id="scenarioChartContainer" style="width: 100%; height: 260px;"></div>
                            </div>

                            <!-- 场景历史流水明细 -->
                            <div
                                style="font-weight: 600; font-size: 14px; margin-bottom: 10px; color: #0f172a; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <i class="fa-solid fa-clock-rotate-left" style="color: #f97316; margin-right: 6px;"></i>场景专属探测日志 (展开行查看各步骤现场、契约校验与提取变量)
                                </div>
                                <el-tag size="small" type="warning" effect="plain">{{ scenarioHistoryList.length }} 条运行流水</el-tag>
                            </div>

                            <el-table :data="scenarioHistoryList" style="width: 100%" size="small"
                                empty-text="当前场景暂无探测历史，可点击列表【执行】立即生成探测流水">
                                <el-table-column type="expand">
                                    <template #default="{ row: hRow }">
                                        <div style="padding: 12px 18px; background: #fffaf5; border-radius: 6px; border: 1px solid #fed7aa;">
                                            <div v-if="hRow.error_message" style="margin-bottom: 10px; padding: 8px 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; color: #dc2626; font-size: 12px;">
                                                <i class="fa-solid fa-circle-exclamation" style="margin-right: 4px;"></i>整链异常: {{ hRow.error_message }}
                                            </div>
                                            <!-- 场景运行时变量池快照 -->
                                            <div v-if="hRow.scenario_variables && Object.keys(hRow.scenario_variables).length"
                                                style="margin-bottom: 10px; padding: 8px 12px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; font-size: 11.5px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                                <span style="font-weight: 600; color: #1e40af; display: flex; align-items: center; gap: 4px;">
                                                    <i class="fa-solid fa-cube"></i>场景变量快照:
                                                </span>
                                                <el-tag v-for="(v, k) in hRow.scenario_variables" :key="k" size="small" type="primary" effect="plain">
                                                    <b>{{ k }}</b> = {{ v }}
                                                </el-tag>
                                            </div>
                                            <div style="font-weight: 600; font-size: 12.5px; color: #334155; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                                                <i class="fa-solid fa-list-check" style="color: #f97316;"></i>步骤执行快照 (共 {{ (hRow.steps_detail || []).length }} 步):
                                            </div>
                                            <div v-for="(sd, sIdx) in (hRow.steps_detail || [])" :key="sIdx"
                                                style="padding: 10px 12px; margin-bottom: 8px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 12px;">
                                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                                    <span style="font-size: 11px; color: #94a3b8; font-weight: 600;">#{{ sIdx + 1 }}</span>
                                                    <span style="font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 3px;"
                                                        :style="getMethodBadgeStyle(sd.http_method)">{{ sd.http_method }}</span>
                                                    <span style="font-weight: 600; color: #0f172a;">{{ sd.name }}</span>
                                                    <el-tag v-if="sd.is_cleanup" size="small" type="warning" effect="plain">
                                                        <i class="fa-solid fa-broom" style="margin-right: 2px;"></i>清理步骤
                                                    </el-tag>
                                                    <span style="margin-left: auto; font-size: 11px; font-weight: 700; padding: 1px 8px; border-radius: 10px;"
                                                        :style="getStepResultBadge(sd).style">{{ getStepResultBadge(sd).text }}</span>
                                                </div>
                                                <div style="font-size: 11.5px; color: #64748b; margin-bottom: 6px; word-break: break-all;">
                                                    <code style="background: #f1f5f9; color: #0284c7; padding: 1px 6px; border-radius: 4px;">{{ sd.http_path }}</code>
                                                    <template v-if="sd.status_code !== null && sd.status_code !== undefined">
                                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                                        HTTP <b :style="{ color: sd.ok ? '#059669' : '#dc2626' }">{{ sd.status_code }}</b>
                                                    </template>
                                                    <template v-if="sd.latency_ms !== null && sd.latency_ms !== undefined">
                                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                                        {{ sd.latency_ms }} ms
                                                    </template>
                                                    <template v-if="sd.schema_configured">
                                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                                        <span v-if="sd.schema_matched" style="color: #059669; font-weight: 600;">
                                                            <i class="fa-solid fa-circle-check" style="margin-right: 2px;"></i>契约通过
                                                        </span>
                                                        <span v-else style="color: #dc2626; font-weight: 600;">
                                                            <i class="fa-solid fa-circle-exclamation" style="margin-right: 2px;"></i>契约突变
                                                        </span>
                                                    </template>
                                                    <template v-else>
                                                        <span style="margin: 0 6px; color: #cbd5e1;">|</span>
                                                        <span style="color: #94a3b8; font-size: 11px;">契约未配置</span>
                                                    </template>
                                                </div>
                                                <div v-if="sd.schema_matched === false && (sd.schema_errors || []).length"
                                                    style="font-size: 11px; color: #dc2626; margin-bottom: 4px; padding-left: 2px;">
                                                    <span v-for="(se, sei) in sd.schema_errors.slice(0, 3)" :key="sei" style="display: block;">
                                                        · 破坏性变更: [{{ se.field }}] {{ se.message }}
                                                    </span>
                                                </div>
                                                <div v-if="sd.error" style="font-size: 11.5px; color: #dc2626; margin-bottom: 4px;">
                                                    <i class="fa-solid fa-circle-exclamation" style="margin-right: 3px;"></i>{{ sd.error }}
                                                </div>
                                                <div v-if="sd.skipped" style="font-size: 11.5px; color: #94a3b8;">
                                                    <i class="fa-solid fa-forward" style="margin-right: 3px;"></i>前序节点失败, 该节点未执行
                                                </div>
                                                <div v-if="sd.assertions_summary && sd.assertions_summary.total > 0" style="font-size: 11.5px; margin-bottom: 4px;">
                                                    <i :class="sd.assertions_summary.all_passed ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"
                                                        :style="{ color: sd.assertions_summary.all_passed ? '#10b981' : '#ef4444', marginRight: '3px' }"></i>
                                                    <span :style="{ color: sd.assertions_summary.all_passed ? '#059669' : '#dc2626' }">
                                                        断言 {{ sd.assertions_summary.passed_count }}/{{ sd.assertions_summary.total }} 通过
                                                    </span>
                                                    <span v-for="(a, ai) in (sd.assertions_result || []).filter(x => !x.passed)" :key="ai"
                                                        style="display: block; color: #dc2626; padding-left: 16px;">
                                                        · {{ a.name }}: {{ a.message || '未通过' }}
                                                    </span>
                                                </div>
                                                <div v-if="sd.extracted_variables && Object.keys(sd.extracted_variables).length"
                                                    style="font-size: 11.5px; color: #1d4ed8; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 4px;">
                                                    <i class="fa-solid fa-link" style="color: #2563eb;"></i>提取变量:
                                                    <el-tag v-for="(v, k) in sd.extracted_variables" :key="k" size="small" effect="plain" type="primary">
                                                        {{ k }} = {{ v }}
                                                    </el-tag>
                                                </div>
                                                <div v-if="sd.response_snippet" style="margin-top: 6px;">
                                                    <pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 8px; font-size: 10.5px; color: #475569; max-height: 120px; overflow: auto; margin: 0; white-space: pre-wrap; word-break: break-all;">{{ sd.response_snippet }}</pre>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </el-table-column>
                                <el-table-column label="执行时间" width="160">
                                    <template #default="{ row: hRow }">{{ formatTime(hRow.probed_at) }}</template>
                                </el-table-column>
                                <el-table-column label="触发方式" width="95" align="center">
                                    <template #default="{ row: hRow }">
                                        <el-tag v-if="hRow.trigger === 'manual'" size="small" type="primary" effect="plain">手动触发</el-tag>
                                        <el-tag v-else size="small" type="info" effect="plain">定时调度</el-tag>
                                    </template>
                                </el-table-column>
                                <el-table-column label="整链状态" width="100" align="center">
                                    <template #default="{ row: hRow }">
                                        <span v-if="hRow.is_success" style="color: #059669; font-weight: 600;">
                                            <i class="fa-solid fa-circle-check" style="margin-right: 3px;"></i>整链成功
                                        </span>
                                        <span v-else style="color: #dc2626; font-weight: 600;">
                                            <i class="fa-solid fa-circle-xmark" style="margin-right: 3px;"></i>存在失败
                                        </span>
                                    </template>
                                </el-table-column>
                                <el-table-column label="整链总耗时" width="110" align="center">
                                    <template #default="{ row: hRow }">
                                        <span v-if="hRow.total_latency_ms !== null && hRow.total_latency_ms !== undefined"
                                            :class="getLatencyBadgeClass(hRow.total_latency_ms)">
                                            {{ hRow.total_latency_ms }} ms
                                        </span>
                                        <span v-else style="color: var(--text-muted); font-size: 12px;">-</span>
                                    </template>
                                </el-table-column>
                                <el-table-column label="契约校验" width="110" align="center">
                                    <template #default="{ row: hRow }">
                                        <el-tag v-if="hRow.schema_matched === true" type="success" size="small">
                                            <i class="fa-solid fa-circle-check" style="margin-right: 2px;"></i>完全匹配
                                        </el-tag>
                                        <el-tag v-else-if="hRow.schema_matched === false" type="danger" size="small">
                                            <i class="fa-solid fa-triangle-exclamation" style="margin-right: 2px;"></i>契约突变
                                        </el-tag>
                                        <span v-else style="color: #94a3b8; font-size: 12px;">未配置</span>
                                    </template>
                                </el-table-column>
                                <el-table-column label="步骤执行数" width="110" align="center">
                                    <template #default="{ row: hRow }">
                                        <span style="font-size: 12px; color: #475569;">
                                            {{ (hRow.steps_detail || []).filter(s => s.ok).length }}/{{ (hRow.steps_detail || []).length }} 步
                                        </span>
                                    </template>
                                </el-table-column>
                            </el-table>
                        </div>
                    </el-drawer>
                </div>
</template>

<script>
import { inject, ref, nextTick } from 'vue'

// 场景拨测视图: 业务链路多步骤拨测 (写入 -> 校验 -> 清理 闭环)
// 对话框复用【接口探测工作台】的 Postman 风格配置界面, 数据源为当前选中的业务链路节点
// 领域状态与逻辑位于 composables/scenarios.js
export default {
    name: 'ScenarioProbeView',
    setup() {
        const wb = inject('workbench')
      // ===== 节点名称就地编辑 =====
        const editingStepIndex = ref(-1)        // 当前正在编辑的节点索引，-1 表示无
        const stepNameInputRefs = ref({})       // 存放各节点 input 的 DOM 引用
        let originalStepName = ''

        function startEditStep(idx) {
          originalStepName = wb.scenarioSteps.value[idx]?.name || ''
          editingStepIndex.value = idx
          nextTick(() => {
            const el = stepNameInputRefs.value[idx]
            if (el) {
              el.focus()
              el.select()
            }
          })
        }

        function finishEditStep() {
          editingStepIndex.value = -1
        }

        function cancelEditStep(idx) {
          const step = wb.scenarioSteps.value[idx]
          if (step) step.name = originalStepName
          editingStepIndex.value = -1
        }
        return {
            // ===== 节点名称就地编辑 =====
            editingStepIndex,
            stepNameInputRefs,
            startEditStep,
            finishEditStep,
            cancelEditStep,
            // 共享导航与机器环境上下文
            currentNav: wb.currentNav,
            environmentList: wb.environmentList,
            currentMachineEnvironment: wb.currentMachineEnvironment,
            // 场景拨测域: 列表
            scenarioLoading: wb.scenarioLoading,
            scenarioSearchQuery: wb.scenarioSearchQuery,
            selectedScenarioEnv: wb.selectedScenarioEnv,
            selectedScenarioMachine: wb.selectedScenarioMachine,
            selectedScenarioStatus: wb.selectedScenarioStatus,
            toggleScenarioActive: wb.toggleScenarioActive,
            filteredScenarios: wb.filteredScenarios,
            scenarioTotalCount: wb.scenarioTotalCount,
            scenarioActiveCount: wb.scenarioActiveCount,
            scenarioCleanupCount: wb.scenarioCleanupCount,
            scenarioStepTotalCount: wb.scenarioStepTotalCount,
            openCreateScenarioDialog: wb.openCreateScenarioDialog,
            openEditScenarioDialog: wb.openEditScenarioDialog,
            handleDeleteScenario: wb.handleDeleteScenario,
            getMethodBadgeStyle: wb.getMethodBadgeStyle,
            getScenarioStatusBadgeClass: wb.getScenarioStatusBadgeClass,
            getScenarioStatusText: wb.getScenarioStatusText,
            getStatusBadgeClass: wb.getStatusBadgeClass,
            getStatusIcon: wb.getStatusIcon,
            getGroupTagType: wb.getGroupTagType,
            getLatencyBadgeClass: wb.getLatencyBadgeClass,
            getIntervalTooltip: wb.getIntervalTooltip,
            formatIntervalDisplay: wb.formatIntervalDisplay,
            // 场景拨测域: 对话框与业务链路步骤
            scenarioDialogVisible: wb.scenarioDialogVisible,
            editingScenarioId: wb.editingScenarioId,
            scenarioSubmitting: wb.scenarioSubmitting,
            scenarioForm: wb.scenarioForm,
            scenarioMachineOptions: wb.scenarioMachineOptions,
            scenarioMachineDisplayName: wb.scenarioMachineDisplayName,
            openEnvDialog: wb.openEnvDialog,
            scenarioIntervalValue: wb.scenarioIntervalValue,
            scenarioIntervalUnit: wb.scenarioIntervalUnit,
            setQuickScenarioInterval: wb.setQuickScenarioInterval,
            resetScenarioBaseUrlToMachine: wb.resetScenarioBaseUrlToMachine,
            scenarioSteps: wb.scenarioSteps,
            activeStepIndex: wb.activeStepIndex,
            activeStep: wb.activeStep,
            addScenarioStep: wb.addScenarioStep,
            removeScenarioStep: wb.removeScenarioStep,
            selectScenarioStep: wb.selectScenarioStep,
            stepActiveTab: wb.stepActiveTab,
            scenarioSystemDefaultHeaders: wb.scenarioSystemDefaultHeaders,
            showStepDefaultHeaders: wb.showStepDefaultHeaders,
            activeScenarioDefaultHeadersCount: wb.activeScenarioDefaultHeadersCount,
            isStepHeaderOverridden: wb.isStepHeaderOverridden,
            addStepParamRow: wb.addStepParamRow,
            removeStepParamRow: wb.removeStepParamRow,
            addStepHeaderRow: wb.addStepHeaderRow,
            removeStepHeaderRow: wb.removeStepHeaderRow,
            formatStepBodyJson: wb.formatStepBodyJson,
            minifyStepBodyJson: wb.minifyStepBodyJson,
            clearStepBodyJson: wb.clearStepBodyJson,
            onStepPathInput: wb.onStepPathInput,
            addStepPreActionRow: wb.addStepPreActionRow,
            removeStepPreActionRow: wb.removeStepPreActionRow,
            applyStepPreActionPreset: wb.applyStepPreActionPreset,
            addStepPostActionRow: wb.addStepPostActionRow,
            removeStepPostActionRow: wb.removeStepPostActionRow,
            onStepPostActionTypeChange: wb.onStepPostActionTypeChange,
            applyStepPostActionPreset: wb.applyStepPostActionPreset,
            submitScenarioForm: wb.submitScenarioForm,
            // 拨测执行引擎
            scenarioRunningId: wb.scenarioRunningId,
            scenarioResultVisible: wb.scenarioResultVisible,
            scenarioResult: wb.scenarioResult,
            stepTestRunning: wb.stepTestRunning,
            stepTestResult: wb.stepTestResult,
            handleRunScenario: wb.handleRunScenario,
            getStepResultBadge: wb.getStepResultBadge,
            handleTestRunStep: wb.handleTestRunStep,
            // 节点 Schema 契约
            stepSchemaSampleJson: wb.stepSchemaSampleJson,
            stepInferring: wb.stepInferring,
            formatStepSchemaJson: wb.formatStepSchemaJson,
            inferStepSchemaFromSample: wb.inferStepSchemaFromSample,
            inferStepSchemaFromTestResult: wb.inferStepSchemaFromTestResult,
            safeFormatJson: wb.safeFormatJson,
            // 从接口管理导入接口为链路节点
            apiImportDialogVisible: wb.apiImportDialogVisible,
            apiImportSearch: wb.apiImportSearch,
            apiImportMethodFilter: wb.apiImportMethodFilter,
            apiImportSelection: wb.apiImportSelection,
            apiImportTableRef: wb.apiImportTableRef,
            importableApis: wb.importableApis,
            openApiImportDialog: wb.openApiImportDialog,
            handleApiImportSelectionChange: wb.handleApiImportSelectionChange,
            confirmImportApisAsSteps: wb.confirmImportApisAsSteps,
            fillActiveStepFromApi: wb.fillActiveStepFromApi,
            // 场景时序排障与历史流水
            scenarioMetricsDrawerVisible: wb.scenarioMetricsDrawerVisible,
            scenarioMetricsLoading: wb.scenarioMetricsLoading,
            activeScenarioMetrics: wb.activeScenarioMetrics,
            scenarioHistoryList: wb.scenarioHistoryList,
            openScenarioMetricsDrawer: wb.openScenarioMetricsDrawer,
            formatTime: wb.formatTime,
            // 业务链路步骤折叠与展开
            isScenarioStepsExpanded: wb.isScenarioStepsExpanded,
            toggleScenarioStepsExpand: wb.toggleScenarioStepsExpand,
            isAllScenarioStepsExpanded: wb.isAllScenarioStepsExpanded,
            toggleAllScenarioStepsExpand: wb.toggleAllScenarioStepsExpand,
            // 场景专属变量池 (隔离防污染)
            scenarioVariablesList: wb.scenarioVariablesList,
            scenarioVariablesDrawerVisible: wb.scenarioVariablesDrawerVisible,
            scenarioVariablesCount: wb.scenarioVariablesCount,
            addScenarioVariableRow: wb.addScenarioVariableRow,
            removeScenarioVariableRow: wb.removeScenarioVariableRow,
            clearScenarioVariables: wb.clearScenarioVariables,
            copyVariableMacro: wb.copyVariableMacro,
            stepResponseTab: wb.stepResponseTab,
            stepExtractedVarNames: wb.stepExtractedVarNames,
            customExtractPath: wb.customExtractPath,
            customExtractVarName: wb.customExtractVarName,
            customExtractPreview: wb.customExtractPreview,
            stepExtractableFields: wb.stepExtractableFields,
            getStepResponseFormattedBody: wb.getStepResponseFormattedBody,
            isFieldExtractedInActiveStep: wb.isFieldExtractedInActiveStep,
            quickExtractFieldToScenarioVariable: wb.quickExtractFieldToScenarioVariable,
            addCustomExtractToScenarioVariable: wb.addCustomExtractToScenarioVariable,
            insertScenarioVarToStepBody: wb.insertScenarioVarToStepBody,
            insertScenarioVarToStepParam: wb.insertScenarioVarToStepParam,
            insertScenarioVarToStepHeader: wb.insertScenarioVarToStepHeader,
            insertScenarioVarToStepPath: wb.insertScenarioVarToStepPath,
            // 场景列表批量操作
            selectedScenarioRows: wb.selectedScenarioRows,
            scenarioTableRef: wb.scenarioTableRef,
            isScenarioBatchOperating: wb.isScenarioBatchOperating,
            handleScenarioSelectionChange: wb.handleScenarioSelectionChange,
            clearScenarioSelection: wb.clearScenarioSelection,
            handleBatchDeleteScenarios: wb.handleBatchDeleteScenarios,
            handleBatchToggleScenarioActive: wb.handleBatchToggleScenarioActive,
            handleBatchSetScenarioInterval: wb.handleBatchSetScenarioInterval,
            // 场景列表分页
            scenarioCurrentPage: wb.scenarioCurrentPage,
            scenarioPageSize: wb.scenarioPageSize,
            paginatedScenarios: wb.paginatedScenarios
        }
    }
}
</script>
