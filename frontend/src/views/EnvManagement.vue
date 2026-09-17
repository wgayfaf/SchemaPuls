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
