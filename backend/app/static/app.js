const { createApp, ref, computed, onMounted, nextTick } = Vue;

const app = createApp({
    setup() {
        const loading = ref(false);
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

        const sampleJsonText = ref("");
        const form = ref({
            name: "",
            group_name: "生产环境",
            host: "",
            port: 80,
            http_path: "/get",
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

        // 契约演进实验室专属数据
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
                case "targets": return "环境与服务拨测工作台";
                case "schema_lab": return "Schema 契约演进实验室";
                case "incidents": return "故障告警排障中心";
                case "settings": return "SMTP 邮件配置说明";
                default: return "监控工作台";
            }
        });

        // 故障异常节点提取 (用于 Incidents 视图)
        const downTargets = computed(() => {
            return targets.value.filter(t => t.current_status === "DOWN" || t.current_status === "DEGRADED");
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

        // vue-element-admin 风格侧边栏激活项与展开控制
        const activeMenuKey = ref("dashboard");

        const handleMenuSelect = (key) => {
            activeMenuKey.value = key;
            if (key === "dashboard") {
                currentNav.value = "dashboard";
            } else if (key === "env_management") {
                currentNav.value = "env_management";
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
                default: return "status-badge unknown";
            }
        };

        const getStatusIcon = (status) => {
            switch (status) {
                case "HEALTHY": return "fa-solid fa-circle-check";
                case "DOWN": return "fa-solid fa-circle-xmark";
                case "DEGRADED": return "fa-solid fa-triangle-exclamation";
                default: return "fa-solid fa-circle-question";
            }
        };

        const fetchData = async () => {
            loading.value = true;
            try {
                const [targetsRes, summaryRes, groupsRes, envsRes] = await Promise.all([
                    axios.get("/api/targets"),
                    axios.get("/api/dashboard/summary"),
                    axios.get("/api/groups"),
                    axios.get("/api/environments")
                ]);
                targets.value = targetsRes.data;
                summary.value = summaryRes.data;
                environmentList.value = envsRes.data;

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

                // 合并环境资产，保证所有环境即使未挂载目标也在侧边栏展现
                const mergedGroups = [];
                for (const env of environmentList.value) {
                    const stats = envMap[env.name] || { name: env.name, total: 0, healthy: 0, down: 0 };
                    mergedGroups.push(stats);
                }
                for (const gName of Object.keys(envMap)) {
                    if (!mergedGroups.some(g => g.name === gName)) {
                        mergedGroups.push(envMap[gName]);
                    }
                }
                groupList.value = mergedGroups;
            } catch (err) {
                ElementPlus.ElMessage.error("获取监控数据失败: " + (err.response?.data?.detail || err.message));
            } finally {
                loading.value = false;
            }
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
            currentNav.value = "targets";
            selectedGroup.value = envName;
            activeMenuKey.value = `targets:${envName}`;
        };

        const getEnvTargetCount = (envName) => {
            return targets.value.filter(t => (t.group_name || "生产环境") === envName).length;
        };

        const openCreateDialog = () => {
            editingTargetId.value = null;
            form.value = {
                name: "",
                group_name: selectedGroup.value !== "ALL" ? selectedGroup.value : "生产环境",
                host: "",
                port: 80,
                http_path: "/get",
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
                http_path: row.http_path || "/get",
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
                form.value.schema_text = JSON.stringify(res.data.schema, null, 2);
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
                labSchemaOutput.value = JSON.stringify(res.data.schema, null, 2);
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

            try {
                const [historyRes, metricsRes] = await Promise.all([
                    axios.get(`/api/targets/${target.id}/history?limit=30`),
                    axios.get(`/api/targets/${target.id}/metrics?hours=24`)
                ]);
                historyList.value = Array.isArray(historyRes.data) ? historyRes.data : [];
                loadingHistory.value = false;

                await nextTick();
                setTimeout(() => {
                    renderChart(Array.isArray(metricsRes.data) ? metricsRes.data : []);
                }, 150);
            } catch (err) {
                console.error("加载时序报表异常:", err);
                ElementPlus.ElMessage.error("加载时序报表失败: " + (err.response?.data?.detail || err.message));
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

        return {
            loading,
            targets,
            groupList,
            selectedGroup,
            currentNav,
            activeMenuKey,
            handleMenuSelect,
            navTitle,
            downTargets,
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
            labJsonInput,
            labStrictMode,
            labSchemaOutput,
            labInferring,
            handleLabInfer,
            copyLabSchema,
            drawerVisible,
            activeTarget,
            loadingHistory,
            historyList,
            fetchData,
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
            getEnvTargetCount
        };
    }
});

app.use(ElementPlus);
app.mount("#app");
