<template>
                <div v-show="currentNav === 'env_management'">
                    <!-- 环境资产管理表格卡片 -->
                    <div class="wb-card">
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div
                                    style="font-size: 15px; font-weight: 600; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-layer-group" style="color: #0284c7;"></i>
                                    <span>运行环境列表</span>
                                </div>
                                <el-tag size="small" type="info" effect="plain">{{ filteredEnvironments.length }}
                                    个环境</el-tag>
                                <el-input v-model="envSearchQuery" placeholder="搜索环境名称或描述..." clearable size="small"
                                    style="width: 220px;">
                                    <template #prefix><i class="fa-solid fa-magnifying-glass"
                                            style="color: #94a3b8;"></i></template>
                                </el-input>
                            </div>
                            <!-- <div style="display: flex; gap: 10px;">
                                <el-button size="small" type="primary" plain @click="fetchData">
                                    <i class="fa-solid fa-arrows-rotate" style="margin-right: 4px;"></i>刷新
                                </el-button>
                                <el-button size="small" type="primary" @click="openCreateEnvDialog">
                                    <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>新建环境
                                </el-button>
                            </div> -->
                        </div>

                        <el-table :data="filteredEnvironments" v-loading="loading" style="width: 100%">
                            <el-table-column prop="id" label="ID" width="70" align="center"></el-table-column>
                            <el-table-column label="环境名称" min-width="180">
                                <template #default="{ row }">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <i class="fa-solid fa-cubes" style="color: #0284c7;"></i>
                                        <span style="font-weight: 600; color: #0f172a; font-size: 13.5px;">{{ row.name
                                            }}</span>
                                    </div>
                                </template>
                            </el-table-column>
                            <el-table-column prop="description" label="环境描述与业务说明" min-width="260">
                                <template #default="{ row }">
                                    <span v-if="row.description" style="color: #475569; font-size: 13px;">{{
                                        row.description }}</span>
                                    <span v-else
                                        style="color: #94a3b8; font-style: italic; font-size: 12px;">暂无描述</span>
                                </template>
                            </el-table-column>
                            <el-table-column prop="order_num" label="排序权重" width="110" align="center">
                                <template #default="{ row }">
                                    <el-tag size="small" effect="plain" type="info">{{ row.order_num }}</el-tag>
                                </template>
                            </el-table-column>
                            <el-table-column label="名下机器节点" width="160" align="center">
                                <template #default="{ row }">
                                    <el-button size="small" type="primary" link @click="goToEnvMachines(row.name)">
                                        <i class="fa-solid fa-server" style="margin-right: 4px;"></i>{{
                                        getEnvMachineCount(row.id, row.name) }} 台机器
                                    </el-button>
                                </template>
                            </el-table-column>
                            <el-table-column label="环境变量池" width="150" align="center">
                                <template #default="{ row }">
                                    <el-button size="small" type="warning" plain @click="openEnvDialog(row)" title="点击管理该环境名下的环境变量">
                                        <i class="fa-solid fa-sliders" style="margin-right: 4px;"></i>变量 ({{ Object.keys(row.variables || {}).length }})
                                    </el-button>
                                </template>
                            </el-table-column>
                            <el-table-column label="创建时间" width="170" align="center">
                                <template #default="{ row }">
                                    <span style="color: #94a3b8; font-size: 12px;">{{ formatTime(row.created_at)
                                        }}</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="280" align="center" fixed="right">
                                <template #default="{ row }">
                                    <el-button size="small" type="warning" plain @click="openEnvDialog(row)">
                                        <i class="fa-solid fa-sliders" style="margin-right: 4px;"></i>变量管理
                                    </el-button>
                                    <el-button size="small" type="primary" plain @click="openEditEnvDialog(row)">
                                        <i class="fa-solid fa-pen-to-square" style="margin-right: 4px;"></i>编辑
                                    </el-button>
                                    <el-popconfirm :title="'确定删除环境 [' + row.name + '] 及其下属资产吗？'"
                                        confirm-button-text="确定" cancel-button-text="取消"
                                        @confirm="handleDeleteEnv(row.id, row.name)">
                                        <template #reference>
                                            <el-button size="small" type="danger" plain>
                                                <i class="fa-solid fa-trash-can" style="margin-right: 4px;"></i>删除
                                            </el-button>
                                        </template>
                                    </el-popconfirm>
                                </template>
                            </el-table-column>
                        </el-table>
                    </div>
                </div>

<!-- ================= 领域弹窗/抽屉 ================= -->
<el-dialog v-model="envDialogVisible" :title="editingEnvId ? '编辑运行环境' : '新建运行环境'" width="540px"
    destroy-on-close>
    <el-form :model="envForm" label-width="100px">
        <el-form-item label="环境名称" required>
            <el-input v-model="envForm.name" placeholder="例如: 生产环境、预发布环境、测试环境"></el-input>
        </el-form-item>
        <el-form-item label="业务描述">
            <el-input v-model="envForm.description" type="textarea" :rows="3"
                placeholder="简要描述该环境所属集群或业务职责"></el-input>
        </el-form-item>
        <el-form-item label="排序权重">
            <el-input-number v-model="envForm.order_num" :min="0" :max="9999"
                style="width: 140px;"></el-input-number>
            <span style="margin-left: 10px; color: var(--text-muted); font-size: 12px;">数值越小排序越靠前</span>
        </el-form-item>
    </el-form>
    <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEnvForm" :loading="envSubmitting">
            {{ editingEnvId ? '保存修改' : '确认创建' }}
        </el-button>
    </template>
</el-dialog>
<el-dialog v-model="envVarsDialogVisible"
    :title="'环境变量管理 - ' + (currentMachineEnvironment.name || '运行环境')"
    width="750px" top="8vh" destroy-on-close>
    <div style="margin-bottom: 14px;">
        <div style="font-size: 13px; color: #475569; line-height: 1.5; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px; padding: 10px 14px;">
            <i class="fa-solid fa-circle-info" style="color: #0284c7; margin-right: 6px;"></i>
            当前宿主机器归属于 <strong>{{ currentMachineEnvironment.name }}</strong>。在此维护的环境变量在该环境下的所有接口中全局生效，支持在 URL、Headers、Params、Body 中通过 <code v-pre>{{变量名}}</code> 直接引用。
        </div>
    </div>

    <div style="max-height: 420px; overflow-y: auto;">
        <table class="pm-table" style="width: 100%;">
            <thead>
                <tr>
                    <th style="width: 200px;">变量名 (Variable Name)</th>
                    <th>当前变量值 (Value)</th>
                    <th style="width: 150px; text-align: center;">快捷引用语法</th>
                    <th style="width: 50px; text-align: center;">操作</th>
                </tr>
            </thead>
            <tbody>
                <tr v-if="envVariablesList.length === 0">
                    <td colspan="4" style="text-align: center; color: #94a3b8; padding: 24px;">
                        暂无环境变量，点击下方【+ 添加新变量】或在接口后置脚本中调用 <code>pm.environment.set(k, v)</code> 自动存入
                    </td>
                </tr>
                <tr v-for="(item, idx) in envVariablesList" :key="idx">
                    <td>
                        <el-input v-model="item.key" placeholder="例如: JWT_TOKEN" size="small"></el-input>
                    </td>
                    <td>
                        <el-input v-model="item.value" placeholder="变量当前值" size="small"></el-input>
                    </td>
                    <td style="text-align: center;">
                        <el-tooltip content="点击一键复制变量引用语法" placement="top">
                            <el-button size="small" type="primary" link @click="copyEnvVarRef(item.key)" :disabled="!item.key">
                                <i class="fa-regular fa-copy" style="margin-right: 2px;"></i>
                                <code>{{ getVarRef(item.key) }}</code>
                            </el-button>
                        </el-tooltip>
                    </td>
                    <td style="text-align: center;">
                        <el-button size="small" link type="danger" @click="removeEnvVarRow(idx)">
                            <i class="fa-solid fa-trash-can"></i>
                        </el-button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
        <el-button size="small" type="primary" plain @click="addEnvVarRow">
            <i class="fa-solid fa-plus" style="margin-right: 4px;"></i>添加新变量
        </el-button>
        <span style="font-size: 11.5px; color: #64748b;">当前共 {{ envVariablesList.length }} 个环境变量</span>
    </div>

    <template #footer>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <div style="font-size: 11.5px; color: #94a3b8;">
                提示：点击保存后将即时同步持久化至后端 SQLite 数据库
            </div>
            <div style="display: flex; gap: 10px;">
                <el-button @click="envVarsDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="saveEnvVariables" :loading="envVariablesSaving">
                    保存修改
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
    name: 'EnvManagementView',
    setup() {
        return inject('workbench')
    }
}
</script>
