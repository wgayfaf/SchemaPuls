import { ref } from 'vue'
import { activeMenuKey, currentNav, fetchData, machineList } from './core'
import { selectedApiEnv, selectedApiMachine } from './apis'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// Postman 数据导入专属响应式状态 (关联机器与环境)
const postmanImportDialogVisible = ref(false);

const postmanImportMachine = ref(null);

const postmanImportMachineId = ref(null);

const postmanImportLoading = ref(false);

const postmanPreviewData = ref(null);

const postmanSelectedApis = ref([]);

const postmanSyncEnvVars = ref(true);

const postmanUpdateBaseUrl = ref(true);

const postmanConflictPolicy = ref("rename"); // 'rename' | 'overwrite' | 'skip'

const postmanCronInterval = ref(5);

const postmanRawJsonText = ref("");

const postmanImportActiveTab = ref("upload"); // 'upload' | 'text'

const postmanImportSuccessResult = ref(null);

// ==========================================
// Postman 数据导入专属方法 (关联机器与环境)
// ==========================================
const openPostmanImportForMachine = (machine) => {
    postmanImportMachine.value = machine;
    postmanImportMachineId.value = machine.id;
    postmanPreviewData.value = null;
    postmanSelectedApis.value = [];
    postmanRawJsonText.value = "";
    postmanImportActiveTab.value = "upload";
    postmanImportSuccessResult.value = null;
    postmanImportDialogVisible.value = true;
};

const openGenericPostmanImport = () => {
    if (machineList.value.length > 0) {
        postmanImportMachineId.value = machineList.value[0].id;
        postmanImportMachine.value = machineList.value[0];
    } else {
        postmanImportMachineId.value = null;
        postmanImportMachine.value = null;
    }
    postmanPreviewData.value = null;
    postmanSelectedApis.value = [];
    postmanRawJsonText.value = "";
    postmanImportActiveTab.value = "upload";
    postmanImportSuccessResult.value = null;
    postmanImportDialogVisible.value = true;
};

const onPostmanImportMachineChange = (mId) => {
    const m = machineList.value.find(item => item.id === mId);
    postmanImportMachine.value = m || null;
};

const handlePostmanFileChange = async (file) => {
    if (!file || !file.raw) return;
    if (!postmanImportMachineId.value) {
        ElMessage.warning("请先选择目标宿主机器节点！");
        return;
    }
    postmanImportLoading.value = true;
    try {
        const formData = new FormData();
        formData.append("file", file.raw);
        const res = await axios.post(`/api/machines/${postmanImportMachineId.value}/import-postman/preview`, formData);
        if (res.data && res.data.success) {
            postmanPreviewData.value = res.data.data;
            postmanSelectedApis.value = [...res.data.data.apis]; // 默认全选
            ElMessage.success(`成功解析 Postman 集合，识别出 ${res.data.data.apis.length} 个接口！`);
        }
    } catch (err) {
        ElMessage.error("Postman 文件解析失败: " + (err.response?.data?.detail || err.message));
    } finally {
        postmanImportLoading.value = false;
    }
};

const handlePostmanTextParse = async () => {
    if (!postmanRawJsonText.value.trim()) {
        ElMessage.warning("请先粘贴 Postman 导出的 JSON 文本！");
        return;
    }
    if (!postmanImportMachineId.value) {
        ElMessage.warning("请先选择目标宿主机器节点！");
        return;
    }
    postmanImportLoading.value = true;
    try {
        const formData = new FormData();
        formData.append("raw_json", postmanRawJsonText.value.trim());
        const res = await axios.post(`/api/machines/${postmanImportMachineId.value}/import-postman/preview`, formData);
        if (res.data && res.data.success) {
            postmanPreviewData.value = res.data.data;
            postmanSelectedApis.value = [...res.data.data.apis]; // 默认全选
            ElMessage.success(`成功解析 JSON 文本，识别出 ${res.data.data.apis.length} 个接口！`);
        }
    } catch (err) {
        ElMessage.error("JSON 解析失败: " + (err.response?.data?.detail || err.message));
    } finally {
        postmanImportLoading.value = false;
    }
};

const toggleSelectAllPostmanApis = () => {
    if (!postmanPreviewData.value || !postmanPreviewData.value.apis) return;
    if (postmanSelectedApis.value.length === postmanPreviewData.value.apis.length) {
        postmanSelectedApis.value = [];
    } else {
        postmanSelectedApis.value = [...postmanPreviewData.value.apis];
    }
};

const isPostmanApiSelected = (apiItem) => {
    return postmanSelectedApis.value.includes(apiItem);
};

const togglePostmanApiSelection = (apiItem) => {
    const idx = postmanSelectedApis.value.indexOf(apiItem);
    if (idx > -1) {
        postmanSelectedApis.value.splice(idx, 1);
    } else {
        postmanSelectedApis.value.push(apiItem);
    }
};

const executeConfirmPostmanImport = async () => {
    if (!postmanImportMachineId.value) {
        ElMessage.warning("请选择目标宿主机器节点！");
        return;
    }
    if (postmanSelectedApis.value.length === 0) {
        ElMessage.warning("请至少勾选 1 个需要导入的接口！");
        return;
    }
    postmanImportLoading.value = true;
    try {
        const payload = {
            selected_apis: postmanSelectedApis.value,
            environment_variables: postmanPreviewData.value?.environment_variables || {},
            postman_base_url: postmanPreviewData.value?.base_url || null,
            sync_env_vars: postmanSyncEnvVars.value,
            update_machine_base_url: postmanUpdateBaseUrl.value,
            conflict_policy: postmanConflictPolicy.value,
            cron_interval_minutes: postmanCronInterval.value || 5,
            machine_id: postmanImportMachineId.value
        };
        const res = await axios.post(`/api/machines/${postmanImportMachineId.value}/import-postman/confirm`, payload);
        if (res.data && res.data.success) {
            postmanImportSuccessResult.value = res.data.result;
            ElMessage.success(`导入成功！共导入 ${res.data.result.total_imported} 个接口！`);
            await fetchData();
        }
    } catch (err) {
        ElMessage.error("导入提交失败: " + (err.response?.data?.detail || err.message));
    } finally {
        postmanImportLoading.value = false;
    }
};

const resetPostmanImport = () => {
    postmanPreviewData.value = null;
    postmanSelectedApis.value = [];
    postmanRawJsonText.value = "";
    postmanImportSuccessResult.value = null;
};

const goToImportedApisView = () => {
    const targetMachineId = postmanImportMachineId.value;
    postmanImportDialogVisible.value = false;
    currentNav.value = "api_management";
    activeMenuKey.value = "api_management";
    selectedApiEnv.value = "ALL";
    selectedApiMachine.value = targetMachineId || "ALL";
};

export { executeConfirmPostmanImport, goToImportedApisView, handlePostmanFileChange, handlePostmanTextParse, isPostmanApiSelected, onPostmanImportMachineChange, openGenericPostmanImport, openPostmanImportForMachine, postmanConflictPolicy, postmanCronInterval, postmanImportActiveTab, postmanImportDialogVisible, postmanImportLoading, postmanImportMachine, postmanImportMachineId, postmanImportSuccessResult, postmanPreviewData, postmanRawJsonText, postmanSelectedApis, postmanSyncEnvVars, postmanUpdateBaseUrl, resetPostmanImport, togglePostmanApiSelection, toggleSelectAllPostmanApis }
