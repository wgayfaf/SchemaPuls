import { ref, computed } from 'vue'
import { activeMenuKey, currentNav, environmentList, fetchData, machineList, targets } from './core'
import { selectedGroup } from './targets'
import { machineSearchQuery, selectedMachineEnv } from './machines'
import { apiSearchQuery, selectedApiEnv, selectedApiMachine, selectedApiStatus } from './apis'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const envDialogVisible = ref(false);

const editingEnvId = ref(null);

const envSubmitting = ref(false);

const envSearchQuery = ref("");

const envForm = ref({
    name: "",
    description: "",
    order_num: 0
});

// 搜索过滤后的环境列表
const filteredEnvironments = computed(() => {
    if (!envSearchQuery.value || !envSearchQuery.value.trim()) {
        return environmentList.value;
    }
    const q = envSearchQuery.value.toLowerCase().trim();
    return environmentList.value.filter(e => 
        (e.name && e.name.toLowerCase().includes(q)) || 
        (e.description && e.description.toLowerCase().includes(q))
    );
});

// 环境管理 CRUD
const openCreateEnvDialog = () => {
    editingEnvId.value = null;
    envForm.value = {
        name: "",
        description: "",
        order_num: (environmentList.value.length + 1) * 10
    };
    envDialogVisible.value = true;
};

const openEditEnvDialog = (row) => {
    editingEnvId.value = row.id;
    envForm.value = {
        name: row.name || "",
        description: row.description || "",
        order_num: row.order_num !== undefined ? row.order_num : 0
    };
    envDialogVisible.value = true;
};

const submitEnvForm = async () => {
    if (!envForm.value.name || !envForm.value.name.trim()) {
        ElMessage.warning("请输入环境名称！");
        return;
    }
    envSubmitting.value = true;
    try {
        const payload = {
            name: envForm.value.name.trim(),
            description: envForm.value.description ? envForm.value.description.trim() : "",
            order_num: envForm.value.order_num || 0
        };
        if (editingEnvId.value) {
            await axios.put(`/api/environments/${editingEnvId.value}`, payload);
            ElMessage.success(`环境 [${payload.name}] 修改成功！`);
        } else {
            await axios.post("/api/environments", payload);
            ElMessage.success(`环境 [${payload.name}] 创建成功！`);
        }
        envDialogVisible.value = false;
        await fetchData();
    } catch (err) {
        ElMessage.error((editingEnvId.value ? "修改环境失败: " : "创建环境失败: ") + (err.response?.data?.detail || err.message));
    } finally {
        envSubmitting.value = false;
    }
};

const handleDeleteEnv = async (envId, envName) => {
    try {
        await axios.delete(`/api/environments/${envId}`);
        ElMessage.success(`环境 [${envName}] 及其下属资产已删除`);
        if (selectedGroup.value === envName) {
            selectedGroup.value = "ALL";
            activeMenuKey.value = "targets:ALL";
        }
        await fetchData();
    } catch (err) {
        ElMessage.error("删除环境失败: " + (err.response?.data?.detail || err.message));
    }
};

const goToEnvTargets = (envName) => {
    currentNav.value = "api_management";
    selectedApiEnv.value = envName;
    selectedApiMachine.value = "ALL";
    activeMenuKey.value = "api_management";
};

const goToEnvApis = (envName) => {
    currentNav.value = "api_management";
    activeMenuKey.value = "api_management";
    selectedApiEnv.value = envName || "ALL";
    selectedApiMachine.value = "ALL";
    selectedApiStatus.value = "ALL";
    apiSearchQuery.value = "";
};

const goToEnvMachines = (envName) => {
    currentNav.value = "machine_management";
    activeMenuKey.value = "machine_management";
    selectedMachineEnv.value = envName || "ALL";
    machineSearchQuery.value = "";
};

const getEnvStatusBadgeClass = (status) => {
    switch (status) {
        case "HEALTHY": return "status-badge healthy";
        case "DOWN": return "status-badge down";
        case "DEGRADED": return "status-badge degraded";
        default: return "status-badge unknown";
    }
};

const getEnvBorderTopColor = (status) => {
    switch (status) {
        case "HEALTHY": return "#059669";
        case "DOWN": return "#dc2626";
        case "DEGRADED": return "#d97706";
        default: return "#94a3b8";
    }
};

const getEnvTargetCount = (envName) => {
    return targets.value.filter(t => (t.group_name || "生产环境") === envName).length;
};

const getEnvMachineCount = (envId, envName) => {
    return machineList.value.filter(m => 
        (envId != null && m.environment_id === envId) || 
        (envName && m.environment_name === envName)
    ).length;
};

export { editingEnvId, envDialogVisible, envForm, envSearchQuery, envSubmitting, filteredEnvironments, getEnvBorderTopColor, getEnvMachineCount, getEnvStatusBadgeClass, getEnvTargetCount, goToEnvApis, goToEnvMachines, goToEnvTargets, handleDeleteEnv, openCreateEnvDialog, openEditEnvDialog, submitEnvForm }
