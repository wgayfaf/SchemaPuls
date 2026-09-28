import { ref, computed } from 'vue'
import { activeMenuKey, apiList, currentNav, environmentList, fetchData, machineList } from './core'
import { form } from './targets'
import { apiForm, selectedApiEnv, selectedApiMachine, syncPathToParams } from './apis'
import { ElMessage, ElNotification } from 'element-plus'
import axios from 'axios'

const machineDialogVisible = ref(false);

const editingMachineId = ref(null);

const machineSubmitting = ref(false);

const triggeringMachineId = ref(null);

const machineSearchQuery = ref("");

const selectedMachineEnv = ref("ALL");

const machineForm = ref({
    environment_id: null,
    name: "",
    host: "",
    port: 80,
    base_url: "",
    cron_interval_minutes: 5,
    email_input: ""
});

// 环境级变量联动响应式状态
const currentMachineEnvironment = ref({
    environment_id: null,
    name: "默认环境",
    description: "",
    variables: {}
});

const envVarsDialogVisible = ref(false);

const envVariablesList = ref([]);

const envVariablesSaving = ref(false);

// 机器管理专属：按选定环境筛选的机器集合 (当选全部环境时显示全部)
const currentEnvMachinesForKpi = computed(() => {
    if (selectedMachineEnv.value === "ALL") {
        return machineList.value;
    }
    return machineList.value.filter(m => {
        if (m.environment_name === selectedMachineEnv.value) return true;
        const env = environmentList.value.find(e => e.name === selectedMachineEnv.value);
        return env && m.environment_id === env.id;
    });
});

// 机器管理专属：按环境动态联动的 4 项 KPI 指标
const machineEnvTotalCount = computed(() => {
    return currentEnvMachinesForKpi.value.length;
});

const machineEnvOnlineCount = computed(() => {
    return currentEnvMachinesForKpi.value.filter(m => m.current_status === "ONLINE" || m.current_status === "DEGRADED").length;
});

const machineEnvOfflineCount = computed(() => {
    return currentEnvMachinesForKpi.value.filter(m => m.current_status === "OFFLINE").length;
});

const machineEnvAvgTcpLatency = computed(() => {
    const valid = currentEnvMachinesForKpi.value.filter(m => m.last_tcp_latency_ms && m.last_tcp_latency_ms > 0);
    if (valid.length === 0) return 0;
    const sum = valid.reduce((acc, cur) => acc + cur.last_tcp_latency_ms, 0);
    return (sum / valid.length).toFixed(1);
});

const filteredMachines = computed(() => {
    let list = currentEnvMachinesForKpi.value;
    if (machineSearchQuery.value && machineSearchQuery.value.trim()) {
        const q = machineSearchQuery.value.toLowerCase().trim();
        list = list.filter(m => 
            (m.name && m.name.toLowerCase().includes(q)) ||
            (m.host && m.host.toLowerCase().includes(q)) ||
            String(m.port).includes(q) ||
            (m.environment_name && m.environment_name.toLowerCase().includes(q))
        );
    }
    return list;
});

// 当前目标表单环境下的机器列表，供快捷点选
const currentEnvMachines = computed(() => {
    return machineList.value.filter(m => m.environment_name === form.value.group_name);
});

const getMachineApiCount = (machineId) => {
    return apiList.value.filter(a => a.machine_id === machineId).length;
};

// 机器管理 CRUD 与连通性测试
const openCreateMachineDialog = (defaultEnvId = null) => {
    editingMachineId.value = null;
    let envId = defaultEnvId;
    if (!envId) {
        if (selectedMachineEnv.value !== "ALL") {
            const found = environmentList.value.find(e => e.name === selectedMachineEnv.value);
            if (found) envId = found.id;
        }
        if (!envId && environmentList.value.length > 0) {
            envId = environmentList.value[0].id;
        }
    }
    machineForm.value = {
        environment_id: envId,
        name: "",
        host: "",
        port: 80,
        base_url: "",
        cron_interval_minutes: 5,
        email_input: ""
    };
    machineDialogVisible.value = true;
};

const openEditMachineDialog = (row) => {
    editingMachineId.value = row.id;
    machineForm.value = {
        environment_id: row.environment_id,
        name: row.name || "",
        host: row.host || "",
        port: row.port || 80,
        base_url: row.base_url || "",
        cron_interval_minutes: row.cron_interval_minutes || 5,
        email_input: (row.email_receivers && Array.isArray(row.email_receivers))
            ? row.email_receivers.join(", ")
            : (row.email_receivers || "")
    };
    machineDialogVisible.value = true;
};

const submitMachineForm = async () => {
    if (!machineForm.value.name || !machineForm.value.name.trim()) {
        ElMessage.warning("请输入机器名称/别名！");
        return;
    }
    if (!machineForm.value.host || !machineForm.value.host.trim()) {
        ElMessage.warning("请输入主机 IP 或域名！");
        return;
    }
    if (!machineForm.value.port) {
        ElMessage.warning("请输入 TCP 端口！");
        return;
    }
    if (!machineForm.value.environment_id) {
        ElMessage.warning("请选择所属环境！");
        return;
    }

    const receivers = machineForm.value.email_input
        ? machineForm.value.email_input.split(/[,;，；\s]+/).filter(Boolean)
        : [];

    machineSubmitting.value = true;
    try {
        const payload = {
            name: machineForm.value.name.trim(),
            host: machineForm.value.host.trim(),
            port: machineForm.value.port,
            base_url: machineForm.value.base_url ? machineForm.value.base_url.trim() : null,
            environment_id: machineForm.value.environment_id,
            cron_interval_minutes: machineForm.value.cron_interval_minutes || 5,
            is_active: true,
            email_receivers: receivers
        };
        if (editingMachineId.value) {
            await axios.put(`/api/machines/${editingMachineId.value}`, payload);
            ElMessage.success(`机器节点 [${payload.name}] 配置已更新！`);
        } else {
            await axios.post("/api/machines", payload);
            ElMessage.success(`机器节点 [${payload.name}] 已添加并接入定时探活！`);
        }
        machineDialogVisible.value = false;
        await fetchData();
    } catch (err) {
        ElMessage.error((editingMachineId.value ? "更新机器失败: " : "创建机器失败: ") + (err.response?.data?.detail || err.message));
    } finally {
        machineSubmitting.value = false;
    }
};

const handleDeleteMachine = async (machineId, machineName) => {
    try {
        await axios.delete(`/api/machines/${machineId}`);
        ElMessage.success(`机器节点 [${machineName}] 已删除`);
        await fetchData();
    } catch (err) {
        ElMessage.error("删除机器失败: " + (err.response?.data?.detail || err.message));
    }
};

const handleTriggerMachine = async (row) => {
    triggeringMachineId.value = row.id;
    try {
        const res = await axios.post(`/api/machines/${row.id}/trigger`);
        const data = res.data;
        if (data.ping_ok && data.tcp_ok) {
            ElNotification({
                title: `探活正常 [${row.name}]`,
                message: `主机 Ping 正常 (${data.ping_latency_ms ? data.ping_latency_ms + ' ms' : '<1ms'})，端口 ${row.port} 握手成功 (${data.tcp_latency_ms} ms)`,
                type: "success"
            });
        } else if (!data.ping_ok) {
            ElNotification({
                title: `主机不可达/离线 [${row.name}]`,
                message: `目标主机 ${row.host} Ping 不通或超时，机器已判定离线`,
                type: "error",
                duration: 6000
            });
        } else {
            ElNotification({
                title: `主机在线/端口未开启 [${row.name}]`,
                message: `主机在线 (Ping ${data.ping_latency_ms} ms)，但服务端口 ${row.port} 握手失败: ${data.error_message || '连接拒绝'}`,
                type: "warning",
                duration: 6000
            });
        }
        await fetchData();
    } catch (err) {
        ElMessage.error("探测请求失败: " + (err.response?.data?.detail || err.message));
    } finally {
        triggeringMachineId.value = null;
    }
};

const goToMachineTargets = (row) => {
    currentNav.value = "api_management";
    if (row.environment_name) {
        selectedApiEnv.value = row.environment_name;
    } else {
        selectedApiEnv.value = "ALL";
    }
    selectedApiMachine.value = row.id;
    activeMenuKey.value = "api_management";
};

// 接口管理 Postman 风格工作台方法与 CRUD
const selectedMachineDisplayName = computed(() => {
    if (!apiForm.value.machine_id) return "未选择归属机器节点";
    const m = machineList.value.find(item => item.id === apiForm.value.machine_id);
    if (!m) return "未知节点";
    return `${m.name} (${m.host}:${m.port})`;
});

const selectedMachineBaseUrl = computed(() => {
    if (!apiForm.value.machine_id) return "http://host:port";
    const m = machineList.value.find(item => item.id === apiForm.value.machine_id);
    if (!m) return "http://host:port";
    if (m.base_url && m.base_url.trim()) return m.base_url.trim();
    const scheme = m.port === 443 ? "https" : "http";
    return (m.port === 80 || m.port === 443) ? `${scheme}://${m.host}` : `${scheme}://${m.host}:${m.port}`;
});

const selectedMachineHost = selectedMachineBaseUrl;

const resetBaseUrlToMachine = () => {
    apiForm.value.base_url = selectedMachineBaseUrl.value;
    ElMessage.success(`已恢复为当前机器默认地址: ${selectedMachineBaseUrl.value}`);
};

const onPathInput = (val) => {
    if (!val) return;
    const trimmed = String(val).trim();
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
        try {
            const urlObj = new URL(trimmed);
            apiForm.value.base_url = urlObj.origin;
            apiForm.value.http_path = (urlObj.pathname || "/") + urlObj.search + urlObj.hash;
            syncPathToParams(apiForm.value.http_path);
            ElMessage.info("已智能拆分完整 URL 为基准地址与相对路径");
        } catch (e) {
            // 忽略输入过程中的格式异常
        }
    }
};

// 获取机器归属的运行环境及其实时环境变量池
const fetchMachineEnvironment = async (machineId) => {
    if (!machineId) {
        currentMachineEnvironment.value = {
            environment_id: null,
            name: "未指定环境",
            description: "",
            variables: {}
        };
        return;
    }
    try {
        const res = await axios.get(`/api/machines/${machineId}/environment`);
        currentMachineEnvironment.value = {
            environment_id: res.data.environment_id,
            name: res.data.environment_name || "默认环境",
            description: res.data.environment_description || "",
            variables: res.data.variables || {}
        };
    } catch (err) {
        console.error("获取机器归属环境失败:", err);
    }
};

const openEnvDialog = async (targetEnv = null) => {
    let envId = null;
    let envName = "运行环境";
    let envDesc = "";

    // 过滤 Vue 点击事件注入的 MouseEvent/PointerEvent 对象
    if (targetEnv && (targetEnv instanceof Event || targetEnv.target !== undefined)) {
        targetEnv = null;
    }

    if (targetEnv && typeof targetEnv === "object" && targetEnv.id) {
        envId = targetEnv.id;
        envName = targetEnv.name || "运行环境";
        envDesc = targetEnv.description || "";
    } else if (typeof targetEnv === "number") {
        envId = targetEnv;
        const found = environmentList.value.find(e => e.id === envId);
        if (found) {
            envName = found.name;
            envDesc = found.description || "";
        }
    } else if (currentMachineEnvironment.value && currentMachineEnvironment.value.environment_id) {
        envId = currentMachineEnvironment.value.environment_id;
        envName = currentMachineEnvironment.value.name;
        envDesc = currentMachineEnvironment.value.description;
    } else if (apiForm.value.machine_id) {
        await fetchMachineEnvironment(apiForm.value.machine_id);
        envId = currentMachineEnvironment.value.environment_id;
        envName = currentMachineEnvironment.value.name;
        envDesc = currentMachineEnvironment.value.description;
    }

    if (!envId) {
        ElMessage.warning("尚未关联到有效的运行环境，无法查看环境变量");
        return;
    }

    // 实时向后端拉取该环境最新的持久化环境变量池，确保绝对与前置/后置条件生成的变量保持 100% 同步
    envVariablesSaving.value = true;
    try {
        const res = await axios.get(`/api/environments/${envId}/variables`);
        const latestVars = res.data.variables || {};
        currentMachineEnvironment.value = {
            environment_id: envId,
            name: envName,
            description: envDesc,
            variables: latestVars
        };
        const list = Object.entries(latestVars).map(([k, v]) => ({
            key: k,
            value: typeof v === "object" ? JSON.stringify(v) : String(v)
        }));
        if (list.length === 0) {
            list.push({ key: "", value: "" });
        }
        envVariablesList.value = list;
        envVarsDialogVisible.value = true;
    } catch (err) {
        ElMessage.error("获取最新环境变量失败: " + (err.response?.data?.detail || err.message));
    } finally {
        envVariablesSaving.value = false;
    }
};

const addEnvVarRow = () => {
    envVariablesList.value.push({ key: "", value: "" });
};

const removeEnvVarRow = (idx) => {
    envVariablesList.value.splice(idx, 1);
    if (envVariablesList.value.length === 0) {
        envVariablesList.value.push({ key: "", value: "" });
    }
};

const saveEnvVariables = async () => {
    const envId = currentMachineEnvironment.value.environment_id;
    if (!envId) {
        ElMessage.warning("当前机器未关联到具体的运行环境，无法持久化存储环境变量");
        return;
    }
    const varsObj = {};
    for (const item of envVariablesList.value) {
        const k = (item.key || "").trim();
        if (k) {
            let v = item.value;
            try {
                if (typeof v === "string" && (v.startsWith("{") || v.startsWith("["))) {
                    v = JSON.parse(v);
                }
            } catch (e) {
                // 保持原字符串
            }
            varsObj[k] = v;
        }
    }
    envVariablesSaving.value = true;
    try {
        const res = await axios.put(`/api/environments/${envId}/variables`, {
            variables: varsObj
        });
        currentMachineEnvironment.value.variables = res.data.variables || varsObj;
        ElMessage.success(`环境 [${currentMachineEnvironment.value.name}] 变量池已成功保存！共 ${Object.keys(varsObj).length} 个变量`);
        envVarsDialogVisible.value = false;
    } catch (err) {
        ElMessage.error("保存环境变量失败: " + (err.response?.data?.detail || err.message));
    } finally {
        envVariablesSaving.value = false;
    }
};

const copyEnvVarRef = (key) => {
    if (!key) return;
    const textToCopy = `{{${key}}}`;
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(() => {
            ElMessage.success(`已复制引用代码: ${textToCopy}`);
        }).catch(() => {
            copyFallback(textToCopy);
        });
    } else {
        copyFallback(textToCopy);
    }
};

const getVarRef = (key) => {
    return `{{${key || "变量名"}}}`;
};

const copyFallback = (text) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand("copy");
        ElMessage.success(`已复制引用代码: ${text}`);
    } catch (err) {
        ElMessage.warning(`请手动复制: ${text}`);
    }
    document.body.removeChild(textArea);
};

// ==========================================================
// 机器关联外部数据库 (DB Fixture / 目标数据库管理)
// ==========================================================
const machineDbDrawerVisible = ref(false);
const currentMachineForDb = ref(null);
const machineDbList = ref([]);
const loadingMachineDbs = ref(false);
const dbDialogVisible = ref(false);
const editingDbId = ref(null);
const testingDb = ref(false);
const savingDb = ref(false);

const dbForm = ref({
    machine_id: null,
    name: "",
    db_type: "postgresql",
    host: "",
    port: 5432,
    database: "",
    username: "",
    password: "",
    ssl_mode: "prefer",
    pool_size: 10,
    connect_timeout: 10
});

const openMachineDbDrawer = async (machine) => {
    currentMachineForDb.value = machine;
    machineDbDrawerVisible.value = true;
    await fetchMachineDbs(machine.id);
};

const fetchMachineDbs = async (machineId) => {
    if (!machineId) return;
    loadingMachineDbs.value = true;
    try {
        const res = await axios.get(`/api/machine-databases?machine_id=${machineId}`);
        machineDbList.value = res.data || [];
    } catch (err) {
        ElMessage.error("获取机器数据库列表失败: " + (err.response?.data?.detail || err.message));
    } finally {
        loadingMachineDbs.value = false;
    }
};

const openCreateDbDialog = () => {
    editingDbId.value = null;
    const m = currentMachineForDb.value;
    dbForm.value = {
        machine_id: m ? m.id : null,
        name: m ? `${m.name}-PostgreSQL` : "目标数据库",
        db_type: "postgresql",
        host: m ? m.host : "",
        port: 5432,
        database: "",
        username: "postgres",
        password: "",
        ssl_mode: "prefer",
        pool_size: 10,
        connect_timeout: 10
    };
    dbDialogVisible.value = true;
};

const openEditDbDialog = (row) => {
    editingDbId.value = row.id;
    dbForm.value = {
        machine_id: row.machine_id,
        name: row.name || "",
        db_type: row.db_type || "postgresql",
        host: row.host || "",
        port: row.port || 5432,
        database: row.database || "",
        username: row.username || "",
        password: row.password || "",
        ssl_mode: row.ssl_mode || "prefer",
        pool_size: row.pool_size || 10,
        connect_timeout: row.connect_timeout || 10
    };
    dbDialogVisible.value = true;
};

const handleTestDbConnection = async (formOverride = null) => {
    const f = formOverride || dbForm.value;
    if (!f.host || !f.port || !f.database || !f.username) {
        ElMessage.warning("请先填写主机、端口、数据库名和用户名！");
        return;
    }
    testingDb.value = true;
    try {
        const res = await axios.post("/api/machine-databases/test-connection", {
            host: f.host.trim(),
            port: Number(f.port) || 5432,
            database: f.database.trim(),
            username: f.username.trim(),
            password: f.password || "",
            ssl_mode: f.ssl_mode || "prefer",
            connect_timeout: Number(f.connect_timeout) || 10
        });
        if (res.data.ok) {
            ElNotification({
                title: "数据库连接成功",
                message: `${res.data.message} (${res.data.version ? res.data.version.split(',')[0] : ''})`,
                type: "success"
            });
        }
    } catch (err) {
        ElNotification({
            title: "数据库连接失败",
            message: err.response?.data?.detail || err.message,
            type: "error",
            duration: 6000
        });
    } finally {
        testingDb.value = false;
    }
};

const handleSaveDbForm = async () => {
    const f = dbForm.value;
    if (!f.name || !f.name.trim()) {
        ElMessage.warning("请输入数据库配置别名！");
        return;
    }
    if (!f.host || !f.host.trim()) {
        ElMessage.warning("请输入主机地址！");
        return;
    }
    if (!f.database || !f.database.trim()) {
        ElMessage.warning("请输入目标数据库名称！");
        return;
    }
    if (!f.username || !f.username.trim()) {
        ElMessage.warning("请输入数据库用户名！");
        return;
    }

    savingDb.value = true;
    try {
        const payload = {
            machine_id: f.machine_id,
            name: f.name.trim(),
            db_type: "postgresql",
            host: f.host.trim(),
            port: Number(f.port) || 5432,
            database: f.database.trim(),
            username: f.username.trim(),
            password: f.password || "",
            ssl_mode: f.ssl_mode || "prefer",
            pool_size: Math.max(1, Math.min(Number(f.pool_size) || 10, 20)),
            connect_timeout: Number(f.connect_timeout) || 10
        };

        if (editingDbId.value) {
            await axios.put(`/api/machine-databases/${editingDbId.value}`, payload);
            ElMessage.success(`数据库 [${payload.name}] 配置已更新！已自动刷新连接池`);
        } else {
            await axios.post("/api/machine-databases", payload);
            ElMessage.success(`数据库 [${payload.name}] 已添加并接入受控连接池！`);
        }
        dbDialogVisible.value = false;
        if (currentMachineForDb.value) {
            await fetchMachineDbs(currentMachineForDb.value.id);
        }
    } catch (err) {
        ElMessage.error((editingDbId.value ? "更新数据库失败: " : "添加数据库失败: ") + (err.response?.data?.detail || err.message));
    } finally {
        savingDb.value = false;
    }
};

const handleDeleteDb = async (dbId, dbName) => {
    try {
        await axios.delete(`/api/machine-databases/${dbId}`);
        ElMessage.success(`数据库 [${dbName}] 已删除，连接池已释放`);
        if (currentMachineForDb.value) {
            await fetchMachineDbs(currentMachineForDb.value.id);
        }
    } catch (err) {
        ElMessage.error("删除数据库配置失败: " + (err.response?.data?.detail || err.message));
    }
};

export {
    addEnvVarRow, copyEnvVarRef, copyFallback, currentEnvMachines, currentEnvMachinesForKpi,
    currentMachineEnvironment, editingMachineId, envVariablesList, envVariablesSaving,
    envVarsDialogVisible, fetchMachineEnvironment, filteredMachines, getMachineApiCount,
    getVarRef, goToMachineTargets, handleDeleteMachine, handleTriggerMachine, machineDialogVisible,
    machineEnvAvgTcpLatency, machineEnvOfflineCount, machineEnvOnlineCount, machineEnvTotalCount,
    machineForm, machineSearchQuery, machineSubmitting, onPathInput, openCreateMachineDialog,
    openEditMachineDialog, openEnvDialog, removeEnvVarRow, resetBaseUrlToMachine, saveEnvVariables,
    selectedMachineBaseUrl, selectedMachineDisplayName, selectedMachineEnv, selectedMachineHost,
    submitMachineForm, triggeringMachineId,
    // 数据库管理导出
    machineDbDrawerVisible, currentMachineForDb, machineDbList, loadingMachineDbs, dbDialogVisible,
    editingDbId, testingDb, savingDb, dbForm, openMachineDbDrawer, fetchMachineDbs, openCreateDbDialog,
    openEditDbDialog, handleTestDbConnection, handleSaveDbForm, handleDeleteDb
}
