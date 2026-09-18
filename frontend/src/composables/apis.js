import { ref, computed, watch, nextTick } from 'vue'
import { apiList, environmentList, fetchData, machineList } from './core'
import { activeTarget, drawerVisible, form, historyList, loadingHistory, renderChart } from './targets'
import { currentMachineEnvironment, fetchMachineEnvironment } from './machines'
import { ElMessage, ElNotification } from 'element-plus'
import axios from 'axios'

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
    is_active: true,
    email_input: "admin@company.com",
    schema_text: ""
});

const apiIntervalValue = ref(5);

const apiIntervalUnit = ref("minutes"); // 'minutes' | 'hours' | 'days'

const setQuickInterval = (val, unit) => {
    apiIntervalValue.value = val;
    apiIntervalUnit.value = unit;
};

const formatIntervalDisplay = (minutes, isActive) => {
    if (isActive === false) return "已关闭";
    const m = parseInt(minutes, 10) || 5;
    if (m >= 1440 && m % 1440 === 0) {
        return `${m / 1440}天`;
    }
    if (m >= 60 && m % 60 === 0) {
        return `${m / 60}小时`;
    }
    return `${m}m`;
};

const getIntervalTooltip = (minutes, isActive) => {
    if (isActive === false) return "该接口已关闭自动探测（仅支持手动拨测或链式调用触发），点击可快速启用";
    const m = parseInt(minutes, 10) || 5;
    let human = `${m} 分钟`;
    if (m >= 1440) {
        const days = (m / 1440).toFixed(1).replace(/\.0$/, "");
        human = `${days} 天 (${m} 分钟)`;
    } else if (m >= 60) {
        const hrs = (m / 60).toFixed(1).replace(/\.0$/, "");
        human = `${hrs} 小时 (${m} 分钟)`;
    }
    return `每 ${human} 自动探活一次，点击可快捷关闭`;
};

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
        // 仅将纯 Query 参数拼接到 URL 尾部，排除路径变量 (如 {tableId} 或 :tableId 或 标注为路径参数的项)
        const queryPairs = apiParamsList.value.filter(p => {
            if (!p.enabled || !p.key || !p.key.trim()) return false;
            const k = p.key.trim();
            const isPathVariable = basePath.includes(`{${k}}`) || basePath.includes(`:${k}`) || (p.description && p.description.includes("路径参数"));
            return !isPathVariable;
        });
        if (queryPairs.length === 0) {
            apiForm.value.http_path = basePath;
        } else {
            const q = queryPairs.map(p => `${encodeURIComponent(p.key.trim())}=${encodeURIComponent(p.value || "")}`).join("&");
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
        if (!newPath) return;
        const basePath = newPath.includes("?") ? newPath.split("?")[0] : newPath;
        const queryString = newPath.includes("?") ? newPath.split("?")[1] : "";
        
        // 保留原有的路径参数
        const pathVarParams = apiParamsList.value.filter(p => {
            if (!p.key) return false;
            const k = p.key.trim();
            return basePath.includes(`{${k}}`) || basePath.includes(`:${k}`) || (p.description && p.description.includes("路径参数"));
        });

        const queryParams = [];
        if (queryString) {
            const searchParams = new URLSearchParams(queryString);
            searchParams.forEach((val, key) => {
                queryParams.push({ enabled: true, key, value: val, description: "" });
            });
        }
        
        const merged = [...pathVarParams, ...queryParams];
        apiParamsList.value = merged.length > 0 ? merged : [{ enabled: true, key: "", value: "", description: "" }];
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
        ElMessage.warning("当前 Body 请求体为空，无需格式化");
        return;
    }
    try {
        apiBodyText.value = safeFormatJson(apiBodyText.value);
        ElMessage.success("Body JSON 格式化完成！");
    } catch (err) {
        ElMessage.error("JSON 格式错误: " + (err.message || "无法解析有效 JSON"));
    }
};

const minifyBodyJson = () => {
    if (!apiBodyText.value || !apiBodyText.value.trim()) {
        ElMessage.warning("当前 Body 请求体为空");
        return;
    }
    try {
        apiBodyText.value = safeMinifyJson(apiBodyText.value);
        ElMessage.success("Body JSON 已压缩为紧凑单行格式！");
    } catch (err) {
        ElMessage.error("JSON 格式错误: " + (err.message || "无法解析有效 JSON"));
    }
};

const clearBodyJson = () => {
    apiBodyText.value = "";
    ElMessage.info("已清空 Body 内容");
};

const formatSchemaJson = () => {
    if (!apiForm.value.schema_text || !apiForm.value.schema_text.trim()) {
        ElMessage.warning("当前 Schema 内容为空，无需格式化");
        return;
    }
    try {
        apiForm.value.schema_text = safeFormatJson(apiForm.value.schema_text);
        ElMessage.success("Schema 契约规则格式化完成！");
    } catch (err) {
        ElMessage.error("Schema 格式错误: " + (err.message || "无法解析有效 JSON"));
    }
};

const formatSampleJson = () => {
    if (!apiSampleJson.value || !apiSampleJson.value.trim()) {
        ElMessage.warning("样本 JSON 内容为空，无需格式化");
        return;
    }
    try {
        apiSampleJson.value = safeFormatJson(apiSampleJson.value);
        ElMessage.success("样本 JSON 格式化完成！");
    } catch (err) {
        ElMessage.error("样本 JSON 格式错误: " + (err.message || "无法解析有效 JSON"));
    }
};

const copyResponseBody = async () => {
    if (!apiTestResult.value || !apiTestResult.value.response_data) {
        ElMessage.warning("当前无有效响应数据可复制");
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
        ElMessage.success("响应 JSON 已成功复制到剪贴板！");
    } catch (err) {
        ElMessage.error("复制失败: " + err.message);
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
        ElMessage.success("已复制到剪贴板！");
    } catch (err) {
        ElMessage.error("复制失败: " + err.message);
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
        is_active: true,
        email_input: "admin@company.com",
        schema_text: ""
    };
    apiIntervalValue.value = 5;
    apiIntervalUnit.value = "minutes";
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
    ElMessage.success("已添加前置操作！");
};

const addPostActionRow = () => {
    apiPostActionsList.value.push({
        enabled: true,
        name: "验证响应状态",
        type: "assert_status_code",
        expression: "",
        operator: "equals",
        target_value: "200",
        value: "",
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
    ElMessage.success("已添加后置断言预设！");
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

    let initMins = parseInt(row.cron_interval_minutes, 10) || 5;
    if (initMins >= 1440 && initMins % 1440 === 0) {
        apiIntervalValue.value = initMins / 1440;
        apiIntervalUnit.value = "days";
    } else if (initMins >= 60 && initMins % 60 === 0) {
        apiIntervalValue.value = initMins / 60;
        apiIntervalUnit.value = "hours";
    } else {
        apiIntervalValue.value = initMins;
        apiIntervalUnit.value = "minutes";
    }

    isSyncingUrlParams = true;
    apiForm.value = {
        machine_id: row.machine_id,
        name: row.name || "",
        base_url: initialBaseUrl,
        http_path: row.http_path || "",
        http_method: row.http_method || "GET",
        cron_interval_minutes: initMins,
        is_active: row.is_active !== false,
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
    setTimeout(() => { isSyncingUrlParams = false; }, 200);

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
            value: a.value !== undefined ? a.value : (a.script || ""),
            description: a.description || ""
        }));
    } else {
        apiPostActionsList.value = [
            { enabled: true, name: "HTTP 状态码等于 200", type: "assert_status_code", expression: "", operator: "equals", target_value: "200", value: "", description: "" }
        ];
    }

    apiTestResult.value = null;
    apiDialogVisible.value = true;
};

const handleInferApiSchema = async () => {
    if (!apiSampleJson.value.trim()) {
        ElMessage.warning("请先粘贴真实的响应 JSON 样本");
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
        ElMessage.success("成功自动推导生成 Draft-7 契约规则！");
    } catch (err) {
        ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
    } finally {
        apiInferring.value = false;
    }
};

const handleTestRunApi = async () => {
    if (!apiForm.value.machine_id) {
        ElMessage.warning("请先选择宿主机器节点！");
        return;
    }
    if (!apiForm.value.http_path || !apiForm.value.http_path.trim()) {
        ElMessage.warning("请输入请求相对路径！");
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
                ElNotification({
                    title: "环境变量已同步",
                    message: `已自动将 ${updatedCount} 个更新变量持久化保存至环境【${res.data.environment.name}】变量池！`,
                    type: "success",
                    duration: 4000
                });
            }
        }

        // 提示脚本异常
        if (res.data.script_error) {
            ElNotification({
                title: "脚本执行异常警告",
                message: `前置/后置脚本执行报错: ${res.data.script_error}`,
                type: "warning",
                duration: 8000
            });
        }

        if (res.data.assertions_summary && res.data.assertions_summary.total > 0 && !res.data.assertions_summary.all_passed) {
            apiResponseTab.value = "assertions";
            ElMessage.warning(`调试完成: 状态码 ${res.data.status_code || '异常'}，但有 ${res.data.assertions_summary.total - res.data.assertions_summary.passed_count} 项后置断言未通过`);
        } else if (res.data.status_code >= 200 && res.data.status_code < 300) {
            ElMessage.success(`调试请求完成 [${res.data.status_code} OK] (${res.data.latency_ms}ms)`);
        } else {
            ElMessage.warning(`响应状态码: ${res.data.status_code || '异常'} (${res.data.latency_ms || 0}ms)`);
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
        ElMessage.error("请求调试异常: " + (err.response?.data?.detail || err.message));
    } finally {
        apiTestRunning.value = false;
    }
};

const inferSchemaFromTestResult = async () => {
    if (!apiTestResult.value || !apiTestResult.value.response_data) {
        ElMessage.warning("当前没有调试响应数据可供推导");
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
        ElMessage.success("已从当前实际响应数据一键推导生成 Draft-7 Schema 契约！");
    } catch (err) {
        ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
    } finally {
        apiInferring.value = false;
    }
};

const submitApiForm = async () => {
    if (!apiForm.value.machine_id) {
        ElMessage.warning("请选择归属的机器节点！");
        return;
    }
    if (!apiForm.value.name || !apiForm.value.name.trim()) {
        ElMessage.warning("请输入接口名称！");
        return;
    }
    if (!apiForm.value.http_path || !apiForm.value.http_path.trim()) {
        ElMessage.warning("请输入接口相对路径！");
        return;
    }
    let parsedSchema = {};
    if (apiForm.value.schema_text && apiForm.value.schema_text.trim()) {
        try {
            parsedSchema = JSON.parse(apiForm.value.schema_text);
        } catch (e) {
            ElMessage.error("Schema 规则必须是合法的 JSON 格式！");
            return;
        }
    }

    const receivers = apiForm.value.email_input
        ? apiForm.value.email_input.split(/[,;，；\s]+/).filter(Boolean)
        : [];

    // 智能根据所选单位计算最终存入后端的分钟数
    let finalIntervalMinutes = 5;
    if (apiIntervalUnit.value === "days") {
        finalIntervalMinutes = Math.max(1, Math.round(apiIntervalValue.value * 1440));
    } else if (apiIntervalUnit.value === "hours") {
        finalIntervalMinutes = Math.max(1, Math.round(apiIntervalValue.value * 60));
    } else {
        finalIntervalMinutes = Math.max(1, Math.round(apiIntervalValue.value || 5));
    }

    const payload = {
        machine_id: apiForm.value.machine_id,
        name: apiForm.value.name.trim(),
        base_url: apiForm.value.base_url ? apiForm.value.base_url.trim() : null,
        http_path: apiForm.value.http_path.trim(),
        http_method: apiForm.value.http_method,
        expected_schema: parsedSchema,
        cron_interval_minutes: finalIntervalMinutes,
        is_active: apiForm.value.is_active !== false,
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
            ElMessage.success(`接口 [${payload.name}] 配置已更新！`);
        } else {
            await axios.post("/api/apis", payload);
            ElMessage.success(`接口 [${payload.name}] 已添加并接入调度！`);
        }
        apiDialogVisible.value = false;
        await fetchData();
    } catch (err) {
        ElMessage.error((editingApiId.value ? "更新失败: " : "创建失败: ") + (err.response?.data?.detail || err.message));
    } finally {
        apiSubmitting.value = false;
    }
};

const toggleApiActive = async (row) => {
    try {
        const res = await axios.post(`/api/apis/${row.id}/toggle-active`);
        row.is_active = res.data.is_active;
        if (row.is_active) {
            ElMessage.success(`接口 [${row.name}] 已启用定时自动探测 (${formatIntervalDisplay(row.cron_interval_minutes, true)})！`);
        } else {
            ElMessage.info(`接口 [${row.name}] 已关闭自动探测 (仅支持手动拨测/链式调用)！`);
        }
    } catch (err) {
        ElMessage.error("切换状态失败: " + (err.response?.data?.detail || err.message));
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
        ElMessage.success(`接口 [${apiName}] 已删除`);
        await fetchData();
    } catch (err) {
        ElMessage.error("删除失败: " + (err.response?.data?.detail || err.message));
    }
};

const handleTriggerApi = async (row) => {
    triggeringApiId.value = row.id;
    try {
        const res = await axios.post(`/api/apis/${row.id}/trigger`);
        const data = res.data;
        if (data.circuit_broken) {
            ElNotification({
                title: `熔断挂起 [${row.name}]`,
                message: "宿主机器处于离线状态，接口拨测已熔断并抑制告警！",
                type: "warning"
            });
        } else if (data.http_status_code === 200 && data.is_healthy) {
            ElNotification({
                title: `接口拨测通过 [${row.name}]`,
                message: `HTTP 200 (${data.http_latency_ms}ms) | Schema 契约校验完全匹配`,
                type: "success"
            });
        } else if (data.http_status_code === 200 && data.is_healthy && data.schema_configured === false) {
            ElNotification({
                title: `接口拨测通过 (未配置契约) [${row.name}]`,
                message: `HTTP 200 (${data.http_latency_ms}ms) | 未配置 Schema 契约，可在编辑弹窗中从响应推导`,
                type: "success"
            });
        } else {
            ElNotification({
                title: `接口探测异常 [${row.name}]`,
                message: `状态码: ${data.http_status_code || '异常'} | Schema匹配: ${data.schema_configured === false ? '未配置' : (data.schema_matched ? '是' : '未通过')}`,
                type: "error",
                duration: 6000
            });
        }
        await fetchData();
        if (apiForm.value.machine_id) {
            await fetchMachineEnvironment(apiForm.value.machine_id);
        }
    } catch (err) {
        ElMessage.error("探测失败: " + (err.response?.data?.detail || err.message));
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
        is_active: row.is_active !== false,
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
        ElMessage.error("加载接口专属时序历史失败: " + (err.response?.data?.detail || err.message));
        historyList.value = [];
        loadingHistory.value = false;
        await nextTick();
        setTimeout(() => {
            renderChart([]);
        }, 150);
    }
};

export { activeDefaultHeadersCount, addHeaderRow, addParamRow, addPostActionRow, addPreActionRow, apiActiveTab, apiAuthConfig, apiAuthType, apiBodyText, apiBodyType, apiDialogVisible, apiEnvAvgLatency, apiEnvHealthyCount, apiEnvIssueCount, apiEnvOnlineMachineCount, apiEnvTotalCount, apiForm, apiHeadersList, apiInferring, apiIntervalUnit, apiIntervalValue, apiParamsList, apiPostActionsList, apiPreActionsList, apiResponseTab, apiSampleJson, apiSearchQuery, apiSubmitting, apiTestResult, apiTestRunning, applyPostActionPreset, applyPreActionPreset, avgApiLatency, clearBodyJson, copyResponseBody, copyText, createDefaultHeaders, currentEnvApisForKpi, currentEnvMachineOptions, editingApiId, filteredApis, formatBodyJson, formatIfJson, formatIntervalDisplay, formatSampleJson, formatSchemaJson, getEffectiveHeaders, getIntervalTooltip, handleDeleteApi, handleInferApiSchema, handleTestRunApi, handleTriggerApi, healthyApiCount, inferSchemaFromTestResult, insertMacroToBody, isHeaderOverridden, isSyncingUrlParams, issueApiCount, minifyBodyJson, onPostActionTypeChange, openApiMetricsDrawer, openCreateApiDialog, openEditApiDialog, removeHeaderRow, removeParamRow, removePostActionRow, removePreActionRow, safeFormatJson, safeMinifyJson, selectedApiEnv, selectedApiMachine, selectedApiStatus, setQuickInterval, showDefaultHeaders, submitApiForm, syncParamsToPath, syncPathToParams, systemDefaultHeaders, toggleApiActive, triggeringApiId }
