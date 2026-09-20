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

                    <!-- 场景列表面板 -->
                    <div class="panel" style="padding: 16px;">
                        <!-- 工具条: 环境筛选 + 搜索 -->
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                                    <i class="fa-solid fa-route" style="color: #f97316;"></i>业务链路场景库
                                </span>
                                <el-select v-model="selectedScenarioEnv" size="small" style="width: 160px;">
                                    <el-option label="全部环境" value="ALL"></el-option>
                                    <el-option v-for="env in environmentList" :key="env.id" :label="env.name" :value="env.name"></el-option>
                                </el-select>
                            </div>
                            <el-input v-model="scenarioSearchQuery" size="small" placeholder="搜索场景名称 / 描述 / 机器" clearable style="width: 240px;">
                                <template #prefix><i class="fa-solid fa-magnifying-glass" style="color: #94a3b8;"></i></template>
                            </el-input>
                        </div>

                        <el-table :data="filteredScenarios" v-loading="scenarioLoading" size="small"
                            style="width: 100%" empty-text="暂无拨测场景，点击右上角【新建场景】创建业务链路">
                            <el-table-column label="场景名称" min-width="180">
                                <template #default="{ row }">
                                    <div style="display: flex; flex-direction: column; gap: 2px;">
                                        <span style="font-weight: 600; color: #0f172a;">{{ row.name }}</span>
                                        <span v-if="row.description" style="font-size: 11px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 260px;">{{ row.description }}</span>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="业务链路步骤" min-width="320">
                                <template #default="{ row }">
                                    <div style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap;">
                                        <template v-for="(step, idx) in (row.steps || [])" :key="idx">
                                            <span style="display: inline-flex; align-items: center; gap: 4px; padding: 1px 6px; border-radius: 4px; font-size: 11px;"
                                                :style="getMethodBadgeStyle(step.http_method)">
                                                <b>{{ step.http_method }}</b>
                                                <span style="color: #334155;">{{ step.name || step.http_path }}</span>
                                                <el-tooltip v-if="step.is_cleanup" content="清理步骤: 拨测引擎将保证其无论成败均执行" placement="top">
                                                    <i class="fa-solid fa-broom" style="color: #d97706;"></i>
                                                </el-tooltip>
                                            </span>
                                            <i v-if="idx < (row.steps || []).length - 1" class="fa-solid fa-arrow-right" style="font-size: 9px; color: #cbd5e1;"></i>
                                        </template>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column label="归属环境" width="110">
                                <template #default="{ row }">
                                    <el-tag size="small" type="success" effect="plain">{{ row.environment_name }}</el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column label="宿主机器" width="130">
                                <template #default="{ row }">
                                    <span style="font-size: 12px; color: #475569;">{{ row.machine_name }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="拨测周期" width="90">
                                <template #default="{ row }">
                                    <span style="font-size: 12px; color: #475569;">{{ row.cron_interval_minutes }} 分钟</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="运行状态" width="110">
                                <template #default="{ row }">
                                    <span :class="getScenarioStatusBadgeClass(row.current_status)">{{ getScenarioStatusText(row.current_status) }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="180" fixed="right">
                                <template #default="{ row }">
                                    <el-button size="small" link type="primary" @click="openEditScenarioDialog(row)">
                                        <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                    </el-button>
                                    <el-tooltip content="立即执行整链拨测: 业务节点串行调用, 清理节点无论成败均执行" placement="top">
                                        <el-button size="small" link type="success" :loading="scenarioRunningId === row.id"
                                            @click="handleRunScenario(row)">
                                            <i class="fa-solid fa-play" style="margin-right: 4px;"></i>执行
                                        </el-button>
                                    </el-tooltip>
                                    <el-popconfirm :title="`确定删除场景 [${row.name}] 吗？`" confirm-button-text="删除" cancel-button-text="取消"
                                        @confirm="handleDeleteScenario(row)">
                                        <template #reference>
                                            <el-button size="small" link type="danger">
                                                <i class="fa-solid fa-trash" style="margin-right: 4px;"></i>删除
                                            </el-button>
                                        </template>
                                    </el-popconfirm>
                                </template>
                            </el-table-column>
                        </el-table>
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
                                            <el-tooltip v-if="step.is_cleanup" content="清理步骤 (finally 语义)" placement="top">
                                                <i class="fa-solid fa-broom" style="color: #d97706;"></i>
                                            </el-tooltip>
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 5px; margin-bottom: 4px;">
                                            <span style="font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px;" :style="getMethodBadgeStyle(step.http_method)">{{ step.http_method }}</span>
                                        </div>
                                        <div style="font-size: 11.5px; font-weight: 600; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                            {{ step.name || '未命名节点' }}
                                        </div>
                                        <div style="font-size: 10px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                            {{ step.http_path || '/' }}
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
                                        <i class="fa-solid fa-server" style="color: #0284c7; margin-right: 4px;"></i>宿主机器:
                                    </span>
                                    <span style="font-weight: 600; color: #0f172a;">
                                        {{ scenarioMachineDisplayName }}
                                    </span>
                                    <span style="color: #cbd5e1; margin: 0 4px;">|</span>
                                    <span style="font-weight: 600; color: #475569;">
                                        <i class="fa-solid fa-layer-group" style="color: #10b981; margin-right: 4px;"></i>所属环境:
                                    </span>
                                    <el-tag size="small" type="success" effect="plain" style="font-weight: 600;">
                                        {{ currentMachineEnvironment.name || '默认环境' }}
                                    </el-tag>
                                    <span style="color: #cbd5e1; margin: 0 4px;">|</span>
                                    <span style="color: #64748b;">
                                        机器默认地址:
                                        <code
                                            style="background: #e2e8f0; color: #0284c7; padding: 2px 6px; border-radius: 4px; font-family: monospace;">{{ scenarioForm.base_url }}</code>
                                    </span>
                                    <el-tooltip content="点击将当前宿主机器的默认基准地址同步填入下方输入框" placement="top">
                                        <el-button size="small" link type="primary" @click="resetScenarioBaseUrlToMachine">
                                            <i class="fa-solid fa-rotate-left" style="margin-right: 2px;"></i>恢复机器地址
                                        </el-button>
                                    </el-tooltip>
                                </div>
                                <div style="color: #64748b; font-size: 11.5px; display: flex; align-items: center; gap: 4px;">
                                    <i class="fa-solid fa-circle-info" style="color: #0284c7;"></i>
                                    <span>正在配置: <b style="color: #c2410c;">节点 {{ activeStepIndex + 1 }}</b> (切换节点仅更换数据, 界面保持不变)</span>
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
                                        <el-button size="small" type="primary" plain @click="addStepParamRow">
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
                                        <el-button size="small" type="primary" plain @click="addStepHeaderRow">
                                            <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加自定义请求头
                                        </el-button>
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
                                            <span v-if="stepTestResult.assertions_summary"
                                                :class="stepTestResult.assertions_summary.all_passed ? 'pm-badge-schema-ok' : 'pm-badge-schema-err'"
                                                :title="'共执行 ' + stepTestResult.assertions_summary.total + ' 项断言, 通过 ' + stepTestResult.assertions_summary.passed_count + ' 项'">
                                                <i :class="stepTestResult.assertions_summary.all_passed ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i>
                                                断言 {{ stepTestResult.assertions_summary.passed_count }}/{{ stepTestResult.assertions_summary.total }}
                                            </span>
                                            <span v-if="Object.keys(stepTestResult.extracted_variables || {}).length"
                                                class="pm-badge-schema-ok" style="background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe;">
                                                <i class="fa-solid fa-link"></i> 提取变量: {{ Object.keys(stepTestResult.extracted_variables).join(', ') }}
                                            </span>
                                        </template>
                                    </div>
                                </div>
                                <div v-if="!stepTestResult" class="pm-response-empty">
                                    <i class="fa-solid fa-paper-plane" style="font-size: 24px; color: #cbd5e1; margin-bottom: 8px; display: block;"></i>
                                    点击上方【发送调试】对当前节点即时发包, 查看状态码、耗时、断言结果与链路变量提取详情
                                </div>
                                <template v-else>
                                    <div v-if="stepTestResult.request_url" style="padding: 8px 14px 0; font-size: 11px; color: #64748b; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                                        <i class="fa-solid fa-globe" style="color: #0284c7;"></i>
                                        实际请求: <code style="background: #f1f5f9; color: #0284c7; padding: 2px 6px; border-radius: 4px; word-break: break-all;">{{ stepTestResult.request_url }}</code>
                                    </div>
                                    <div v-if="stepTestResult.error" style="margin: 8px 14px 0; padding: 8px 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; font-size: 12px; color: #dc2626;">
                                        <i class="fa-solid fa-circle-exclamation" style="margin-right: 4px;"></i>{{ stepTestResult.error }}
                                    </div>
                                    <pre class="pm-response-body">{{ stepTestResult.response_snippet || (stepTestResult.error ? '无响应内容' : '该请求未返回 JSON 响应体') }}</pre>
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

                        <el-table ref="apiImportTableRef" :data="importableApis" size="small" max-height="380"
                            @selection-change="handleApiImportSelectionChange"
                            empty-text="接口管理中暂无接口，请先在【接口管理】页面创建">
                            <el-table-column type="selection" width="42"></el-table-column>
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
                </div>
</template>

<script>
import { inject } from 'vue'

// 场景拨测视图: 业务链路多步骤拨测 (写入 -> 校验 -> 清理 闭环)
// 对话框复用【接口探测工作台】的 Postman 风格配置界面, 数据源为当前选中的业务链路节点
// 领域状态与逻辑位于 composables/scenarios.js
export default {
    name: 'ScenarioProbeView',
    setup() {
        const wb = inject('workbench')
        return {
            // 共享导航与机器环境上下文
            currentNav: wb.currentNav,
            environmentList: wb.environmentList,
            currentMachineEnvironment: wb.currentMachineEnvironment,
            // 场景拨测域: 列表
            scenarioLoading: wb.scenarioLoading,
            scenarioSearchQuery: wb.scenarioSearchQuery,
            selectedScenarioEnv: wb.selectedScenarioEnv,
            filteredScenarios: wb.filteredScenarios,
            scenarioTotalCount: wb.scenarioTotalCount,
            scenarioActiveCount: wb.scenarioActiveCount,
            scenarioCleanupCount: wb.scenarioCleanupCount,
            scenarioStepTotalCount: wb.scenarioStepTotalCount,
            openEditScenarioDialog: wb.openEditScenarioDialog,
            handleDeleteScenario: wb.handleDeleteScenario,
            getMethodBadgeStyle: wb.getMethodBadgeStyle,
            getScenarioStatusBadgeClass: wb.getScenarioStatusBadgeClass,
            getScenarioStatusText: wb.getScenarioStatusText,
            // 场景拨测域: 对话框与业务链路步骤
            scenarioDialogVisible: wb.scenarioDialogVisible,
            editingScenarioId: wb.editingScenarioId,
            scenarioSubmitting: wb.scenarioSubmitting,
            scenarioForm: wb.scenarioForm,
            scenarioMachineOptions: wb.scenarioMachineOptions,
            scenarioMachineDisplayName: wb.scenarioMachineDisplayName,
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
            fillActiveStepFromApi: wb.fillActiveStepFromApi
        }
    }
}
</script>
