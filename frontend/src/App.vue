<template>
        <!-- ================= 工业级左侧导航菜单 ================= -->
        <aside class="workbench-sidebar">
            <div class="sidebar-brand">
                <i class="fa-solid fa-satellite-dish brand-icon"></i>
                <span class="brand-title">SchemaPulse</span>
                <span class="brand-badge">PRO</span>
            </div>

            <div style="flex: 1; overflow-y: auto; padding: 6px 0;">
                <el-menu :default-active="activeMenuKey"
                    :default-openeds="['topology_group', 'tools_group', 'settings_group']" class="vue-admin-menu"
                    @select="handleMenuSelect">

                    <!-- 一级主菜单: 监控大盘 -->
                    <el-menu-item index="dashboard">
                        <i class="fa-solid fa-gauge-high menu-icon"></i>
                        <span>全局监控大盘</span>
                    </el-menu-item>

                    <!-- 一级功能模块 (含二级子菜单): 服务监控拓扑 -->
                    <el-sub-menu index="topology_group">
                        <template #title>
                            <i class="fa-solid fa-network-wired menu-icon"></i>
                            <span>服务监控拓扑</span>
                        </template>
                        <el-menu-item index="env_management">
                            <i class="fa-solid fa-layer-group menu-icon" style="color: #0284c7;"></i>
                            <span>环境管理</span>
                        </el-menu-item>
                        <el-menu-item index="machine_management">
                            <i class="fa-solid fa-server menu-icon" style="color: #10b981;"></i>
                            <span>机器管理</span>
                        </el-menu-item>
                        <el-menu-item index="api_management">
                            <i class="fa-solid fa-code menu-icon" style="color: #8b5cf6;"></i>
                            <span>接口管理</span>
                        </el-menu-item>
                    </el-sub-menu>

                    <!-- 一级功能模块 (含二级子菜单): 排障与契约实验室 -->
                    <el-sub-menu index="tools_group">
                        <template #title>
                            <i class="fa-solid fa-screwdriver-wrench menu-icon"></i>
                            <span>排障与实验室</span>
                        </template>
                        <el-menu-item index="schema_lab">
                            <i class="fa-solid fa-flask-vial menu-icon" style="color: #a855f7;"></i>
                            <span>Schema 契约实验室</span>
                        </el-menu-item>
                        <el-menu-item index="incidents">
                            <i class="fa-solid fa-triangle-exclamation menu-icon" style="color: #ef4444;"></i>
                            <span>故障告警排障中心</span>
                        </el-menu-item>
                    </el-sub-menu>

                    <!-- 一级功能模块 (含二级子菜单): 系统与配置 -->
                    <el-sub-menu index="settings_group">
                        <template #title>
                            <i class="fa-solid fa-sliders menu-icon"></i>
                            <span>系统配置支持</span>
                        </template>
                        <el-menu-item index="settings">
                            <i class="fa-solid fa-envelope-open-text menu-icon" style="color: #10b981;"></i>
                            <span>SMTP 告警配置</span>
                        </el-menu-item>
                        <el-menu-item index="docs">
                            <i class="fa-solid fa-book-open menu-icon" style="color: #6366f1;"></i>
                            <span>Swagger API 文档</span>
                        </el-menu-item>
                    </el-sub-menu>
                </el-menu>
            </div>

            <div class="sidebar-footer">
                <div><span class="pulse-indicator"></span>引擎在线中</div>
                <div>v1.0.0</div>
            </div>
        </aside>

        <!-- ================= 右侧主工作区 ================= -->
        <main class="workbench-main">
            <!-- 顶部 Header -->
            <header class="workbench-header">
                <div class="header-breadcrumb">
                    <i class="fa-solid fa-terminal" style="color: var(--primary);"></i>
                    <span>工作区</span>
                    <span>/</span>
                    <b>{{ navTitle }}</b>
                    <span v-if="currentNav === 'targets'">
                        / <el-tag size="small" :type="getGroupTagType(selectedGroup)" effect="light">{{ selectedGroup
                            === 'ALL' ? '全部环境' : selectedGroup }}</el-tag>
                    </span>
                </div>

                <div class="header-actions">
                    <span
                        style="font-size: 11.5px; color: #64748b; margin-right: 8px; display: inline-flex; align-items: center;">
                        <i class="fa-regular fa-clock" style="margin-right: 4px;"></i>上次同步: {{ lastRefreshTime }}
                    </span>
                    <el-button type="info" size="small" text @click="openDocs">
                        <i class="fa-solid fa-book-open" style="margin-right: 6px;"></i>Swagger 接口
                    </el-button>
                    <el-button type="primary" size="small" plain @click="handleManualRefresh" :loading="loading">
                        <i class="fa-solid fa-arrows-rotate" :class="{ 'fa-spin': loading }"
                            style="margin-right: 6px;"></i>刷新
                    </el-button>
                    <el-button v-if="currentNav === 'env_management'" type="primary" size="small"
                        @click="openCreateEnvDialog">
                        <i class="fa-solid fa-plus" style="margin-right: 6px;"></i>新建环境
                    </el-button>
                    <el-button v-else-if="currentNav === 'machine_management'" type="primary" size="small"
                        @click="openCreateMachineDialog()">
                        <i class="fa-solid fa-plus" style="margin-right: 6px;"></i>新建机器
                    </el-button>
                    <el-button v-else-if="currentNav === 'api_management'" type="primary" size="small"
                        @click="openCreateApiDialog()">
                        <i class="fa-solid fa-plus" style="margin-right: 6px;"></i>新建接口
                    </el-button>
                    <el-button v-else-if="currentNav === 'targets'" type="primary" size="small"
                        @click="openCreateDialog">
                        <i class="fa-solid fa-plus" style="margin-right: 6px;"></i>新建监控目标
                    </el-button>
                </div>
            </header>

            <!-- 工作区各功能视图 (根据 currentNav 动态切换) -->
            <div class="workbench-content">

                <!-- 视图 1: 全局监控大盘 (Dashboard - 按环境分类与态势看板) -->
                <DashboardView />

                <!-- 视图: 环境管理 (Environment Management) -->
                <EnvManagementView />

                <!-- 视图: 机器管理 (Machine Management) -->
                <MachineManagementView />

                <!-- 视图: 接口管理 (API Probe Management) -->
                <ApiManagementView />

                <!-- 视图 2: 环境与服务拨测工作台 (Targets) -->
                <TargetsView />

                <!-- 视图 3: Schema 契约生成与破坏性变更实验室 (Schema Lab) -->
                <SchemaLabView />

                <!-- 视图 4: 故障告警排障中心 (Incidents) -->
                <IncidentsView />

                <!-- 视图 5: 系统设置 (Settings) -->
                <SettingsView />

            </div>
        </main>

        <!-- 新增/编辑目标对话框 -->

        <!-- 新增/编辑环境对话框 -->

        <!-- 新增/编辑机器对话框 -->

        <!-- Postman 风格接口探测与调试工作台对话框 -->

        <!-- 环境级变量查看与管理对话框 (Apifox 风格) -->

        <!-- Postman 资产智能导入对话框 (关联机器与运行环境) -->

        <!-- 时序指标与日志排障抽屉 -->
</template>

<script>
import { provide } from 'vue'
import { workbenchSetup } from './workbench'
import DashboardView from './views/Dashboard.vue'
import EnvManagementView from './views/EnvManagement.vue'
import MachineManagementView from './views/MachineManagement.vue'
import ApiManagementView from './views/ApiManagement.vue'
import TargetsView from './views/Targets.vue'
import SchemaLabView from './views/SchemaLab.vue'
import IncidentsView from './views/Incidents.vue'
import SettingsView from './views/Settings.vue'

// 阶段二：九大视图拆分为独立组件，通过 provide/inject 共享工作台上下文
// 阶段三：将 workbench.js 按领域拆分为 composables，各视图按需引入
export default {
    components: {
        DashboardView,
        EnvManagementView,
        MachineManagementView,
        ApiManagementView,
        TargetsView,
        SchemaLabView,
        IncidentsView,
        SettingsView
    },
    setup() {
        const ctx = workbenchSetup()
        provide('workbench', ctx)
        return ctx
    }
}
</script>
