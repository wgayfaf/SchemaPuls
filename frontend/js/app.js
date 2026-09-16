/**
 * SchemaPulse 前端核心业务逻辑
 * 前后端分离架构下驱动 Vue 3 + Element-Plus + ECharts
 */

// 配置 Axios 默认基础 API 路由 (支持前后端分离与远程 API)
if (window.API_BASE_URL) {
    axios.defaults.baseURL = window.API_BASE_URL;
} else if (window.SCHEMA_PULSE_CONFIG && window.SCHEMA_PULSE_CONFIG.API_BASE_URL) {
    axios.defaults.baseURL = window.SCHEMA_PULSE_CONFIG.API_BASE_URL;
} else {
    axios.defaults.baseURL = "http://127.0.0.1:8000";
}

// 全局请求拦截与错误兜底
axios.interceptors.response.use(
    response => response,
    error => {
        if (error.code === "ERR_NETWORK" || !error.response) {
            console.error("[SchemaPulse API Network Error]", error);
        }
        return Promise.reject(error);
    }
);

const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

const app = createApp({
    setup() {
        const loading = ref(false);
        const lastRefreshTime = ref(new Date().toLocaleTimeString());
        const targets = ref([]);
        const groupList = ref([]);
        const selectedGroup = ref("ALL");

        // 工业级左侧边栏导航控制: 'dashboard' | 'targets' | 'schema_lab' | 'incidents' | 'settings'
        const currentNav = ref("dashboard");

        const summary = ref({
            total_targets: 0,
            healthy_count: 0,
            down_count: 0,
            degraded_count: 0,
            sla_rate: 100
        });

        const triggeringId = ref(null);
        const createDialogVisible = ref(false);
        const editingTargetId = ref(null);
        const submitting = ref(false);
        const inferring = ref(false);

        // 环境管理专属响应式状态
        const environmentList = ref([]);
        const envDialogVisible = ref(false);
        const editingEnvId = ref(null);
        const envSubmitting = ref(false);
        const envSearchQuery = ref("");
        const envForm = ref({
            name: "",
            description: "",
            order_num: 0
        });

        // 机器管理专属响应式状态
        const machineList = ref([]);
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
            email_input: "admin@company.com"
        });

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

        // 接口管理专属响应式状态
        const apiList = ref([]);
        const apiDialogVisible = ref(false);
        const editingApiId = ref(null);
        const apiSubmitting = ref(false);
        const triggeringApiId = ref(null);
        const apiSearchQuery = ref("");
        const selectedApiEnv = ref("ALL");
        const selectedApiMachine = ref("ALL");
        const selectedApiStatus = ref("ALL");
        const apiSampleJson = ref("");
        const apiInferring = ref(false);
        const apiForm = ref({
            machine_id: null,
            name: "",
            base_url: "",
            http_path: "",
            http_method: "GET",
            cron_interval_minutes: 5,
            email_input: "admin@company.com",
            schema_text: ""
        });

        // Postman 风格工作台专属响应式状态
        const apiActiveTab = ref("params"); // 'params' | 'headers' | 'body' | 'auth' | 'schema'
        const apiResponseTab = ref("body"); // 'body' | 'headers'
        const apiParamsList = ref([
            { enabled: true, key: "", value: "", description: "" }
        ]);
        // Postman 风格系统默认自动生成请求头
        const createDefaultHeaders = () => [
            { enabled: true, key: "User-Agent", value: "SchemaPulse/2.0 (PostmanRuntime)", description: "客户端探针引擎标识", isSystem: true, isCalculated: false },
            { enabled: true, key: "Accept", value: "*/*", description: "默认允许接收所有响应类型", isSystem: true, isCalculated: false },
            { enabled: true, key: "Accept-Encoding", value: "gzip, deflate, br", description: "客户端支持的压缩算法", isSystem: true, isCalculated: false },
            { enabled: true, key: "Connection", value: "keep-alive", description: "保持 HTTP 长连接", isSystem: true, isCalculated: false },
            { enabled: true, key: "Host", value: "<根据请求目标地址自动解析>", description: "根据目标地址动态解析主机名", isSystem: true, isCalculated: true },
            { enabled: true, key: "Content-Type", value: "application/json", description: "根据请求体格式自动配置", isSystem: true, isCalculated: false, isDynamicType: true },
            { enabled: true, key: "Content-Length", value: "<根据请求体大小自动计算>", description: "根据请求体实际长度动态填充", isSystem: true, isCalculated: true }
        ];

        const systemDefaultHeaders = ref(createDefaultHeaders());
        const showDefaultHeaders = ref(false); // 默认收起 Postman 预填请求头，用户主动点击后才展开

        const apiHeadersList = ref([
            { enabled: true, key: "", value: "", description: "" }
        ]);
        const apiBodyType = ref("none"); // 'none' | 'json' | 'form'
        const apiBodyText = ref("");
        const apiAuthType = ref("none"); // 'none' | 'bearer' | 'basic' | 'custom'
        const apiAuthConfig = ref({
            token: "",
            username: "",
            password: "",
            header_key: "Authorization",
            header_value: ""
        });
        const apiPreActionsList = ref([]);
        const apiPostActionsList = ref([]);
        const apiTestRunning = ref(false);
        const apiTestResult = ref(null);

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

        const sampleJsonText = ref("");
        const form = ref({
            name: "",
            group_name: "生产环境",
            host: "",
            port: 80,
            http_path: "",
            http_method: "GET",
            cron_interval_minutes: 5,
            email_input: "admin@company.com",
            schema_text: JSON.stringify({
                type: "object",
                required: ["headers", "origin", "url"],
                properties: {
                    origin: { type: "string" },
                    url: { type: "string" },
                    headers: { type: "object" }
                }
            }, null, 2)
        });

        // 契约演进实验室专属数据 (契约推导 + 破坏性变更演进仿真)
        const labActiveTab = ref("infer"); // 'infer' | 'validate'
        const labJsonInput = ref(JSON.stringify({
            code: 200,
            status: "success",
            user: {
                id: 10086,
                name: "Developer",
                roles: ["admin", "tester"]
            }
        }, null, 2));
        const labStrictMode = ref(true);
        const labSchemaOutput = ref("");
        const labInferring = ref(false);

        // 破坏性变更演进校验仿真专属数据
        const labValidateSchemaText = ref(JSON.stringify({
            type: "object",
            required: ["code", "status", "user"],
            properties: {
                code: { type: "integer" },
                status: { type: "string" },
                user: {
                    type: "object",
                    required: ["id", "name", "roles"],
                    properties: {
                        id: { type: "integer" },
                        name: { type: "string" },
                        roles: { type: "array" }
                    }
                }
            }
        }, null, 2));
        const labValidateJsonText = ref(JSON.stringify({
            code: "200",
            status: "success",
            user: {
                id: "10086",
                name: "Developer"
            }
        }, null, 2));
        const labValidating = ref(false);
        const labValidationResult = ref(null);

        // 抽屉与图表
        const drawerVisible = ref(false);
        const activeTarget = ref(null);
        const loadingHistory = ref(false);
        const historyList = ref([]);
        let echartsInstance = null;

        // 面包屑标题
        const navTitle = computed(() => {
            switch (currentNav.value) {
                case "dashboard": return "全局监控大盘";
                case "env_management": return "环境管理";
                case "machine_management": return "机器管理";
                case "api_management": return "接口管理";
                case "targets": return "环境与服务拨测工作台";
                case "schema_lab": return "Schema 契约演进实验室";
                case "incidents": return "故障告警排障中心";
                case "settings": return "SMTP 邮件配置说明";
                default: return "监控工作台";
            }
        });

        // 故障异常节点提取 (用于 Incidents 视图)
        // 核心规则：严格只纳管【接口管理】(apiList) 中当前真实存在的受损接口，接口管理中没有的接口绝对不显示
        const incidentSearchQuery = ref("");
        const downTargets = computed(() => {
            return apiList.value.filter(a => 
                a.current_status === "DOWN" || 
                a.current_status === "DEGRADED" || 
                a.current_status === "CIRCUIT_BROKEN"
            );
        });
        const filteredDownTargets = computed(() => {
            if (!incidentSearchQuery.value || !incidentSearchQuery.value.trim()) {
                return downTargets.value;
            }
            const q = incidentSearchQuery.value.toLowerCase().trim();
            return downTargets.value.filter(a => 
                (a.name && a.name.toLowerCase().includes(q)) ||
                (a.machine_host && a.machine_host.toLowerCase().includes(q)) ||
                (a.machine_name && a.machine_name.toLowerCase().includes(q)) ||
                (a.http_path && a.http_path.toLowerCase().includes(q)) ||
                (a.environment_name && a.environment_name.toLowerCase().includes(q))
            );
        });

        // 根据选中的环境分组过滤
        const filteredTargets = computed(() => {
            if (selectedGroup.value === "ALL") {
                return targets.value;
            }
            return targets.value.filter(t => (t.group_name || "默认环境") === selectedGroup.value);
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

        // 全局接口指标 (供 Dashboard 看板使用)
        const healthyApiCount = computed(() => {
            return apiList.value.filter(a => a.current_status === "HEALTHY").length;
        });

        const issueApiCount = computed(() => {
            return apiList.value.filter(a => a.current_status === "DOWN" || a.current_status === "DEGRADED" || a.current_status === "CIRCUIT_BROKEN").length;
        });

        const avgApiLatency = computed(() => {
            const valid = apiList.value.filter(a => a.last_http_latency_ms && a.last_http_latency_ms > 0);
            if (valid.length === 0) return 0;
            const sum = valid.reduce((acc, cur) => acc + cur.last_http_latency_ms, 0);
            return (sum / valid.length).toFixed(1);
        });

        const currentEnvMachineOptions = computed(() => {
            if (selectedApiEnv.value === "ALL") {
                return machineList.value;
            }
            return machineList.value.filter(m => {
                if (m.environment_name === selectedApiEnv.value) return true;
                const env = environmentList.value.find(e => e.name === selectedApiEnv.value);
                return env && m.environment_id === env.id;
            });
        });

        // 接口管理专属：按选定环境筛选的接口集合 (当选全部环境时显示全部)
        const currentEnvApisForKpi = computed(() => {
            if (selectedApiEnv.value === "ALL") {
                return apiList.value;
            }
            return apiList.value.filter(a => {
                if (a.environment_name === selectedApiEnv.value) return true;
                const env = environmentList.value.find(e => e.name === selectedApiEnv.value);
                return env && a.environment_id === env.id;
            });
        });

        // 接口管理专属：按环境动态联动的 5 项核心指标
        const apiEnvTotalCount = computed(() => {
            return currentEnvApisForKpi.value.length;
        });

        const apiEnvOnlineMachineCount = computed(() => {
            return currentEnvMachineOptions.value.filter(m => m.current_status === "ONLINE" || m.current_status === "DEGRADED").length;
        });

        const apiEnvHealthyCount = computed(() => {
            return currentEnvApisForKpi.value.filter(a => a.current_status === "HEALTHY").length;
        });

        const apiEnvIssueCount = computed(() => {
            return currentEnvApisForKpi.value.filter(a => a.current_status === "DOWN" || a.current_status === "DEGRADED" || a.current_status === "CIRCUIT_BROKEN").length;
        });

        const apiEnvAvgLatency = computed(() => {
            const valid = currentEnvApisForKpi.value.filter(a => a.last_http_latency_ms && a.last_http_latency_ms > 0);
            if (valid.length === 0) return 0;
            const sum = valid.reduce((acc, cur) => acc + cur.last_http_latency_ms, 0);
            return (sum / valid.length).toFixed(1);
        });

        const filteredApis = computed(() => {
            let list = currentEnvApisForKpi.value;
            if (selectedApiMachine.value !== "ALL") {
                list = list.filter(a => a.machine_id === selectedApiMachine.value);
            }
            if (selectedApiStatus.value !== "ALL") {
                list = list.filter(a => a.current_status === selectedApiStatus.value);
            }
            if (apiSearchQuery.value && apiSearchQuery.value.trim()) {
                const q = apiSearchQuery.value.toLowerCase().trim();
                list = list.filter(a =>
                    (a.name && a.name.toLowerCase().includes(q)) ||
                    (a.http_path && a.http_path.toLowerCase().includes(q)) ||
                    (a.full_url && a.full_url.toLowerCase().includes(q)) ||
                    (a.machine_name && a.machine_name.toLowerCase().includes(q))
                );
            }
            return list;
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
            loading.value = true;
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
                    ElementPlus.ElMessage.success(`监控大盘数据已同步至最新 (${lastRefreshTime.value})`);
                }
            } catch (err) {
                ElementPlus.ElMessage.error("获取监控数据失败: " + (err.response?.data?.detail || err.message));
            } finally {
                loading.value = false;
            }
        };

        const handleManualRefresh = () => {
            fetchData(true);
        };

        const handleTrigger = async (row) => {
            triggeringId.value = row.id;
            try {
                const res = await axios.post(`/api/targets/${row.id}/trigger`);
                const data = res.data;
                if (data.is_healthy) {
                    ElementPlus.ElNotification({
                        title: `探测连通正常 [${row.name}]`,
                        message: `TCP: ${data.tcp_latency_ms}ms | HTTP 200: ${data.http_latency_ms}ms | 契约 Schema 完全匹配`,
                        type: "success"
                    });
                } else {
                    let errMsg = "探测异常: ";
                    if (!data.tcp_ok) errMsg += "TCP 端口未开放; ";
                    if (data.http_status_code !== 200) errMsg += `HTTP 状态码 ${data.http_status_code}; `;
                    if (!data.schema_matched) errMsg += "Schema 捕获破坏性结构变更; ";

                    ElementPlus.ElNotification({
                        title: `服务异常预警 [${row.name}]`,
                        message: errMsg,
                        type: "error",
                        duration: 6000
                    });
                }
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("探测请求异常: " + (err.response?.data?.detail || err.message));
            } finally {
                triggeringId.value = null;
            }
        };

        const handleDelete = async (targetId) => {
            try {
                await axios.delete(`/api/targets/${targetId}`);
                ElementPlus.ElMessage.success("监控目标已从当前环境移除");
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("删除失败: " + (err.response?.data?.detail || err.message));
            }
        };

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
                ElementPlus.ElMessage.warning("请输入环境名称！");
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
                    ElementPlus.ElMessage.success(`环境 [${payload.name}] 修改成功！`);
                } else {
                    await axios.post("/api/environments", payload);
                    ElementPlus.ElMessage.success(`环境 [${payload.name}] 创建成功！`);
                }
                envDialogVisible.value = false;
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error((editingEnvId.value ? "修改环境失败: " : "创建环境失败: ") + (err.response?.data?.detail || err.message));
            } finally {
                envSubmitting.value = false;
            }
        };

        const handleDeleteEnv = async (envId, envName) => {
            try {
                await axios.delete(`/api/environments/${envId}`);
                ElementPlus.ElMessage.success(`环境 [${envName}] 及其下属资产已删除`);
                if (selectedGroup.value === envName) {
                    selectedGroup.value = "ALL";
                    activeMenuKey.value = "targets:ALL";
                }
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("删除环境失败: " + (err.response?.data?.detail || err.message));
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
                email_input: "admin@company.com"
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
                ElementPlus.ElMessage.warning("请输入机器名称/别名！");
                return;
            }
            if (!machineForm.value.host || !machineForm.value.host.trim()) {
                ElementPlus.ElMessage.warning("请输入主机 IP 或域名！");
                return;
            }
            if (!machineForm.value.port) {
                ElementPlus.ElMessage.warning("请输入 TCP 端口！");
                return;
            }
            if (!machineForm.value.environment_id) {
                ElementPlus.ElMessage.warning("请选择所属环境！");
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
                    ElementPlus.ElMessage.success(`机器节点 [${payload.name}] 配置已更新！`);
                } else {
                    await axios.post("/api/machines", payload);
                    ElementPlus.ElMessage.success(`机器节点 [${payload.name}] 已添加并接入定时探活！`);
                }
                machineDialogVisible.value = false;
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error((editingMachineId.value ? "更新机器失败: " : "创建机器失败: ") + (err.response?.data?.detail || err.message));
            } finally {
                machineSubmitting.value = false;
            }
        };

        const handleDeleteMachine = async (machineId, machineName) => {
            try {
                await axios.delete(`/api/machines/${machineId}`);
                ElementPlus.ElMessage.success(`机器节点 [${machineName}] 已删除`);
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("删除机器失败: " + (err.response?.data?.detail || err.message));
            }
        };

        const handleTriggerMachine = async (row) => {
            triggeringMachineId.value = row.id;
            try {
                const res = await axios.post(`/api/machines/${row.id}/trigger`);
                const data = res.data;
                if (data.ping_ok && data.tcp_ok) {
                    ElementPlus.ElNotification({
                        title: `探活正常 [${row.name}]`,
                        message: `主机 Ping 正常 (${data.ping_latency_ms ? data.ping_latency_ms + ' ms' : '<1ms'})，端口 ${row.port} 握手成功 (${data.tcp_latency_ms} ms)`,
                        type: "success"
                    });
                } else if (!data.ping_ok) {
                    ElementPlus.ElNotification({
                        title: `主机不可达/离线 [${row.name}]`,
                        message: `目标主机 ${row.host} Ping 不通或超时，机器已判定离线`,
                        type: "error",
                        duration: 6000
                    });
                } else {
                    ElementPlus.ElNotification({
                        title: `主机在线/端口未开启 [${row.name}]`,
                        message: `主机在线 (Ping ${data.ping_latency_ms} ms)，但服务端口 ${row.port} 握手失败: ${data.error_message || '连接拒绝'}`,
                        type: "warning",
                        duration: 6000
                    });
                }
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("探测请求失败: " + (err.response?.data?.detail || err.message));
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
            ElementPlus.ElMessage.success(`已恢复为当前机器默认地址: ${selectedMachineBaseUrl.value}`);
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
                    ElementPlus.ElMessage.info("已智能拆分完整 URL 为基准地址与相对路径");
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

        const openEnvDialog = () => {
            const vars = currentMachineEnvironment.value.variables || {};
            const list = Object.entries(vars).map(([k, v]) => ({
                key: k,
                value: typeof v === "object" ? JSON.stringify(v) : String(v)
            }));
            if (list.length === 0) {
                list.push({ key: "", value: "" });
            }
            envVariablesList.value = list;
            envVarsDialogVisible.value = true;
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
                ElementPlus.ElMessage.warning("当前机器未关联到具体的运行环境，无法持久化存储环境变量");
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
                ElementPlus.ElMessage.success(`环境 [${currentMachineEnvironment.value.name}] 变量池已成功保存！共 ${Object.keys(varsObj).length} 个变量`);
                envVarsDialogVisible.value = false;
            } catch (err) {
                ElementPlus.ElMessage.error("保存环境变量失败: " + (err.response?.data?.detail || err.message));
            } finally {
                envVariablesSaving.value = false;
            }
        };

        const copyEnvVarRef = (key) => {
            if (!key) return;
            const textToCopy = `{{${key}}}`;
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    ElementPlus.ElMessage.success(`已复制引用代码: ${textToCopy}`);
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
                ElementPlus.ElMessage.success(`已复制引用代码: ${text}`);
            } catch (err) {
                ElementPlus.ElMessage.warning(`请手动复制: ${text}`);
            }
            document.body.removeChild(textArea);
        };

        // 监听机器选择变动，自动同步更新 Base URL 与该机器归属的环境及变量池
        watch(() => apiForm.value.machine_id, (newMId) => {
            if (!newMId) return;
            fetchMachineEnvironment(newMId);
            const m = machineList.value.find(item => item.id === newMId);
            if (!m) return;
            if (m.base_url && m.base_url.trim()) {
                apiForm.value.base_url = m.base_url.trim();
            } else {
                const scheme = m.port === 443 ? "https" : "http";
                apiForm.value.base_url = (m.port === 80 || m.port === 443) ? `${scheme}://${m.host}` : `${scheme}://${m.host}:${m.port}`;
            }
        });

        let isSyncingUrlParams = false;

        const syncParamsToPath = () => {
            if (isSyncingUrlParams) return;
            isSyncingUrlParams = true;
            try {
                const currentPath = apiForm.value.http_path || "";
                const basePath = currentPath.includes("?") ? currentPath.split("?")[0] : currentPath;
                const activePairs = apiParamsList.value.filter(p => p.enabled && p.key && p.key.trim() !== "");
                if (activePairs.length === 0) {
                    apiForm.value.http_path = basePath;
                } else {
                    const q = activePairs.map(p => `${encodeURIComponent(p.key.trim())}=${encodeURIComponent(p.value || "")}`).join("&");
                    apiForm.value.http_path = basePath ? `${basePath}?${q}` : `?${q}`;
                }
            } finally {
                isSyncingUrlParams = false;
            }
        };

        const syncPathToParams = (newPath) => {
            if (isSyncingUrlParams) return;
            isSyncingUrlParams = true;
            try {
                if (!newPath || !newPath.includes("?")) {
                    return;
                }
                const queryString = newPath.split("?")[1];
                if (!queryString) return;
                const searchParams = new URLSearchParams(queryString);
                const newParams = [];
                searchParams.forEach((val, key) => {
                    newParams.push({ enabled: true, key, value: val, description: "" });
                });
                if (newParams.length > 0) {
                    apiParamsList.value = newParams;
                }
            } catch (e) {
                // 忽略路径输入过程中的格式异常
            } finally {
                isSyncingUrlParams = false;
            }
        };

        const addParamRow = () => {
            apiParamsList.value.push({ enabled: true, key: "", value: "", description: "" });
        };

        const removeParamRow = (idx) => {
            apiParamsList.value.splice(idx, 1);
            if (apiParamsList.value.length === 0) {
                apiParamsList.value.push({ enabled: true, key: "", value: "", description: "" });
            }
            syncParamsToPath();
        };

        const addHeaderRow = () => {
            apiHeadersList.value.push({ enabled: true, key: "", value: "", description: "" });
        };

        const removeHeaderRow = (idx) => {
            apiHeadersList.value.splice(idx, 1);
            if (apiHeadersList.value.length === 0) {
                apiHeadersList.value.push({ enabled: true, key: "", value: "", description: "" });
            }
        };

        // 判断指定 Key 是否已被用户自定义请求头覆盖 (不区分大小写)
        const isHeaderOverridden = (key) => {
            if (!key) return false;
            const lowerKey = key.trim().toLowerCase();
            return apiHeadersList.value.some(h => 
                h.enabled && h.key && h.key.trim().toLowerCase() === lowerKey
            );
        };

        // 计算当前生效且未被覆盖的系统默认请求头数量
        const activeDefaultHeadersCount = computed(() => {
            return systemDefaultHeaders.value.filter(h => h.enabled && !isHeaderOverridden(h.key)).length;
        });

        // 组装最终真实发包的有效请求头集合 (自定义请求头优先并覆盖同名系统默认)
        const getEffectiveHeaders = () => {
            const result = [];
            const lowerCustomKeys = new Set();

            // 1. 优先加入用户自定义且启用的有效请求头
            apiHeadersList.value.forEach(h => {
                if (h.enabled && h.key && h.key.trim()) {
                    result.push({
                        enabled: true,
                        key: h.key.trim(),
                        value: h.value !== undefined && h.value !== null ? String(h.value) : "",
                        description: h.description || ""
                    });
                    lowerCustomKeys.add(h.key.trim().toLowerCase());
                }
            });

            // 2. 补充分配未被覆盖、启用的系统默认请求头 (排除纯界面占位标记 isCalculated)
            systemDefaultHeaders.value.forEach(h => {
                if (h.enabled && !lowerCustomKeys.has(h.key.trim().toLowerCase())) {
                    if (!h.isCalculated) {
                        result.push({
                            enabled: true,
                            key: h.key.trim(),
                            value: h.value !== undefined && h.value !== null ? String(h.value) : "",
                            description: h.description || ""
                        });
                    }
                }
            });

            return result;
        };

        // 监听 Body 类型变动，自动同步系统默认 Content-Type
        watch(apiBodyType, (newType) => {
            const ct = systemDefaultHeaders.value.find(h => h.key.toLowerCase() === 'content-type');
            if (ct) {
                if (newType === 'json') {
                    ct.enabled = true;
                    ct.value = 'application/json';
                    ct.description = '根据 Body 格式自动设置 (JSON 数据类型)';
                } else if (newType === 'form') {
                    ct.enabled = true;
                    ct.value = 'application/x-www-form-urlencoded';
                    ct.description = '根据 Body 格式自动设置 (表单数据)';
                } else {
                    ct.enabled = false;
                    ct.description = '无需请求体 (Body 为 none)';
                }
            }
        });

        const insertMacroToBody = (macroType) => {
            let snippet = "";
            if (macroType === 'timestamp') snippet = '"{{$timestamp}}"';
            else if (macroType === 'uuid') snippet = '"{{$uuid}}"';
            else if (macroType === 'randomInt') snippet = '{{$randomInt(1000, 9999)}}';
            else snippet = macroType;
            apiBodyText.value = (apiBodyText.value || "") + snippet;
        };

        // JSON 格式化核心解析器 (容错支持未加引号的模板宏)
        const safeFormatJson = (rawStr) => {
            if (!rawStr || !rawStr.trim()) return "";
            const trimmed = rawStr.trim();
            try {
                const obj = JSON.parse(trimmed);
                return JSON.stringify(obj, null, 2);
            } catch (e1) {
                const macroTokens = [];
                const masked = trimmed.replace(/(?<!")(\{\{[\w$().,-]+\}\})(?!")/g, (match) => {
                    const placeholder = `"__SP_MACRO_${macroTokens.length}__"`;
                    macroTokens.push(match);
                    return placeholder;
                });
                try {
                    const obj = JSON.parse(masked);
                    let formatted = JSON.stringify(obj, null, 2);
                    macroTokens.forEach((original, idx) => {
                        formatted = formatted.replace(`"__SP_MACRO_${idx}__"`, original);
                    });
                    return formatted;
                } catch (e2) {
                    throw e1;
                }
            }
        };

        const safeMinifyJson = (rawStr) => {
            if (!rawStr || !rawStr.trim()) return "";
            const trimmed = rawStr.trim();
            try {
                const obj = JSON.parse(trimmed);
                return JSON.stringify(obj);
            } catch (e1) {
                const macroTokens = [];
                const masked = trimmed.replace(/(?<!")(\{\{[\w$().,-]+\}\})(?!")/g, (match) => {
                    const placeholder = `"__SP_MACRO_${macroTokens.length}__"`;
                    macroTokens.push(match);
                    return placeholder;
                });
                try {
                    const obj = JSON.parse(masked);
                    let minified = JSON.stringify(obj);
                    macroTokens.forEach((original, idx) => {
                        minified = minified.replace(`"__SP_MACRO_${idx}__"`, original);
                    });
                    return minified;
                } catch (e2) {
                    throw e1;
                }
            }
        };

        const formatBodyJson = () => {
            if (!apiBodyText.value || !apiBodyText.value.trim()) {
                ElementPlus.ElMessage.warning("当前 Body 请求体为空，无需格式化");
                return;
            }
            try {
                apiBodyText.value = safeFormatJson(apiBodyText.value);
                ElementPlus.ElMessage.success("Body JSON 格式化完成！");
            } catch (err) {
                ElementPlus.ElMessage.error("JSON 格式错误: " + (err.message || "无法解析有效 JSON"));
            }
        };

        const minifyBodyJson = () => {
            if (!apiBodyText.value || !apiBodyText.value.trim()) {
                ElementPlus.ElMessage.warning("当前 Body 请求体为空");
                return;
            }
            try {
                apiBodyText.value = safeMinifyJson(apiBodyText.value);
                ElementPlus.ElMessage.success("Body JSON 已压缩为紧凑单行格式！");
            } catch (err) {
                ElementPlus.ElMessage.error("JSON 格式错误: " + (err.message || "无法解析有效 JSON"));
            }
        };

        const clearBodyJson = () => {
            apiBodyText.value = "";
            ElementPlus.ElMessage.info("已清空 Body 内容");
        };

        const formatSchemaJson = () => {
            if (!apiForm.value.schema_text || !apiForm.value.schema_text.trim()) {
                ElementPlus.ElMessage.warning("当前 Schema 内容为空，无需格式化");
                return;
            }
            try {
                apiForm.value.schema_text = safeFormatJson(apiForm.value.schema_text);
                ElementPlus.ElMessage.success("Schema 契约规则格式化完成！");
            } catch (err) {
                ElementPlus.ElMessage.error("Schema 格式错误: " + (err.message || "无法解析有效 JSON"));
            }
        };

        const formatSampleJson = () => {
            if (!apiSampleJson.value || !apiSampleJson.value.trim()) {
                ElementPlus.ElMessage.warning("样本 JSON 内容为空，无需格式化");
                return;
            }
            try {
                apiSampleJson.value = safeFormatJson(apiSampleJson.value);
                ElementPlus.ElMessage.success("样本 JSON 格式化完成！");
            } catch (err) {
                ElementPlus.ElMessage.error("样本 JSON 格式错误: " + (err.message || "无法解析有效 JSON"));
            }
        };

        const copyResponseBody = async () => {
            if (!apiTestResult.value || !apiTestResult.value.response_data) {
                ElementPlus.ElMessage.warning("当前无有效响应数据可复制");
                return;
            }
            try {
                const text = JSON.stringify(apiTestResult.value.response_data, null, 2);
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(text);
                } else {
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    document.body.removeChild(ta);
                }
                ElementPlus.ElMessage.success("响应 JSON 已成功复制到剪贴板！");
            } catch (err) {
                ElementPlus.ElMessage.error("复制失败: " + err.message);
            }
        };

        const formatIfJson = (str) => {
            if (!str) return "";
            try {
                const parsed = JSON.parse(str);
                return JSON.stringify(parsed, null, 2);
            } catch {
                return str;
            }
        };

        const copyText = async (text) => {
            if (!text) return;
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(text);
                } else {
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    document.body.removeChild(ta);
                }
                ElementPlus.ElMessage.success("已复制到剪贴板！");
            } catch (err) {
                ElementPlus.ElMessage.error("复制失败: " + err.message);
            }
        };

        const openCreateApiDialog = (defaultMachineId = null) => {
            editingApiId.value = null;
            let mId = defaultMachineId;
            if (!mId) {
                if (selectedApiMachine.value !== "ALL") {
                    mId = selectedApiMachine.value;
                } else if (machineList.value.length > 0) {
                    mId = machineList.value[0].id;
                }
            }
            let initialBaseUrl = "";
            if (mId) {
                const m = machineList.value.find(item => item.id === mId);
                if (m) {
                    if (m.base_url && m.base_url.trim()) {
                        initialBaseUrl = m.base_url.trim();
                    } else {
                        const scheme = m.port === 443 ? "https" : "http";
                        initialBaseUrl = (m.port === 80 || m.port === 443) ? `${scheme}://${m.host}` : `${scheme}://${m.host}:${m.port}`;
                    }
                }
            }

            if (mId) {
                fetchMachineEnvironment(mId);
            }

            apiForm.value = {
                machine_id: mId,
                name: "",
                base_url: initialBaseUrl,
                http_path: "",
                http_method: "GET",
                cron_interval_minutes: 5,
                email_input: "admin@company.com",
                schema_text: ""
            };
            apiSampleJson.value = "";
            apiActiveTab.value = "params";
            apiResponseTab.value = "body";
            apiParamsList.value = [
                { enabled: true, key: "", value: "", description: "" }
            ];
            systemDefaultHeaders.value = createDefaultHeaders();
            showDefaultHeaders.value = false;
            apiHeadersList.value = [
                { enabled: true, key: "", value: "", description: "" }
            ];
            apiBodyType.value = "none";
            apiBodyText.value = "";
            apiAuthType.value = "none";
            apiAuthConfig.value = {
                token: "",
                username: "",
                password: "",
                header_key: "Authorization",
                header_value: ""
            };
            apiPreActionsList.value = [];
            apiPostActionsList.value = [
                { enabled: true, name: "HTTP 状态码等于 200", type: "assert_status_code", expression: "", operator: "equals", target_value: "200", description: "" }
            ];
            apiTestResult.value = null;
            apiDialogVisible.value = true;
        };

        const addPreActionRow = () => {
            apiPreActionsList.value.push({
                enabled: true,
                type: "set_variable",
                key: "",
                value: "",
                description: ""
            });
        };

        const removePreActionRow = (idx) => {
            apiPreActionsList.value.splice(idx, 1);
        };

        const applyPreActionPreset = (preset) => {
            if (preset === 'js_script') {
                apiPreActionsList.value.push({
                    enabled: true,
                    type: "javascript",
                    key: "",
                    value: "",
                    description: "Postman JS 脚本"
                });
            } else if (preset === 'script') {
                apiPreActionsList.value.push({
                    enabled: true,
                    type: "custom_script",
                    key: "",
                    value: "",
                    description: "Python 脚本"
                });
            }
            ElementPlus.ElMessage.success("已添加前置操作！");
        };

        const addPostActionRow = () => {
            apiPostActionsList.value.push({
                enabled: true,
                name: "验证响应状态",
                type: "assert_status_code",
                expression: "",
                operator: "equals",
                target_value: "200",
                description: ""
            });
        };

        const removePostActionRow = (idx) => {
            apiPostActionsList.value.splice(idx, 1);
        };

        const onPostActionTypeChange = (item) => {
            if (item.type === 'assert_status_code') {
                item.name = item.name || "HTTP 状态码等于 200";
                item.expression = "";
                item.operator = "equals";
                item.target_value = "200";
            } else if (item.type === 'assert_latency') {
                item.name = item.name || "响应耗时 < 1000ms";
                item.expression = "";
                item.operator = "less_than";
                item.target_value = "1000";
            } else if (item.type === 'assert_json_path') {
                item.name = item.name || "验证 JSON 字段值";
                item.expression = item.expression || "code";
                item.operator = "equals";
                item.target_value = "200";
            } else if (item.type === 'assert_header') {
                item.name = item.name || "响应头校验";
                item.expression = item.expression || "content-type";
                item.operator = "contains";
                item.target_value = "application/json";
            } else if (item.type === 'assert_body_contains') {
                item.name = item.name || "响应内容包含关键字";
                item.expression = "";
                item.operator = "contains";
                item.target_value = "OK";
            } else if (item.type === 'extract_variable') {
                item.name = item.name || "提取响应数据";
                item.expression = item.expression || "data.id";
                item.operator = "extract";
                item.target_value = "targetId";
            } else if (item.type === 'javascript') {
                item.name = item.name || "Postman JS 脚本断言";
                item.expression = "";
                item.value = item.value || "";
                item.operator = "pm.test";
                item.target_value = "";
            }
        };

        const applyPostActionPreset = (preset) => {
            if (preset === 'status_200') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "状态码等于 200",
                    type: "assert_status_code",
                    expression: "",
                    operator: "equals",
                    target_value: "200"
                });
            } else if (preset === 'status_2xx') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "状态码在 2xx 成功范围",
                    type: "assert_status_code",
                    expression: "",
                    operator: "in_2xx",
                    target_value: ""
                });
            } else if (preset === 'latency_1000') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "响应耗时 < 1000ms",
                    type: "assert_latency",
                    expression: "",
                    operator: "less_than",
                    target_value: "1000"
                });
            } else if (preset === 'json_code') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "JSON code 等于 200",
                    type: "assert_json_path",
                    expression: "code",
                    operator: "equals",
                    target_value: "200"
                });
            } else if (preset === 'contains_ok') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "响应文本包含 OK",
                    type: "assert_body_contains",
                    expression: "",
                    operator: "contains",
                    target_value: "OK"
                });
            } else if (preset === 'extract_var') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "提取响应 Token",
                    type: "extract_variable",
                    expression: "data.token",
                    operator: "extract",
                    target_value: "authToken"
                });
            } else if (preset === 'js_test') {
                apiPostActionsList.value.push({
                    enabled: true,
                    name: "Postman JS 脚本测试断言",
                    type: "javascript",
                    value: "",
                    operator: "pm.test",
                    target_value: "",
                    description: "Postman Tests JS 断言脚本"
                });
            }
            ElementPlus.ElMessage.success("已添加后置断言预设！");
        };

        const openEditApiDialog = (row) => {
            editingApiId.value = row.id;

            let initialBaseUrl = row.base_url || "";
            if (!initialBaseUrl && row.machine_id) {
                const m = machineList.value.find(item => item.id === row.machine_id);
                if (m) {
                    if (m.base_url && m.base_url.trim()) {
                        initialBaseUrl = m.base_url.trim();
                    } else {
                        const scheme = m.port === 443 ? "https" : "http";
                        initialBaseUrl = (m.port === 80 || m.port === 443) ? `${scheme}://${m.host}` : `${scheme}://${m.host}:${m.port}`;
                    }
                }
            }

            if (row.machine_id) {
                fetchMachineEnvironment(row.machine_id);
            }

            apiForm.value = {
                machine_id: row.machine_id,
                name: row.name || "",
                base_url: initialBaseUrl,
                http_path: row.http_path || "",
                http_method: row.http_method || "GET",
                cron_interval_minutes: row.cron_interval_minutes || 5,
                email_input: (row.email_receivers && Array.isArray(row.email_receivers))
                    ? row.email_receivers.join(", ")
                    : (row.email_receivers || ""),
                schema_text: row.expected_schema ? JSON.stringify(row.expected_schema, null, 2) : "{}"
            };
            apiSampleJson.value = "";
            apiActiveTab.value = "params";
            apiResponseTab.value = "body";

            // 恢复 Params
            if (row.http_params && Array.isArray(row.http_params) && row.http_params.length > 0) {
                apiParamsList.value = row.http_params.map(p => ({
                    enabled: p.enabled !== false,
                    key: p.key || "",
                    value: p.value || "",
                    description: p.description || ""
                }));
            } else if (row.http_path && row.http_path.includes("?")) {
                const searchParams = new URLSearchParams(row.http_path.split("?")[1]);
                const plist = [];
                searchParams.forEach((val, key) => {
                    plist.push({ enabled: true, key, value: val, description: "" });
                });
                apiParamsList.value = plist.length > 0 ? plist : [{ enabled: true, key: "", value: "", description: "" }];
            } else {
                apiParamsList.value = [{ enabled: true, key: "", value: "", description: "" }];
            }

            // 恢复 Headers (分离系统默认请求头与用户自定义请求头)
            systemDefaultHeaders.value = createDefaultHeaders();
            showDefaultHeaders.value = false;
            const customHeaders = [];
            if (row.http_headers && Array.isArray(row.http_headers) && row.http_headers.length > 0) {
                row.http_headers.forEach(h => {
                    const k = (h.key || "").trim().toLowerCase();
                    const sysMatch = systemDefaultHeaders.value.find(s => s.key.toLowerCase() === k);
                    if (sysMatch && !sysMatch.isCalculated) {
                        sysMatch.enabled = h.enabled !== false;
                        if (h.value !== undefined && h.value !== null) {
                            sysMatch.value = h.value;
                        }
                    } else {
                        customHeaders.push({
                            enabled: h.enabled !== false,
                            key: h.key || "",
                            value: h.value || "",
                            description: h.description || ""
                        });
                    }
                });
            }
            apiHeadersList.value = customHeaders.length > 0 ? customHeaders : [
                { enabled: true, key: "", value: "", description: "" }
            ];

            apiBodyType.value = row.http_body_type || "none";
            apiBodyText.value = row.http_body || "";
            apiAuthType.value = row.auth_type || "none";
            apiAuthConfig.value = Object.assign({
                token: "",
                username: "",
                password: "",
                header_key: "Authorization",
                header_value: ""
            }, row.auth_config || {});

            // 恢复 Pre-request Actions
            if (row.pre_actions && Array.isArray(row.pre_actions)) {
                apiPreActionsList.value = row.pre_actions.map(a => ({
                    enabled: a.enabled !== false,
                    type: a.type || "set_variable",
                    key: a.key || "",
                    value: a.value || "",
                    description: a.description || ""
                }));
            } else {
                apiPreActionsList.value = [];
            }

            // 恢复 Post-response Actions
            if (row.post_actions && Array.isArray(row.post_actions)) {
                apiPostActionsList.value = row.post_actions.map(a => ({
                    enabled: a.enabled !== false,
                    name: a.name || "",
                    type: a.type || "assert_status_code",
                    expression: a.expression || "",
                    operator: a.operator || "equals",
                    target_value: a.target_value !== undefined ? a.target_value : "",
                    description: a.description || ""
                }));
            } else {
                apiPostActionsList.value = [
                    { enabled: true, name: "HTTP 状态码等于 200", type: "assert_status_code", expression: "", operator: "equals", target_value: "200", description: "" }
                ];
            }

            apiTestResult.value = null;
            apiDialogVisible.value = true;
        };

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
                ElementPlus.ElMessage.warning("请先选择目标宿主机器节点！");
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
                    ElementPlus.ElMessage.success(`成功解析 Postman 集合，识别出 ${res.data.data.apis.length} 个接口！`);
                }
            } catch (err) {
                ElementPlus.ElMessage.error("Postman 文件解析失败: " + (err.response?.data?.detail || err.message));
            } finally {
                postmanImportLoading.value = false;
            }
        };

        const handlePostmanTextParse = async () => {
            if (!postmanRawJsonText.value.trim()) {
                ElementPlus.ElMessage.warning("请先粘贴 Postman 导出的 JSON 文本！");
                return;
            }
            if (!postmanImportMachineId.value) {
                ElementPlus.ElMessage.warning("请先选择目标宿主机器节点！");
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
                    ElementPlus.ElMessage.success(`成功解析 JSON 文本，识别出 ${res.data.data.apis.length} 个接口！`);
                }
            } catch (err) {
                ElementPlus.ElMessage.error("JSON 解析失败: " + (err.response?.data?.detail || err.message));
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
                ElementPlus.ElMessage.warning("请选择目标宿主机器节点！");
                return;
            }
            if (postmanSelectedApis.value.length === 0) {
                ElementPlus.ElMessage.warning("请至少勾选 1 个需要导入的接口！");
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
                    ElementPlus.ElMessage.success(`导入成功！共导入 ${res.data.result.total_imported} 个接口！`);
                    await fetchData();
                }
            } catch (err) {
                ElementPlus.ElMessage.error("导入提交失败: " + (err.response?.data?.detail || err.message));
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

        const handleInferApiSchema = async () => {
            if (!apiSampleJson.value.trim()) {
                ElementPlus.ElMessage.warning("请先粘贴真实的响应 JSON 样本");
                return;
            }
            apiInferring.value = true;
            try {
                const parsed = JSON.parse(apiSampleJson.value.trim());
                const res = await axios.post("/api/tools/infer-schema", {
                    sample_json: parsed,
                    strict_mode: false
                });
                const schemaObj = (res.data && res.data.schema) ? res.data.schema : res.data;
                apiForm.value.schema_text = JSON.stringify(schemaObj, null, 2);
                ElementPlus.ElMessage.success("成功自动推导生成 Draft-7 契约规则！");
            } catch (err) {
                ElementPlus.ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
            } finally {
                apiInferring.value = false;
            }
        };

        const handleTestRunApi = async () => {
            if (!apiForm.value.machine_id) {
                ElementPlus.ElMessage.warning("请先选择宿主机器节点！");
                return;
            }
            if (!apiForm.value.http_path || !apiForm.value.http_path.trim()) {
                ElementPlus.ElMessage.warning("请输入请求相对路径！");
                return;
            }
            let parsedSchema = null;
            if (apiForm.value.schema_text && apiForm.value.schema_text.trim()) {
                try {
                    parsedSchema = JSON.parse(apiForm.value.schema_text);
                } catch (e) {
                    // 仅提示不阻断
                }
            }

            apiTestRunning.value = true;
            try {
                const testPayload = {
                    machine_id: apiForm.value.machine_id,
                    base_url: apiForm.value.base_url ? apiForm.value.base_url.trim() : null,
                    http_method: apiForm.value.http_method,
                    http_path: apiForm.value.http_path.trim(),
                    http_params: apiParamsList.value.filter(p => p.enabled && p.key && p.key.trim()),
                    http_headers: getEffectiveHeaders(),
                    http_body_type: apiBodyType.value,
                    http_body: apiBodyType.value !== "none" ? apiBodyText.value : null,
                    auth_type: apiAuthType.value,
                    auth_config: apiAuthType.value !== "none" ? apiAuthConfig.value : null,
                    expected_schema: parsedSchema,
                    pre_actions: apiPreActionsList.value.filter(a => a.enabled),
                    post_actions: apiPostActionsList.value.filter(a => a.enabled)
                };
                const res = await axios.post("/api/apis/test-run", testPayload);
                apiTestResult.value = res.data;

                // 同步更新宿主机器所属环境的环境变量池
                if (res.data.environment) {
                    currentMachineEnvironment.value.environment_id = res.data.environment.id;
                    currentMachineEnvironment.value.name = res.data.environment.name || "默认环境";
                    currentMachineEnvironment.value.variables = res.data.environment.variables || {};
                    if (res.data.environment.updated_variables && Object.keys(res.data.environment.updated_variables).length > 0) {
                        const updatedCount = Object.keys(res.data.environment.updated_variables).length;
                        ElementPlus.ElNotification({
                            title: "环境变量已同步",
                            message: `已自动将 ${updatedCount} 个更新变量持久化保存至环境【${res.data.environment.name}】变量池！`,
                            type: "success",
                            duration: 4000
                        });
                    }
                }

                if (res.data.assertions_summary && res.data.assertions_summary.total > 0 && !res.data.assertions_summary.all_passed) {
                    apiResponseTab.value = "assertions";
                    ElementPlus.ElMessage.warning(`调试完成: 状态码 ${res.data.status_code || '异常'}，但有 ${res.data.assertions_summary.total - res.data.assertions_summary.passed_count} 项后置断言未通过`);
                } else if (res.data.status_code >= 200 && res.data.status_code < 300) {
                    ElementPlus.ElMessage.success(`调试请求完成 [${res.data.status_code} OK] (${res.data.latency_ms}ms)`);
                } else {
                    ElementPlus.ElMessage.warning(`响应状态码: ${res.data.status_code || '异常'} (${res.data.latency_ms || 0}ms)`);
                }
            } catch (err) {
                apiTestResult.value = {
                    status_code: 0,
                    latency_ms: 0,
                    schema_matched: false,
                    schema_error: err.response?.data?.detail || err.message,
                    response_data: { error: err.response?.data?.detail || err.message },
                    response_headers: {},
                    assertions_result: [],
                    assertions_summary: { all_passed: false, total: 0, passed_count: 0 },
                    resolved_url: ""
                };
                ElementPlus.ElMessage.error("请求调试异常: " + (err.response?.data?.detail || err.message));
            } finally {
                apiTestRunning.value = false;
            }
        };

        const inferSchemaFromTestResult = async () => {
            if (!apiTestResult.value || !apiTestResult.value.response_data) {
                ElementPlus.ElMessage.warning("当前没有调试响应数据可供推导");
                return;
            }
            apiInferring.value = true;
            try {
                const res = await axios.post("/api/tools/infer-schema", {
                    sample_json: apiTestResult.value.response_data,
                    strict_mode: false
                });
                const schemaObj = (res.data && res.data.schema) ? res.data.schema : res.data;
                apiForm.value.schema_text = JSON.stringify(schemaObj, null, 2);
                apiActiveTab.value = "schema";
                ElementPlus.ElMessage.success("已从当前实际响应数据一键推导生成 Draft-7 Schema 契约！");
            } catch (err) {
                ElementPlus.ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
            } finally {
                apiInferring.value = false;
            }
        };

        const submitApiForm = async () => {
            if (!apiForm.value.machine_id) {
                ElementPlus.ElMessage.warning("请选择归属的机器节点！");
                return;
            }
            if (!apiForm.value.name || !apiForm.value.name.trim()) {
                ElementPlus.ElMessage.warning("请输入接口名称！");
                return;
            }
            if (!apiForm.value.http_path || !apiForm.value.http_path.trim()) {
                ElementPlus.ElMessage.warning("请输入接口相对路径！");
                return;
            }
            let parsedSchema = {};
            if (apiForm.value.schema_text && apiForm.value.schema_text.trim()) {
                try {
                    parsedSchema = JSON.parse(apiForm.value.schema_text);
                } catch (e) {
                    ElementPlus.ElMessage.error("Schema 规则必须是合法的 JSON 格式！");
                    return;
                }
            }

            const receivers = apiForm.value.email_input
                ? apiForm.value.email_input.split(/[,;，；\s]+/).filter(Boolean)
                : [];

            const payload = {
                machine_id: apiForm.value.machine_id,
                name: apiForm.value.name.trim(),
                base_url: apiForm.value.base_url ? apiForm.value.base_url.trim() : null,
                http_path: apiForm.value.http_path.trim(),
                http_method: apiForm.value.http_method,
                expected_schema: parsedSchema,
                cron_interval_minutes: apiForm.value.cron_interval_minutes || 5,
                is_active: true,
                email_receivers: receivers,
                http_params: apiParamsList.value.filter(p => p.key && p.key.trim() !== ""),
                http_headers: getEffectiveHeaders(),
                http_body_type: apiBodyType.value,
                http_body: apiBodyType.value !== "none" ? apiBodyText.value : null,
                auth_type: apiAuthType.value,
                auth_config: apiAuthType.value !== "none" ? apiAuthConfig.value : null,
                pre_actions: apiPreActionsList.value.filter(a => a.key || a.value || a.type === 'custom_script' || a.type === 'javascript'),
                post_actions: apiPostActionsList.value.filter(a => a.type)
            };

            apiSubmitting.value = true;
            try {
                if (editingApiId.value) {
                    await axios.put(`/api/apis/${editingApiId.value}`, payload);
                    ElementPlus.ElMessage.success(`接口 [${payload.name}] 配置已更新！`);
                } else {
                    await axios.post("/api/apis", payload);
                    ElementPlus.ElMessage.success(`接口 [${payload.name}] 已添加并接入定时调度！`);
                }
                apiDialogVisible.value = false;
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error((editingApiId.value ? "更新失败: " : "创建失败: ") + (err.response?.data?.detail || err.message));
            } finally {
                apiSubmitting.value = false;
            }
        };

        // URL 与 Query Params 双向同步监听
        watch(apiParamsList, () => {
            syncParamsToPath();
        }, { deep: true });

        watch(() => apiForm.value.http_path, (newVal) => {
            syncPathToParams(newVal);
        });

        const handleDeleteApi = async (apiId, apiName) => {
            try {
                await axios.delete(`/api/apis/${apiId}`);
                ElementPlus.ElMessage.success(`接口 [${apiName}] 已删除`);
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("删除失败: " + (err.response?.data?.detail || err.message));
            }
        };

        const handleTriggerApi = async (row) => {
            triggeringApiId.value = row.id;
            try {
                const res = await axios.post(`/api/apis/${row.id}/trigger`);
                const data = res.data;
                if (data.circuit_broken) {
                    ElementPlus.ElNotification({
                        title: `熔断挂起 [${row.name}]`,
                        message: "宿主机器处于离线状态，接口拨测已熔断并抑制告警！",
                        type: "warning"
                    });
                } else if (data.http_status_code === 200 && data.schema_matched) {
                    ElementPlus.ElNotification({
                        title: `接口拨测通过 [${row.name}]`,
                        message: `HTTP 200 (${data.http_latency_ms}ms) | Schema 契约校验完全匹配`,
                        type: "success"
                    });
                } else {
                    ElementPlus.ElNotification({
                        title: `接口探测异常 [${row.name}]`,
                        message: `状态码: ${data.http_status_code || '异常'} | Schema匹配: ${data.schema_matched ? '是' : '未通过'}`,
                        type: "error",
                        duration: 6000
                    });
                }
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error("探测失败: " + (err.response?.data?.detail || err.message));
            } finally {
                triggeringApiId.value = null;
            }
        };

        const openApiMetricsDrawer = async (row) => {
            const host = row.machine_host || "";
            const port = row.machine_port || 80;
            const fullUrl = row.full_url || ((row.base_url || ('http://' + host + ':' + port)) + (row.http_path || ''));

            activeTarget.value = {
                id: row.id,
                name: row.name,
                group_name: row.environment_name || "生产环境",
                host: host,
                port: port,
                http_path: row.http_path,
                http_method: row.http_method || "GET",
                machine_name: row.machine_name || `${host}:${port}`,
                machine_status: row.machine_status,
                full_url: fullUrl,
                current_status: row.current_status,
                cron_interval_minutes: row.cron_interval_minutes || 5,
                last_http_latency_ms: row.last_http_latency_ms
            };
            drawerVisible.value = true;
            loadingHistory.value = true;
            historyList.value = [];
            try {
                const [historyRes, metricsRes] = await Promise.all([
                    axios.get(`/api/apis/${row.id}/history?limit=50`),
                    axios.get(`/api/apis/${row.id}/metrics`)
                ]);
                // 严格只展示当前接口自身专属探测历史，杜绝跨表/跨接口脏数据污染
                historyList.value = Array.isArray(historyRes.data) ? historyRes.data : [];
                loadingHistory.value = false;
                await nextTick();
                setTimeout(() => {
                    renderChart(metricsRes.data?.points || []);
                }, 150);
            } catch (err) {
                console.error("加载接口时序与历史异常:", err);
                ElementPlus.ElMessage.error("加载接口专属时序历史失败: " + (err.response?.data?.detail || err.message));
                historyList.value = [];
                loadingHistory.value = false;
                await nextTick();
                setTimeout(() => {
                    renderChart([]);
                }, 150);
            }
        };

        const openCreateDialog = () => {
            editingTargetId.value = null;
            form.value = {
                name: "",
                group_name: selectedGroup.value !== "ALL" ? selectedGroup.value : "生产环境",
                host: "",
                port: 80,
                http_path: "",
                http_method: "GET",
                cron_interval_minutes: 5,
                email_input: "admin@company.com",
                schema_text: JSON.stringify({
                    type: "object",
                    required: ["headers", "origin", "url"],
                    properties: {
                        origin: { type: "string" },
                        url: { type: "string" },
                        headers: { type: "object" }
                    }
                }, null, 2)
            };
            sampleJsonText.value = "";
            createDialogVisible.value = true;
        };

        const openEditDialog = (row) => {
            editingTargetId.value = row.id;
            form.value = {
                name: row.name || "",
                group_name: row.group_name || "生产环境",
                host: row.host || "",
                port: row.port || 80,
                http_path: row.http_path || "",
                http_method: row.http_method || "GET",
                cron_interval_minutes: row.cron_interval_minutes || 5,
                email_input: (row.email_receivers && Array.isArray(row.email_receivers))
                    ? row.email_receivers.join(", ")
                    : (row.email_receivers || ""),
                schema_text: row.expected_schema ? JSON.stringify(row.expected_schema, null, 2) : "{}"
            };
            sampleJsonText.value = "";
            createDialogVisible.value = true;
        };

        const handleInferSchema = async () => {
            if (!sampleJsonText.value.trim()) {
                ElementPlus.ElMessage.warning("请先粘贴真实的响应 JSON 样本");
                return;
            }
            let parsed = null;
            try {
                parsed = JSON.parse(sampleJsonText.value);
            } catch (e) {
                ElementPlus.ElMessage.error("JSON 格式错误: " + e.message);
                return;
            }

            inferring.value = true;
            try {
                const res = await axios.post("/api/tools/infer-schema", {
                    sample_json: parsed,
                    strict_mode: true
                });
                const schemaObj = (res.data && res.data.schema) ? res.data.schema : res.data;
                form.value.schema_text = JSON.stringify(schemaObj, null, 2);
                ElementPlus.ElMessage.success("已成功转换为 Draft-7 Schema 规则模板！");
            } catch (err) {
                ElementPlus.ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
            } finally {
                inferring.value = false;
            }
        };

        const handleLabInfer = async () => {
            if (!labJsonInput.value.trim()) {
                ElementPlus.ElMessage.warning("请先输入合法的 JSON 样本");
                return;
            }
            let parsed = null;
            try {
                parsed = JSON.parse(labJsonInput.value);
            } catch (e) {
                ElementPlus.ElMessage.error("JSON 格式校验失败: " + e.message);
                return;
            }

            labInferring.value = true;
            try {
                const res = await axios.post("/api/tools/infer-schema", {
                    sample_json: parsed,
                    strict_mode: labStrictMode.value
                });
                const schemaObj = (res.data && res.data.schema) ? res.data.schema : res.data;
                labSchemaOutput.value = JSON.stringify(schemaObj, null, 2);
                ElementPlus.ElMessage.success("实验室 Schema 结构推导完毕！");
            } catch (err) {
                ElementPlus.ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
            } finally {
                labInferring.value = false;
            }
        };

        const copyLabSchema = () => {
            if (!labSchemaOutput.value) return;
            navigator.clipboard.writeText(labSchemaOutput.value).then(() => {
                ElementPlus.ElMessage.success("已复制 Schema 到剪贴板！");
            });
        };

        const copySchemaToValidate = () => {
            if (!labSchemaOutput.value) return;
            labValidateSchemaText.value = labSchemaOutput.value;
            labValidateJsonText.value = labJsonInput.value;
            labActiveTab.value = "validate";
            labValidationResult.value = null;
            ElementPlus.ElMessage.success("已将生成的 Schema 及样本数据载入破坏性变更仿真！");
        };

        const loadValidateSample = (type) => {
            labValidationResult.value = null;
            if (type === "normal") {
                labValidateJsonText.value = JSON.stringify({
                    code: 200,
                    status: "success",
                    user: {
                        id: 10086,
                        name: "Developer",
                        roles: ["admin", "tester"]
                    }
                }, null, 2);
            } else if (type === "breaking") {
                labValidateJsonText.value = JSON.stringify({
                    code: "200",
                    status: "success",
                    user: {
                        id: "10086",
                        name: 12345
                    }
                }, null, 2);
            }
        };

        const handleLabValidate = async () => {
            if (!labValidateSchemaText.value.trim()) {
                ElementPlus.ElMessage.warning("请先输入或从推导结果导入预期 Schema 契约规则！");
                return;
            }
            if (!labValidateJsonText.value.trim()) {
                ElementPlus.ElMessage.warning("请先输入待测试的实际响应 JSON 数据！");
                return;
            }
            let parsedSchema, parsedData;
            try {
                parsedSchema = JSON.parse(labValidateSchemaText.value);
            } catch (e) {
                ElementPlus.ElMessage.error("预期 Schema 格式错误: " + e.message);
                return;
            }
            try {
                parsedData = JSON.parse(labValidateJsonText.value);
            } catch (e) {
                ElementPlus.ElMessage.error("待测 JSON 格式错误: " + e.message);
                return;
            }

            labValidating.value = true;
            try {
                const res = await axios.post("/api/tools/validate-schema", {
                    sample_json: parsedData,
                    expected_schema: parsedSchema
                });
                labValidationResult.value = res.data;
                if (res.data.valid) {
                    ElementPlus.ElMessage.success("契约校验完全通过！未发现破坏性变更");
                } else {
                    ElementPlus.ElMessage.warning(`捕获到 ${res.data.error_count} 项破坏性结构变更！`);
                }
            } catch (err) {
                ElementPlus.ElMessage.error("校验请求失败: " + (err.response?.data?.detail || err.message));
            } finally {
                labValidating.value = false;
            }
        };

        const submitCreateTarget = async () => {
            if (!form.value.name || !form.value.host || !form.value.port) {
                ElementPlus.ElMessage.warning("请完整填写环境、名称、IP/域名与端口");
                return;
            }
            let parsedSchema = null;
            try {
                parsedSchema = JSON.parse(form.value.schema_text);
            } catch (e) {
                ElementPlus.ElMessage.error("Schema 规则必须是合法的 JSON: " + e.message);
                return;
            }

            const receivers = form.value.email_input
                ? form.value.email_input.split(/[,;，；\s]+/).filter(Boolean)
                : [];

            const payload = {
                name: form.value.name,
                group_name: form.value.group_name || "生产环境",
                host: form.value.host,
                port: form.value.port,
                http_path: form.value.http_path,
                http_method: form.value.http_method,
                cron_interval_minutes: form.value.cron_interval_minutes,
                expected_schema: parsedSchema,
                email_receivers: receivers,
                retry_threshold: 3,
                silence_minutes: 30,
                is_active: true
            };

            submitting.value = true;
            try {
                if (editingTargetId.value) {
                    await axios.put(`/api/targets/${editingTargetId.value}`, payload);
                    ElementPlus.ElMessage.success("监控目标已更新！");
                } else {
                    await axios.post("/api/targets", payload);
                    ElementPlus.ElMessage.success("监控目标创建成功，后台定时调度引擎已接管！");
                }
                createDialogVisible.value = false;
                await fetchData();
            } catch (err) {
                ElementPlus.ElMessage.error((editingTargetId.value ? "更新失败: " : "创建失败: ") + (err.response?.data?.detail || err.message));
            } finally {
                submitting.value = false;
            }
        };

        const openMetricsDrawer = async (target) => {
            activeTarget.value = target;
            drawerVisible.value = true;
            loadingHistory.value = true;
            historyList.value = [];

            try {
                const [historyRes, metricsRes] = await Promise.all([
                    axios.get(`/api/targets/${target.id}/history?limit=50`),
                    axios.get(`/api/targets/${target.id}/metrics?hours=24`)
                ]);
                let hist = Array.isArray(historyRes.data) ? historyRes.data : [];
                if (hist.length === 0) {
                    try {
                        const apiHistRes = await axios.get(`/api/apis/${target.id}/history?limit=50`);
                        if (Array.isArray(apiHistRes.data) && apiHistRes.data.length > 0) {
                            hist = apiHistRes.data;
                        }
                    } catch (e) {}
                }
                historyList.value = hist;
                loadingHistory.value = false;

                await nextTick();
                setTimeout(() => {
                    renderChart(Array.isArray(metricsRes.data) ? metricsRes.data : []);
                }, 150);
            } catch (err) {
                console.error("加载时序报表异常:", err);
                try {
                    const [apiHistRes, apiMetRes] = await Promise.all([
                        axios.get(`/api/apis/${target.id}/history?limit=50`),
                        axios.get(`/api/apis/${target.id}/metrics`)
                    ]);
                    historyList.value = Array.isArray(apiHistRes.data) ? apiHistRes.data : [];
                    renderChart(apiMetRes.data.points || []);
                } catch (fallbackErr) {
                    ElementPlus.ElMessage.error("加载时序报表失败: " + (err.response?.data?.detail || err.message));
                }
                loadingHistory.value = false;
            }
        };

        const renderChart = (points) => {
            const dom = document.getElementById("chartContainer");
            if (!dom) return;

            if (!Array.isArray(points)) {
                points = [];
            }

            if (echartsInstance) {
                echartsInstance.dispose();
            }
            echartsInstance = echarts.init(dom);

            const times = points.map(p => p.time);
            const tcpData = points.map(p => (p.tcp_ms !== undefined && p.tcp_ms !== null ? p.tcp_ms : null));
            const httpData = points.map(p => (p.http_ms !== undefined && p.http_ms !== null ? p.http_ms : null));

            const markPoints = points
                .filter(p => !p.is_healthy && p.time)
                .map(p => ({
                    name: "异常破坏点",
                    coord: [p.time, p.http_ms || p.tcp_ms || 10],
                    value: "FAIL",
                    itemStyle: { color: "#dc2626" }
                }));

            const option = {
                backgroundColor: "transparent",
                tooltip: {
                    trigger: "axis",
                    axisPointer: { type: "cross", crossStyle: { color: "#94a3b8" } },
                    backgroundColor: "rgba(255, 255, 255, 0.96)",
                    borderColor: "#dbe5f0",
                    borderWidth: 1,
                    textStyle: { color: "#0f172a" },
                    extraCssText: "box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08); border-radius: 6px;"
                },
                legend: {
                    data: ["TCP 耗时 (ms)", "HTTP 响应 (ms)"],
                    textStyle: { color: "#475569" },
                    top: 4
                },
                grid: {
                    left: "3%",
                    right: "4%",
                    bottom: "3%",
                    containLabel: true
                },
                xAxis: {
                    type: "category",
                    data: times.length ? times : ["暂无时序数据"],
                    axisLine: { lineStyle: { color: "#cbd5e1" } },
                    axisLabel: { color: "#64748b", fontSize: 11 }
                },
                yAxis: {
                    type: "value",
                    name: "延迟 (ms)",
                    nameTextStyle: { color: "#64748b" },
                    axisLine: { lineStyle: { color: "#cbd5e1" } },
                    splitLine: { lineStyle: { color: "#e2eafd", type: "dashed" } },
                    axisLabel: { color: "#64748b", fontSize: 11 }
                },
                series: [
                    {
                        name: "TCP 耗时 (ms)",
                        type: "line",
                        smooth: true,
                        data: tcpData,
                        itemStyle: { color: "#0284c7" },
                        lineStyle: { width: 1.8 }
                    },
                    {
                        name: "HTTP 响应 (ms)",
                        type: "line",
                        smooth: true,
                        data: httpData,
                        itemStyle: { color: "#2563eb" },
                        lineStyle: { width: 2 },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: "rgba(37, 99, 235, 0.15)" },
                                { offset: 1, color: "rgba(37, 99, 235, 0.01)" }
                            ])
                        },
                        markPoint: { data: markPoints }
                    }
                ]
            };
            echartsInstance.setOption(option);
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

        onMounted(() => {
            fetchData();
            setInterval(fetchData, 15000);
            window.addEventListener("resize", () => {
                if (echartsInstance) echartsInstance.resize();
            });
        });

        const setupResult = {
            loading,
            targets,
            groupList,
            selectedGroup,
            currentNav,
            activeMenuKey,
            handleMenuSelect,
            navTitle,
            downTargets,
            incidentSearchQuery,
            filteredDownTargets,
            filteredTargets,
            switchNav,
            filterBySidebarGroup,
            getGroupColor,
            getGroupTagType,
            getStatusBadgeClass,
            getStatusIcon,
            summary,
            triggeringId,
            createDialogVisible,
            submitting,
            inferring,
            sampleJsonText,
            form,
            labActiveTab,
            labJsonInput,
            labStrictMode,
            labSchemaOutput,
            labInferring,
            handleLabInfer,
            copyLabSchema,
            copySchemaToValidate,
            labValidateSchemaText,
            labValidateJsonText,
            labValidating,
            labValidationResult,
            loadValidateSample,
            handleLabValidate,
            drawerVisible,
            activeTarget,
            loadingHistory,
            historyList,
            fetchData,
            lastRefreshTime,
            handleManualRefresh,
            handleTrigger,
            handleDelete,
            openCreateDialog,
            openEditDialog,
            editingTargetId,
            handleInferSchema,
            submitCreateTarget,
            openMetricsDrawer,
            formatTime,
            formatLatency,
            getLatencyBadgeClass,
            openDocs,
            // 环境管理导出
            environmentList,
            envDialogVisible,
            editingEnvId,
            envSubmitting,
            envSearchQuery,
            envForm,
            filteredEnvironments,
            openCreateEnvDialog,
            openEditEnvDialog,
            submitEnvForm,
            handleDeleteEnv,
            goToEnvTargets,
            goToEnvApis,
            goToEnvMachines,
            getEnvStatusBadgeClass,
            getEnvBorderTopColor,
            dashboardEnvironments,
            getEnvTargetCount,
            getEnvMachineCount,
            // 机器管理导出
            machineList,
            machineDialogVisible,
            editingMachineId,
            machineSubmitting,
            triggeringMachineId,
            machineSearchQuery,
            selectedMachineEnv,
            machineForm,
            onlineMachineCount,
            offlineMachineCount,
            avgTcpLatency,
            machineEnvTotalCount,
            machineEnvOnlineCount,
            machineEnvOfflineCount,
            machineEnvAvgTcpLatency,
            filteredMachines,
            openCreateMachineDialog,
            openEditMachineDialog,
            submitMachineForm,
            handleDeleteMachine,
            handleTriggerMachine,
            getMachineApiCount,
            goToMachineTargets,
            currentEnvMachines,
            // 接口管理导出
            apiList,
            apiDialogVisible,
            editingApiId,
            apiSubmitting,
            triggeringApiId,
            apiSearchQuery,
            selectedApiEnv,
            selectedApiMachine,
            selectedApiStatus,
            apiSampleJson,
            apiInferring,
            apiForm,
            healthyApiCount,
            issueApiCount,
            avgApiLatency,
            apiEnvTotalCount,
            apiEnvOnlineMachineCount,
            apiEnvHealthyCount,
            apiEnvIssueCount,
            apiEnvAvgLatency,
            currentEnvMachineOptions,
            filteredApis,
            openCreateApiDialog,
            openEditApiDialog,
            handleInferApiSchema,
            submitApiForm,
            handleDeleteApi,
            handleTriggerApi,
            openApiMetricsDrawer,
            // Postman 风格工作台导出
            apiActiveTab,
            apiResponseTab,
            apiParamsList,
            apiHeadersList,
            apiBodyType,
            apiBodyText,
            apiAuthType,
            apiAuthConfig,
            apiTestRunning,
            apiTestResult,
            selectedMachineDisplayName,
            selectedMachineBaseUrl,
            selectedMachineHost,
            resetBaseUrlToMachine,
            onPathInput,
            addParamRow,
            removeParamRow,
            addHeaderRow,
            removeHeaderRow,
            systemDefaultHeaders,
            showDefaultHeaders,
            isHeaderOverridden,
            activeDefaultHeadersCount,
            getEffectiveHeaders,
            insertMacroToBody,
            formatBodyJson,
            minifyBodyJson,
            clearBodyJson,
            formatSchemaJson,
            formatSampleJson,
            copyResponseBody,
            formatIfJson,
            copyText,
            handleTestRunApi,
            inferSchemaFromTestResult,
            // 前置操作与后置操作导出
            apiPreActionsList,
            apiPostActionsList,
            addPreActionRow,
            removePreActionRow,
            applyPreActionPreset,
            addPostActionRow,
            removePostActionRow,
            applyPostActionPreset,
            onPostActionTypeChange,
            // 宿主机器运行环境与环境变量管理导出
            currentMachineEnvironment,
            envVarsDialogVisible,
            envVariablesList,
            envVariablesSaving,
            fetchMachineEnvironment,
            openEnvDialog,
            addEnvVarRow,
            removeEnvVarRow,
            saveEnvVariables,
            copyEnvVarRef,
            getVarRef,
            // Postman 数据导入导出
            postmanImportDialogVisible,
            postmanImportMachine,
            postmanImportMachineId,
            postmanImportLoading,
            postmanPreviewData,
            postmanSelectedApis,
            postmanSyncEnvVars,
            postmanUpdateBaseUrl,
            postmanConflictPolicy,
            postmanCronInterval,
            postmanRawJsonText,
            postmanImportActiveTab,
            postmanImportSuccessResult,
            openPostmanImportForMachine,
            openGenericPostmanImport,
            onPostmanImportMachineChange,
            handlePostmanFileChange,
            handlePostmanTextParse,
            toggleSelectAllPostmanApis,
            isPostmanApiSelected,
            togglePostmanApiSelection,
            executeConfirmPostmanImport,
            resetPostmanImport,
            goToImportedApisView
        };

        // 调试与自动化测试全局挂载
        window.SchemaPulseApp = setupResult;

        return setupResult;
    }
});

app.use(ElementPlus);
window.app = app.mount("#app");
