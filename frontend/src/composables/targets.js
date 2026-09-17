import { ref, computed, nextTick } from 'vue'
import { apiList, fetchData, targets } from './core'
import { ElMessage, ElNotification } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'

const selectedGroup = ref("ALL");

const triggeringId = ref(null);

const createDialogVisible = ref(false);

const editingTargetId = ref(null);

const submitting = ref(false);

const inferring = ref(false);

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

// 抽屉与图表
const drawerVisible = ref(false);

const activeTarget = ref(null);

const loadingHistory = ref(false);

const historyList = ref([]);

let echartsInstance = null;

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

const handleTrigger = async (row) => {
    triggeringId.value = row.id;
    try {
        const res = await axios.post(`/api/targets/${row.id}/trigger`);
        const data = res.data;
        if (data.is_healthy) {
            ElNotification({
                title: `探测连通正常 [${row.name}]`,
                message: `TCP: ${data.tcp_latency_ms}ms | HTTP 200: ${data.http_latency_ms}ms | 契约 Schema 完全匹配`,
                type: "success"
            });
        } else {
            let errMsg = "探测异常: ";
            if (!data.tcp_ok) errMsg += "TCP 端口未开放; ";
            if (data.http_status_code !== 200) errMsg += `HTTP 状态码 ${data.http_status_code}; `;
            if (!data.schema_matched) errMsg += "Schema 捕获破坏性结构变更; ";

            ElNotification({
                title: `服务异常预警 [${row.name}]`,
                message: errMsg,
                type: "error",
                duration: 6000
            });
        }
        await fetchData();
    } catch (err) {
        ElMessage.error("探测请求异常: " + (err.response?.data?.detail || err.message));
    } finally {
        triggeringId.value = null;
    }
};

const handleDelete = async (targetId) => {
    try {
        await axios.delete(`/api/targets/${targetId}`);
        ElMessage.success("监控目标已从当前环境移除");
        await fetchData();
    } catch (err) {
        ElMessage.error("删除失败: " + (err.response?.data?.detail || err.message));
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
        ElMessage.warning("请先粘贴真实的响应 JSON 样本");
        return;
    }
    let parsed = null;
    try {
        parsed = JSON.parse(sampleJsonText.value);
    } catch (e) {
        ElMessage.error("JSON 格式错误: " + e.message);
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
        ElMessage.success("已成功转换为 Draft-7 Schema 规则模板！");
    } catch (err) {
        ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
    } finally {
        inferring.value = false;
    }
};

const submitCreateTarget = async () => {
    if (!form.value.name || !form.value.host || !form.value.port) {
        ElMessage.warning("请完整填写环境、名称、IP/域名与端口");
        return;
    }
    let parsedSchema = null;
    try {
        parsedSchema = JSON.parse(form.value.schema_text);
    } catch (e) {
        ElMessage.error("Schema 规则必须是合法的 JSON: " + e.message);
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
            ElMessage.success("监控目标已更新！");
        } else {
            await axios.post("/api/targets", payload);
            ElMessage.success("监控目标创建成功，后台定时调度引擎已接管！");
        }
        createDialogVisible.value = false;
        await fetchData();
    } catch (err) {
        ElMessage.error((editingTargetId.value ? "更新失败: " : "创建失败: ") + (err.response?.data?.detail || err.message));
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
            ElMessage.error("加载时序报表失败: " + (err.response?.data?.detail || err.message));
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

export { activeTarget, createDialogVisible, downTargets, drawerVisible, echartsInstance, editingTargetId, filteredDownTargets, filteredTargets, form, handleDelete, handleInferSchema, handleTrigger, historyList, incidentSearchQuery, inferring, loadingHistory, openCreateDialog, openEditDialog, openMetricsDrawer, renderChart, sampleJsonText, selectedGroup, submitCreateTarget, submitting, triggeringId }
