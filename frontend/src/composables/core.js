import { ref, computed } from 'vue'
import { selectedGroup } from './targets'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const loading = ref(false);

const lastRefreshTime = ref(new Date().toLocaleTimeString());

const targets = ref([]);

const groupList = ref([]);

// 工业级左侧边栏导航控制: 'dashboard' | 'targets' | 'schema_lab' | 'incidents' | 'settings'
const currentNav = ref("dashboard");

const summary = ref({
    total_targets: 0,
    healthy_count: 0,
    down_count: 0,
    degraded_count: 0,
    sla_rate: 100
});

// 环境管理专属响应式状态
const environmentList = ref([]);

// 机器管理专属响应式状态
const machineList = ref([]);

// 接口管理专属响应式状态
const apiList = ref([]);

// 面包屑标题
const navTitle = computed(() => {
    switch (currentNav.value) {
        case "dashboard": return "全局监控大盘";
        case "env_management": return "环境管理";
        case "machine_management": return "机器管理";
        case "api_management": return "接口管理";
        case "scenario_probe": return "场景拨测";
        case "targets": return "环境与服务拨测工作台";
        case "schema_lab": return "Schema 契约演进实验室";
        case "incidents": return "故障告警排障中心";
        case "settings": return "SMTP 邮件配置说明";
        default: return "监控工作台";
    }
});

// 全局监控大盘 - 严格基于【环境管理】(environmentList) 进行纳管分类与态势数据聚合
const dashboardEnvironments = computed(() => {
    // 严格只纳管【环境管理】中配置的真实环境，严禁无主历史脏数据渗透
    const envs = [...environmentList.value].sort((a, b) => (a.order_num || 0) - (b.order_num || 0));

    return envs.map(env => {
        // 1. 严格过滤属于该环境的机器 (通过 environment_id 或 environment_name 精确匹配)
        const envMachines = machineList.value.filter(m => 
            (m.environment_id != null && m.environment_id === env.id) || 
            (m.environment_name && m.environment_name === env.name)
        );
        const machineTotal = envMachines.length;
        const machineOnline = envMachines.filter(m => m.current_status === "ONLINE" || m.current_status === "DEGRADED").length;
        const machineOffline = envMachines.filter(m => m.current_status === "OFFLINE").length;
        
        const validTcp = envMachines.filter(m => m.last_tcp_latency_ms && m.last_tcp_latency_ms > 0);
        const avgTcp = validTcp.length > 0
            ? (validTcp.reduce((acc, cur) => acc + cur.last_tcp_latency_ms, 0) / validTcp.length).toFixed(1)
            : null;

        // 2. 严格过滤属于该环境的接口 (机器下属接口或直属环境接口)
        const machineIds = new Set(envMachines.map(m => m.id));
        const envApis = apiList.value.filter(a => 
            (a.environment_id != null && a.environment_id === env.id) ||
            (a.environment_name && a.environment_name === env.name) ||
            (a.machine_id != null && machineIds.has(a.machine_id))
        );

        const apiTotal = envApis.length;
        const apiHealthy = envApis.filter(a => a.current_status === "HEALTHY").length;
        const apiDown = envApis.filter(a => a.current_status === "DOWN" || a.current_status === "DEGRADED").length;
        const apiCircuitBroken = envApis.filter(a => a.current_status === "CIRCUIT_BROKEN" || a.circuit_broken).length;

        const validHttp = envApis.filter(a => a.last_latency_ms && a.last_latency_ms > 0);
        const avgHttp = validHttp.length > 0
            ? (validHttp.reduce((acc, cur) => acc + cur.last_latency_ms, 0) / validHttp.length).toFixed(0)
            : null;

        // 3. 可用率与健康等级计算
        let slaRate = 0;
        let status = "EMPTY";

        if (machineTotal === 0) {
            // 环境下没有纳管机器时，可用率不应为 100%，归零并标识为未接入
            slaRate = 0;
            status = "EMPTY";
        } else {
            const totalItems = machineTotal + apiTotal;
            const healthyItems = machineOnline + apiHealthy;
            slaRate = Math.round((healthyItems / totalItems) * 100);

            // 4. 环境健康等级判定
            if (machineOffline > 0 || apiDown > 0) {
                status = "DOWN";
            } else if (apiCircuitBroken > 0) {
                status = "DEGRADED";
            } else {
                status = "HEALTHY";
            }
        }

        return {
            id: env.id,
            name: env.name,
            description: env.description,
            order_num: env.order_num || 0,
            status,
            slaRate,
            machines: envMachines,
            machineTotal,
            machineOnline,
            machineOffline,
            avgTcp,
            apis: envApis,
            apiTotal,
            apiHealthy,
            apiDown,
            apiCircuitBroken,
            avgHttp
        };
    });
});

// 全局机器指标 (供 Dashboard 看板使用)
const onlineMachineCount = computed(() => {
    return machineList.value.filter(m => m.current_status === "ONLINE" || m.current_status === "DEGRADED").length;
});

const offlineMachineCount = computed(() => {
    return machineList.value.filter(m => m.current_status === "OFFLINE").length;
});

const avgTcpLatency = computed(() => {
    const valid = machineList.value.filter(m => m.last_tcp_latency_ms && m.last_tcp_latency_ms > 0);
    if (valid.length === 0) return 0;
    const sum = valid.reduce((acc, cur) => acc + cur.last_tcp_latency_ms, 0);
    return (sum / valid.length).toFixed(1);
});

// vue-element-admin 风格侧边栏激活项与展开控制
const activeMenuKey = ref("dashboard");

const handleMenuSelect = (key) => {
    activeMenuKey.value = key;
    if (key === "dashboard") {
        currentNav.value = "dashboard";
    } else if (key === "env_management") {
        currentNav.value = "env_management";
    } else if (key === "machine_management") {
        currentNav.value = "machine_management";
    } else if (key === "api_management") {
        currentNav.value = "api_management";
    } else if (key === "scenario_probe") {
        currentNav.value = "scenario_probe";
    } else if (key.startsWith("targets:")) {
        currentNav.value = "targets";
        selectedGroup.value = key.split(":")[1];
    } else if (key === "schema_lab") {
        currentNav.value = "schema_lab";
    } else if (key === "incidents") {
        currentNav.value = "incidents";
    } else if (key === "settings") {
        currentNav.value = "settings";
    } else if (key === "docs") {
        openDocs();
    }
};

const switchNav = (navKey) => {
    currentNav.value = navKey;
    if (navKey === "targets") {
        activeMenuKey.value = `targets:${selectedGroup.value}`;
    } else {
        activeMenuKey.value = navKey;
    }
};

const filterBySidebarGroup = (grpName) => {
    currentNav.value = "targets";
    selectedGroup.value = grpName;
    activeMenuKey.value = `targets:${grpName}`;
};

const getGroupColor = (name) => {
    if (!name) return "#64748b";
    if (name.includes("生产") || name.toLowerCase().includes("prod")) return "#94a3b8";
    return "#64748b";
};

const getGroupTagType = (name) => {
    return "info";
};

const getStatusBadgeClass = (status) => {
    switch (status) {
        case "HEALTHY": return "status-badge healthy";
        case "DOWN": return "status-badge down";
        case "DEGRADED": return "status-badge degraded";
        case "CIRCUIT_BROKEN": return "status-badge circuit-broken";
        default: return "status-badge unknown";
    }
};

const getStatusIcon = (status) => {
    switch (status) {
        case "HEALTHY": return "fa-solid fa-circle-check";
        case "DOWN": return "fa-solid fa-circle-xmark";
        case "DEGRADED": return "fa-solid fa-triangle-exclamation";
        case "CIRCUIT_BROKEN": return "fa-solid fa-ban";
        default: return "fa-solid fa-circle-question";
    }
};

const fetchData = async (isManual = false) => {
    // 首次全量拉取或用户手动点击刷新时才展示遮罩，后台每 15 秒静默轮询不打扰用户操作
    if (isManual || (!targets.value.length && !apiList.value.length)) {
        loading.value = true;
    }
    try {
        const [targetsRes, summaryRes, groupsRes, envsRes, machinesRes, apisRes] = await Promise.all([
            axios.get("/api/targets"),
            axios.get("/api/dashboard/summary"),
            axios.get("/api/groups"),
            axios.get("/api/environments"),
            axios.get("/api/machines"),
            axios.get("/api/apis")
        ]);
        targets.value = targetsRes.data;
        summary.value = summaryRes.data;
        environmentList.value = envsRes.data;
        machineList.value = machinesRes.data;
        apiList.value = apisRes.data;

        // 统计每个环境下的目标数量与健康状态
        const envMap = {};
        for (const t of targets.value) {
            const gName = t.group_name || "生产环境";
            if (!envMap[gName]) {
                envMap[gName] = { name: gName, total: 0, healthy: 0, down: 0 };
            }
            envMap[gName].total++;
            if (t.current_status === "HEALTHY") envMap[gName].healthy++;
            if (t.current_status === "DOWN" || t.current_status === "DEGRADED") envMap[gName].down++;
        }

        // 仅同步实际在环境管理中的环境资产
        const mergedGroups = [];
        for (const env of environmentList.value) {
            const stats = envMap[env.name] || { name: env.name, total: 0, healthy: 0, down: 0 };
            mergedGroups.push(stats);
        }
        groupList.value = mergedGroups;

        lastRefreshTime.value = new Date().toLocaleTimeString();
        if (isManual) {
            ElMessage.success(`监控大盘数据已同步至最新 (${lastRefreshTime.value})`);
        }
    } catch (err) {
        ElMessage.error("获取监控数据失败: " + (err.response?.data?.detail || err.message));
    } finally {
        loading.value = false;
    }
};

const handleManualRefresh = () => {
    fetchData(true);
};

const formatTime = (isoStr) => {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleString();
};

const formatLatency = (val) => {
    if (val === null || val === undefined) return "待探测";
    return `${val} ms`;
};

const getLatencyBadgeClass = (val) => {
    if (val === null || val === undefined) return "latency-badge unknown";
    if (val < 150) return "latency-badge fast";
    if (val < 500) return "latency-badge normal";
    return "latency-badge slow";
};

const openDocs = () => {
    window.open("/docs", "_blank");
};

export { activeMenuKey, apiList, avgTcpLatency, currentNav, dashboardEnvironments, environmentList, fetchData, filterBySidebarGroup, formatLatency, formatTime, getGroupColor, getGroupTagType, getLatencyBadgeClass, getStatusBadgeClass, getStatusIcon, groupList, handleManualRefresh, handleMenuSelect, lastRefreshTime, loading, machineList, navTitle, offlineMachineCount, onlineMachineCount, openDocs, summary, switchNav, targets }
