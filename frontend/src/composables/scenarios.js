/**
 * scenarios.js — 场景拨测域 (业务链路多步骤拨测)
 *
 * 核心概念: 场景 = 有序步骤链 (业务链路节点) + 共享变量池 + 清理步骤保障
 *   - 业务链路节点流位于【新建/编辑场景】对话框中定时调度区下方
 *   - 点击节点仅切换数据源, 下方接口配置区 (Postman 风格 Params/Headers/Body/Auth/前置/后置) 界面保持不变
 *   - is_cleanup 节点为清理步骤 (如 DELETE 脏数据), 拨测引擎将保证其无论成败均执行 (finally 语义)
 *   - 步骤间变量传递与执行引擎将在后续版本接入
 *
 * 模块级单例状态 (与其他领域 composables 保持一致)
 */
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import axios from 'axios'
import { machineList, environmentList, apiList } from './core'
import { fetchMachineEnvironment, currentMachineEnvironment } from './machines'

// ================= 列表与筛选状态 =================
const scenarioList = ref([])
const scenarioLoading = ref(false)
const scenarioSearchQuery = ref('')
const selectedScenarioEnv = ref('ALL')

// ================= 对话框与表单状态 =================
const scenarioDialogVisible = ref(false)
const editingScenarioId = ref(null)
const scenarioSubmitting = ref(false)

const scenarioForm = ref({
    machine_id: null,
    name: '',
    description: '',
    base_url: '',
    cron_interval_minutes: 5,
    is_active: true
})

// 拨测周期数值 + 单位 (与接口管理一致的交互)
const scenarioIntervalValue = ref(5)
const scenarioIntervalUnit = ref("minutes")

// 业务链路步骤链与当前选中节点
const scenarioSteps = ref([])
const activeStepIndex = ref(0)

// 当前选中节点的 Postman 配置 Tab 状态
const stepActiveTab = ref("params")

// ================= 拨测执行引擎交互状态 =================
const scenarioRunningId = ref(null)          // 正在手动执行的场景 id (按钮 loading)
const scenarioResultVisible = ref(false)     // 执行结果抽屉
const scenarioResult = ref(null)             // 最近一次执行的历史流水 (含逐节点明细)
const stepTestRunning = ref(false)           // 单节点调试发包中
const stepTestResult = ref(null)             // 单节点调试结果

// ================= 数据获取 =================
const fetchScenarios = async () => {
    scenarioLoading.value = true
    try {
        const res = await axios.get('/api/scenarios')
        scenarioList.value = res.data
    } catch (err) {
        ElMessage.error('获取场景列表失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        scenarioLoading.value = false
    }
}

// ================= 计算属性 =================
// 按环境筛选后的场景集合
const currentEnvScenarios = computed(() => {
    if (selectedScenarioEnv.value === 'ALL') return scenarioList.value
    return scenarioList.value.filter(s => {
        if (s.environment_name === selectedScenarioEnv.value) return true
        const env = environmentList.value.find(e => e.name === selectedScenarioEnv.value)
        return env && s.environment_id === env.id
    })
})

const filteredScenarios = computed(() => {
    let list = currentEnvScenarios.value
    if (scenarioSearchQuery.value && scenarioSearchQuery.value.trim()) {
        const q = scenarioSearchQuery.value.toLowerCase().trim()
        list = list.filter(s =>
            (s.name && s.name.toLowerCase().includes(q)) ||
            (s.description && s.description.toLowerCase().includes(q)) ||
            (s.machine_name && s.machine_name.toLowerCase().includes(q))
        )
    }
    return list
})

// 当前环境可选的机器节点 (对话框宿主机器下拉)
const scenarioMachineOptions = computed(() => {
    if (selectedScenarioEnv.value === 'ALL') return machineList.value
    return machineList.value.filter(m => {
        if (m.environment_name === selectedScenarioEnv.value) return true
        const env = environmentList.value.find(e => e.name === selectedScenarioEnv.value)
        return env && m.environment_id === env.id
    })
})

// KPI 指标
const scenarioTotalCount = computed(() => currentEnvScenarios.value.length)
const scenarioActiveCount = computed(() => currentEnvScenarios.value.filter(s => s.is_active).length)
const scenarioCleanupCount = computed(() => currentEnvScenarios.value.filter(s => s.cleanup_step_count > 0).length)
const scenarioStepTotalCount = computed(() => currentEnvScenarios.value.reduce((acc, s) => acc + (s.step_count || 0), 0))

// 当前选中节点
const activeStep = computed(() => scenarioSteps.value[activeStepIndex.value] || null)

// 对话框内机器展示信息 (环境联动信息条)
const scenarioMachineDisplayName = computed(() => {
    const m = machineList.value.find(item => item.id === scenarioForm.value.machine_id)
    if (!m) return '未选择机器节点'
    return `${m.name} (${m.host}:${m.port})`
})

// ================= 步骤 (节点) 操作 =================
const createEmptyStep = () => ({
    name: '',
    http_method: 'GET',
    http_path: '/',
    http_params: [{ enabled: true, key: "", value: "", description: "" }],
    http_headers: [{ enabled: true, key: "", value: "", description: "" }],
    http_body_type: 'none',   // 'none' | 'json' | 'form'
    http_body: '',
    auth_type: 'none',
    auth_config: { token: "", username: "", password: "", header_key: "Authorization", header_value: "" },
    pre_actions: [],
    post_actions: [
        { enabled: true, name: "HTTP 状态码等于 200", type: "assert_status_code", expression: "", operator: "equals", target_value: "200", description: "" }
    ],
    is_cleanup: false
})

const addScenarioStep = () => {
    scenarioSteps.value.push(createEmptyStep())
    activeStepIndex.value = scenarioSteps.value.length - 1
    stepActiveTab.value = "params"
}

const removeScenarioStep = (idx) => {
    const step = scenarioSteps.value[idx]
    const tip = step && step.is_cleanup
        ? `确定删除清理步骤 [${idx + 1}. ${step.name || '未命名节点'}] 吗？删除后该环节产生的脏数据将无法自动清理！`
        : `确定删除步骤 [${idx + 1}. ${step?.name || '未命名节点'}] 吗？`
    ElMessageBox.confirm(tip, '删除节点', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
    }).then(() => {
        scenarioSteps.value.splice(idx, 1)
        if (activeStepIndex.value >= scenarioSteps.value.length) {
            activeStepIndex.value = Math.max(0, scenarioSteps.value.length - 1)
        }
        ElMessage.success('节点已删除')
    }).catch(() => { })
}

const selectScenarioStep = (idx) => {
    activeStepIndex.value = idx
    stepActiveTab.value = "params"
    stepTestResult.value = null
}

// ================= 机器联动: 自动填充基准地址与环境变量 =================
const fillBaseUrlFromMachine = (m) => {
    if (m.base_url && m.base_url.trim()) return m.base_url.trim()
    const scheme = m.port === 443 ? 'https' : 'http'
    return (m.port === 80 || m.port === 443) ? `${scheme}://${m.host}` : `${scheme}://${m.host}:${m.port}`
}

watch(() => scenarioForm.value.machine_id, (newMId) => {
    if (!newMId) return
    fetchMachineEnvironment(newMId)
    const m = machineList.value.find(item => item.id === newMId)
    if (!m) return
    scenarioForm.value.base_url = fillBaseUrlFromMachine(m)
})

const resetScenarioBaseUrlToMachine = () => {
    const m = machineList.value.find(item => item.id === scenarioForm.value.machine_id)
    if (m) {
        scenarioForm.value.base_url = fillBaseUrlFromMachine(m)
        ElMessage.success('已恢复为机器默认地址')
    }
}

// ================= 周期快捷预设 =================
const setQuickScenarioInterval = (val, unit) => {
    scenarioIntervalValue.value = val
    scenarioIntervalUnit.value = unit
}

// ================= Postman 风格步骤配置 (数据源为当前选中节点 activeStep) =================
// 系统默认请求头 (与接口管理 createDefaultHeaders 保持一致)
const createScenarioDefaultHeaders = () => [
    { enabled: true, key: "User-Agent", value: "SchemaPulse/2.0 (PostmanRuntime)", description: "客户端探针引擎标识", isSystem: true, isCalculated: false },
    { enabled: true, key: "Accept", value: "*/*", description: "默认允许接收所有响应类型", isSystem: true, isCalculated: false },
    { enabled: true, key: "Accept-Encoding", value: "gzip, deflate, br", description: "客户端支持的压缩算法", isSystem: true, isCalculated: false },
    { enabled: true, key: "Connection", value: "keep-alive", description: "保持 HTTP 长连接", isSystem: true, isCalculated: false },
    { enabled: true, key: "Host", value: "<根据请求目标地址自动解析>", description: "根据目标地址动态解析主机名", isSystem: true, isCalculated: true },
    { enabled: true, key: "Content-Type", value: "application/json", description: "根据请求体格式自动配置", isSystem: true, isCalculated: false, isDynamicType: true },
    { enabled: true, key: "Content-Length", value: "<根据请求体大小自动计算>", description: "根据请求体实际长度动态填充", isSystem: true, isCalculated: true }
]

const scenarioSystemDefaultHeaders = ref(createScenarioDefaultHeaders())
const showStepDefaultHeaders = ref(false)

const activeScenarioDefaultHeadersCount = computed(() => {
    return scenarioSystemDefaultHeaders.value.filter(h => h.enabled).length
})

const isStepHeaderOverridden = (key) => {
    if (!activeStep.value) return false
    return (activeStep.value.http_headers || []).some(h => h.enabled && h.key && h.key.trim().toLowerCase() === String(key).toLowerCase())
}

// ---- Params ----
const addStepParamRow = () => {
    activeStep.value?.http_params.push({ enabled: true, key: "", value: "", description: "" })
}

const removeStepParamRow = (idx) => {
    if (!activeStep.value) return
    activeStep.value.http_params.splice(idx, 1)
    if (activeStep.value.http_params.length === 0) {
        activeStep.value.http_params.push({ enabled: true, key: "", value: "", description: "" })
    }
    syncStepParamsToPath()
}

// ---- Headers ----
const addStepHeaderRow = () => {
    activeStep.value?.http_headers.push({ enabled: true, key: "", value: "", description: "" })
}

const removeStepHeaderRow = (idx) => {
    if (!activeStep.value) return
    activeStep.value.http_headers.splice(idx, 1)
    if (activeStep.value.http_headers.length === 0) {
        activeStep.value.http_headers.push({ enabled: true, key: "", value: "", description: "" })
    }
}

// ---- Body ----
const formatStepBodyJson = () => {
    if (!activeStep.value) return
    try {
        const parsed = JSON.parse(activeStep.value.http_body)
        activeStep.value.http_body = JSON.stringify(parsed, null, 2)
        ElMessage.success('JSON 已格式化')
    } catch (e) {
        ElMessage.error('当前内容不是合法 JSON, 无法格式化')
    }
}

const minifyStepBodyJson = () => {
    if (!activeStep.value) return
    try {
        const parsed = JSON.parse(activeStep.value.http_body)
        activeStep.value.http_body = JSON.stringify(parsed)
        ElMessage.success('JSON 已压缩为单行')
    } catch (e) {
        ElMessage.error('当前内容不是合法 JSON, 无法压缩')
    }
}

const clearStepBodyJson = () => {
    if (activeStep.value) activeStep.value.http_body = ''
}

// ---- URL 与 Params 双向同步 (移植自接口管理) ----
let isSyncingStepUrlParams = false

const syncStepParamsToPath = () => {
    if (isSyncingStepUrlParams || !activeStep.value) return
    isSyncingStepUrlParams = true
    try {
        const currentPath = activeStep.value.http_path || ""
        const basePath = currentPath.includes("?") ? currentPath.split("?")[0] : currentPath
        const queryPairs = activeStep.value.http_params.filter(p => {
            if (!p.enabled || !p.key || !p.key.trim()) return false
            const k = p.key.trim()
            const isPathVariable = basePath.includes(`{${k}}`) || basePath.includes(`:${k}`) || (p.description && p.description.includes("路径参数"))
            return !isPathVariable
        })
        if (queryPairs.length === 0) {
            activeStep.value.http_path = basePath
        } else {
            const q = queryPairs.map(p => `${encodeURIComponent(p.key.trim())}=${encodeURIComponent(p.value || "")}`).join("&")
            activeStep.value.http_path = basePath ? `${basePath}?${q}` : `?${q}`
        }
    } finally {
        isSyncingStepUrlParams = false
    }
}

const syncStepPathToParams = (newPath) => {
    if (isSyncingStepUrlParams || !activeStep.value) return
    isSyncingStepUrlParams = true
    try {
        if (!newPath) return
        const basePath = newPath.includes("?") ? newPath.split("?")[0] : newPath
        const queryString = newPath.includes("?") ? newPath.split("?")[1] : ""

        const pathVarParams = activeStep.value.http_params.filter(p => {
            if (!p.key) return false
            const k = p.key.trim()
            return basePath.includes(`{${k}}`) || basePath.includes(`:${k}`) || (p.description && p.description.includes("路径参数"))
        })

        const queryParams = []
        if (queryString) {
            const searchParams = new URLSearchParams(queryString)
            searchParams.forEach((val, key) => {
                queryParams.push({ enabled: true, key, value: val, description: "" })
            })
        }

        const merged = [...pathVarParams, ...queryParams]
        activeStep.value.http_params = merged.length > 0 ? merged : [{ enabled: true, key: "", value: "", description: "" }]
    } catch (e) {
        // 忽略路径输入过程中的格式异常
    } finally {
        isSyncingStepUrlParams = false
    }
}

const onStepPathInput = (newPath) => syncStepPathToParams(newPath)

// ---- 前置操作 ----
const addStepPreActionRow = () => {
    activeStep.value?.pre_actions.push({ enabled: true, type: "set_variable", key: "", value: "", description: "" })
}

const removeStepPreActionRow = (idx) => {
    activeStep.value?.pre_actions.splice(idx, 1)
}

const applyStepPreActionPreset = (preset) => {
    if (!activeStep.value) return
    if (preset === 'js_script') {
        activeStep.value.pre_actions.push({ enabled: true, type: "javascript", key: "", value: "", description: "Postman JS 脚本" })
    } else if (preset === 'script') {
        activeStep.value.pre_actions.push({ enabled: true, type: "custom_script", key: "", value: "", description: "Python 脚本" })
    }
    ElMessage.success("已添加前置操作！")
}

// ---- 后置操作 ----
const addStepPostActionRow = () => {
    activeStep.value?.post_actions.push({
        enabled: true, name: "验证响应状态", type: "assert_status_code",
        expression: "", operator: "equals", target_value: "200", value: "", description: ""
    })
}

const removeStepPostActionRow = (idx) => {
    activeStep.value?.post_actions.splice(idx, 1)
}

const onStepPostActionTypeChange = (item) => {
    if (item.type === 'assert_status_code') {
        item.name = item.name || "HTTP 状态码等于 200"
        item.expression = ""; item.operator = "equals"; item.target_value = "200"
    } else if (item.type === 'assert_latency') {
        item.name = item.name || "响应耗时 < 1000ms"
        item.expression = ""; item.operator = "less_than"; item.target_value = "1000"
    } else if (item.type === 'assert_json_path') {
        item.name = item.name || "验证 JSON 字段值"
        item.expression = item.expression || "code"; item.operator = "equals"; item.target_value = "200"
    } else if (item.type === 'assert_header') {
        item.name = item.name || "响应头校验"
        item.expression = item.expression || "content-type"; item.operator = "contains"; item.target_value = "application/json"
    } else if (item.type === 'assert_body_contains') {
        item.name = item.name || "响应内容包含关键字"
        item.expression = ""; item.operator = "contains"; item.target_value = "OK"
    } else if (item.type === 'extract_variable') {
        item.name = item.name || "提取响应数据"
        item.expression = item.expression || "data.id"; item.operator = "extract"; item.target_value = "targetId"
    } else if (item.type === 'javascript') {
        item.name = item.name || "Postman JS 脚本断言"
        item.expression = ""; item.value = item.value || ""; item.operator = "pm.test"; item.target_value = ""
    }
}

const applyStepPostActionPreset = (preset) => {
    if (!activeStep.value) return
    const presets = {
        status_200: { enabled: true, name: "状态码等于 200", type: "assert_status_code", expression: "", operator: "equals", target_value: "200" },
        status_2xx: { enabled: true, name: "状态码在 2xx 成功范围", type: "assert_status_code", expression: "", operator: "in_2xx", target_value: "" },
        latency_1000: { enabled: true, name: "响应耗时 < 1000ms", type: "assert_latency", expression: "", operator: "less_than", target_value: "1000" },
        json_code: { enabled: true, name: "JSON code 等于 200", type: "assert_json_path", expression: "code", operator: "equals", target_value: "200" },
        contains_ok: { enabled: true, name: "响应文本包含 OK", type: "assert_body_contains", expression: "", operator: "contains", target_value: "OK" },
        extract_var: { enabled: true, name: "提取响应 Token", type: "extract_variable", expression: "data.token", operator: "extract", target_value: "authToken" },
        js_test: { enabled: true, name: "Postman JS 脚本测试断言", type: "javascript", value: "", operator: "pm.test", target_value: "", description: "Postman Tests JS 断言脚本" }
    }
    if (presets[preset]) {
        activeStep.value.post_actions.push(presets[preset])
        ElMessage.success("已添加后置断言预设！")
    }
}

// ================= 从接口管理导入接口为链路节点 =================
const apiImportDialogVisible = ref(false)
const apiImportSearch = ref('')
const apiImportMethodFilter = ref('ALL')
const apiImportSelection = ref([])
const apiImportTableRef = ref(null)

// 可导入接口集合 (来自【接口管理】apiList, 支持名称/路径/机器搜索与方法筛选)
const importableApis = computed(() => {
    let list = apiList.value || []
    if (apiImportMethodFilter.value !== 'ALL') {
        list = list.filter(a => (a.http_method || '').toUpperCase() === apiImportMethodFilter.value)
    }
    const q = apiImportSearch.value.trim().toLowerCase()
    if (q) {
        list = list.filter(a =>
            (a.name && a.name.toLowerCase().includes(q)) ||
            (a.http_path && a.http_path.toLowerCase().includes(q)) ||
            (a.machine_name && a.machine_name.toLowerCase().includes(q))
        )
    }
    return list
})

// 将接口管理中的接口配置映射为业务链路节点 (深拷贝, 字段结构与场景步骤完全一致)
const mapApiToScenarioStep = (api) => {
    // Headers 归一化: 后端可能返回数组或字典两种结构
    let headers = []
    if (Array.isArray(api.http_headers)) {
        headers = api.http_headers.map(h => ({
            enabled: h.enabled !== false,
            key: h.key || '',
            value: h.value || '',
            description: h.description || ''
        }))
    } else if (api.http_headers && typeof api.http_headers === 'object') {
        headers = Object.entries(api.http_headers).map(([k, v]) => ({
            enabled: true, key: k, value: typeof v === 'string' ? v : String(v ?? ''), description: '导入自接口管理'
        }))
    }

    // Body 类型归一化: 接口管理的 form_data/raw 等类型映射为场景支持的 none/json/form
    let bodyType = (api.http_body_type || 'none').toLowerCase()
    if (bodyType === 'form_data' || bodyType === 'form') bodyType = 'form'
    else if (bodyType === 'raw' || bodyType === 'json') bodyType = 'json'
    else bodyType = 'none'

    // 鉴权类型归一化: 场景支持 none/bearer/basic/custom_header
    let authType = api.auth_type || 'none'
    if (authType === 'custom') authType = 'custom_header'
    else if (!['none', 'bearer', 'basic', 'custom_header'].includes(authType)) authType = 'none'

    const params = Array.isArray(api.http_params) && api.http_params.length
        ? api.http_params.map(p => ({ enabled: p.enabled !== false, key: p.key || '', value: p.value || '', description: p.description || '' }))
        : [{ enabled: true, key: '', value: '', description: '' }]

    return {
        name: api.name || '',
        http_method: (api.http_method || 'GET').toUpperCase(),
        http_path: api.http_path || '/',
        http_params: params,
        http_headers: headers.length ? headers : [{ enabled: true, key: '', value: '', description: '' }],
        http_body_type: bodyType,
        http_body: bodyType !== 'none' ? (api.http_body || '') : '',
        auth_type: authType,
        auth_config: Object.assign({ token: '', username: '', password: '', header_key: 'Authorization', header_value: '' }, api.auth_config || {}),
        pre_actions: Array.isArray(api.pre_actions) ? api.pre_actions.map(a => ({ ...a })) : [],
        post_actions: Array.isArray(api.post_actions) ? api.post_actions.map(a => ({ ...a })) : [],
        // DELETE 接口语义上即为清理脏数据, 批量导入时自动标记为清理步骤 (finally 语义)
        is_cleanup: (api.http_method || '').toUpperCase() === 'DELETE'
    }
}

const openApiImportDialog = () => {
    apiImportSearch.value = ''
    apiImportMethodFilter.value = 'ALL'
    apiImportSelection.value = []
    apiImportDialogVisible.value = true
    nextTick(() => apiImportTableRef.value?.clearSelection())
}

const handleApiImportSelectionChange = (rows) => {
    apiImportSelection.value = rows || []
}

// 批量导入: 将选中接口依次追加到当前选中节点之后
const confirmImportApisAsSteps = () => {
    if (!apiImportSelection.value.length) {
        ElMessage.warning('请先勾选需要导入的接口！')
        return
    }
    const steps = apiImportSelection.value.map(mapApiToScenarioStep)
    const insertAt = activeStepIndex.value + 1
    scenarioSteps.value.splice(insertAt, 0, ...steps)
    activeStepIndex.value = insertAt
    apiImportDialogVisible.value = false
    const cleanupCount = steps.filter(s => s.is_cleanup).length
    ElMessage.success(`已导入 ${steps.length} 个接口为业务链路节点${cleanupCount ? ` (其中 ${cleanupCount} 个 DELETE 接口已自动标记为清理步骤)` : ''}`)
}

// 单个导入: 用选中接口的配置覆盖填充当前选中节点
const fillActiveStepFromApi = (api) => {
    if (!activeStep.value) {
        ElMessage.warning('请先在业务链路中添加并选中一个节点！')
        return
    }
    const idx = activeStepIndex.value
    scenarioSteps.value[idx] = mapApiToScenarioStep(api)
    apiImportDialogVisible.value = false
    ElMessage.success(`节点 ${idx + 1} 已填入接口 [${api.name}] 的配置`)
}

// ================= 拨测执行引擎 =================
// 单步骤载荷构建 (与 buildStepsPayload 保持同一套过滤规则, 供整链提交与单步调试共用)
const buildStepPayload = (s) => ({
    name: (s.name || '').trim(),
    http_method: s.http_method,
    http_path: (s.http_path || '/').trim(),
    http_params: (s.http_params || []).filter(p => p.enabled && p.key && p.key.trim() !== ''),
    http_headers: (s.http_headers || []).filter(h => h.enabled && h.key && h.key.trim() !== '' && !h.isSystem),
    http_body_type: s.http_body_type || 'none',
    http_body: s.http_body_type !== 'none' ? s.http_body : null,
    auth_type: s.auth_type || 'none',
    auth_config: s.auth_type !== 'none' ? (s.auth_config || {}) : null,
    pre_actions: (s.pre_actions || []).filter(a => a.enabled && (a.key || a.value || a.type === 'custom_script' || a.type === 'javascript')),
    post_actions: (s.post_actions || []).filter(a => a.enabled && a.type),
    is_cleanup: !!s.is_cleanup
})

const buildStepsPayload = () => {
    return scenarioSteps.value.map(buildStepPayload)
}

// 手动立即执行整链拨测 (业务节点串行 + 清理节点 finally 保障)
const handleRunScenario = async (row) => {
    if (scenarioRunningId.value) return
    scenarioRunningId.value = row.id
    try {
        const res = await axios.post(`/api/scenarios/${row.id}/run`)
        const h = res.data.history
        scenarioResult.value = h
        scenarioResultVisible.value = true
        fetchScenarios()
        if (h.is_success) {
            ElMessage.success(`场景 [${row.name}] 拨测通过！共 ${h.steps_detail.length} 个节点, 总耗时 ${h.total_latency_ms}ms`)
        } else {
            ElMessage.error(`场景 [${row.name}] 拨测存在失败节点: ${h.error_message || '详见执行详情'}`)
        }
    } catch (err) {
        ElMessage.error('执行场景拨测失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        scenarioRunningId.value = null
    }
}

// 节点状态徽章文案与样式 (结果抽屉用)
const getStepResultBadge = (d) => {
    if (d.skipped) return { text: '已跳过', style: { background: '#f1f5f9', color: '#64748b', border: '1px solid #e2e8f0' } }
    if (d.ok) return { text: '通过', style: { background: '#ecfdf5', color: '#059669', border: '1px solid #a7f3d0' } }
    return { text: '失败', style: { background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' } }
}

// 单节点无状态调试 (新建/编辑场景对话框中的发送调试, 不落库不回写场景状态)
const handleTestRunStep = async () => {
    if (!scenarioForm.value.machine_id) {
        ElMessage.warning('请先选择场景归属的机器节点！')
        return
    }
    if (!activeStep.value) {
        ElMessage.warning('请先在业务链路中添加并选中一个节点！')
        return
    }
    if (!activeStep.value.http_path || !activeStep.value.http_path.trim()) {
        ElMessage.warning('当前节点的请求路径不能为空！')
        return
    }
    stepTestRunning.value = true
    try {
        const res = await axios.post('/api/scenarios/test-step', {
            machine_id: scenarioForm.value.machine_id,
            base_url: scenarioForm.value.base_url ? scenarioForm.value.base_url.trim() : null,
            step: buildStepPayload(activeStep.value)
        })
        stepTestResult.value = res.data
        const ok = res.data.ok
        if (ok) {
            ElMessage.success(`节点调试通过: HTTP ${res.data.status_code}, 耗时 ${res.data.latency_ms}ms`)
        } else {
            ElMessage.warning(`节点调试未通过: ${res.data.error || '断言未全部通过'} (HTTP ${res.data.status_code ?? '-'})`)
        }
        // 同步调试产生的环境变量回当前机器环境上下文
        if (res.data.environment && res.data.environment.updated_variables && Object.keys(res.data.environment.updated_variables).length > 0) {
            currentMachineEnvironment.value.variables = res.data.environment.variables || {}
            ElNotification({
                title: '环境变量已同步',
                message: `调试提取的 ${Object.keys(res.data.environment.updated_variables).length} 个变量已持久化至环境【${res.data.environment.name}】`,
                type: 'success',
                duration: 4000
            })
        }
    } catch (err) {
        ElMessage.error('节点调试失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        stepTestRunning.value = false
    }
}

// ================= 对话框开关 =================
const resetScenarioForm = () => {
    let mId = machineList.value.length > 0 ? machineList.value[0].id : null
    let initialBaseUrl = ''
    if (mId) {
        const m = machineList.value.find(item => item.id === mId)
        if (m) initialBaseUrl = fillBaseUrlFromMachine(m)
    }
    scenarioForm.value = {
        machine_id: mId,
        name: '',
        description: '',
        base_url: initialBaseUrl,
        cron_interval_minutes: 5,
        is_active: true
    }
    scenarioIntervalValue.value = 5
    scenarioIntervalUnit.value = "minutes"
    scenarioSteps.value = [createEmptyStep()]
    activeStepIndex.value = 0
    stepActiveTab.value = "params"
    stepTestResult.value = null
    scenarioSystemDefaultHeaders.value = createScenarioDefaultHeaders()
    showStepDefaultHeaders.value = false
    if (mId) fetchMachineEnvironment(mId)
}

const openCreateScenarioDialog = () => {
    editingScenarioId.value = null
    resetScenarioForm()
    scenarioDialogVisible.value = true
}

const openEditScenarioDialog = (row) => {
    editingScenarioId.value = row.id
    scenarioForm.value = {
        machine_id: row.machine_id,
        name: row.name,
        description: row.description || '',
        base_url: row.base_url || '',
        cron_interval_minutes: row.cron_interval_minutes || 5,
        is_active: row.is_active !== false
    }
    // 反推周期数值与单位
    const mins = row.cron_interval_minutes || 5
    if (mins % 1440 === 0) {
        scenarioIntervalValue.value = mins / 1440
        scenarioIntervalUnit.value = "days"
    } else if (mins % 60 === 0) {
        scenarioIntervalValue.value = mins / 60
        scenarioIntervalUnit.value = "hours"
    } else {
        scenarioIntervalValue.value = mins
        scenarioIntervalUnit.value = "minutes"
    }
    // 深拷贝步骤链, 保证每个节点具备完整字段结构 (与接口配置区数据结构一致)
    scenarioSteps.value = (row.steps || []).map(s => ({
        name: s.name || '',
        http_method: s.http_method || 'GET',
        http_path: s.http_path || '/',
        http_params: Array.isArray(s.http_params) && s.http_params.length
            ? s.http_params.map(p => ({ enabled: p.enabled !== false, key: p.key || '', value: p.value || '', description: p.description || '' }))
            : [{ enabled: true, key: "", value: "", description: "" }],
        http_headers: Array.isArray(s.http_headers) && s.http_headers.length
            ? s.http_headers.map(h => ({ enabled: h.enabled !== false, key: h.key || '', value: h.value || '', description: h.description || '' }))
            : [{ enabled: true, key: "", value: "", description: "" }],
        http_body_type: s.http_body_type || 'none',
        http_body: s.http_body || '',
        auth_type: s.auth_type || 'none',
        auth_config: Object.assign({ token: "", username: "", password: "", header_key: "Authorization", header_value: "" }, s.auth_config || {}),
        pre_actions: Array.isArray(s.pre_actions) ? s.pre_actions : [],
        post_actions: Array.isArray(s.post_actions) ? s.post_actions : [],
        is_cleanup: !!s.is_cleanup
    }))
    if (scenarioSteps.value.length === 0) {
        scenarioSteps.value = [createEmptyStep()]
    }
    activeStepIndex.value = 0
    stepActiveTab.value = "params"
    stepTestResult.value = null
    scenarioSystemDefaultHeaders.value = createScenarioDefaultHeaders()
    showStepDefaultHeaders.value = false
    if (row.machine_id) fetchMachineEnvironment(row.machine_id)
    scenarioDialogVisible.value = true
}

// ================= 提交 =================
const submitScenarioForm = async () => {
    if (!scenarioForm.value.machine_id) {
        ElMessage.warning('请选择场景归属的机器节点！')
        return
    }
    if (!scenarioForm.value.name || !scenarioForm.value.name.trim()) {
        ElMessage.warning('请输入场景名称！')
        return
    }
    if (scenarioSteps.value.length === 0) {
        ElMessage.warning('业务链路至少需要一个步骤节点！')
        return
    }
    const invalidIdx = scenarioSteps.value.findIndex(s => !s.http_path || !s.http_path.trim())
    if (invalidIdx !== -1) {
        ElMessage.warning(`第 ${invalidIdx + 1} 个节点的请求路径不能为空！`)
        activeStepIndex.value = invalidIdx
        return
    }

    // 智能根据所选单位计算最终存入后端的分钟数 (与接口管理一致)
    let finalIntervalMinutes = 5
    if (scenarioIntervalUnit.value === "days") {
        finalIntervalMinutes = Math.max(1, Math.round(scenarioIntervalValue.value * 1440))
    } else if (scenarioIntervalUnit.value === "hours") {
        finalIntervalMinutes = Math.max(1, Math.round(scenarioIntervalValue.value * 60))
    } else {
        finalIntervalMinutes = Math.max(1, Math.round(scenarioIntervalValue.value || 5))
    }

    const payload = {
        machine_id: scenarioForm.value.machine_id,
        name: scenarioForm.value.name.trim(),
        description: scenarioForm.value.description ? scenarioForm.value.description.trim() : null,
        base_url: scenarioForm.value.base_url ? scenarioForm.value.base_url.trim() : null,
        steps: buildStepsPayload(),
        cron_interval_minutes: finalIntervalMinutes,
        is_active: scenarioForm.value.is_active !== false
    }

    scenarioSubmitting.value = true
    try {
        if (editingScenarioId.value) {
            await axios.put(`/api/scenarios/${editingScenarioId.value}`, payload)
            ElMessage.success(`场景 [${payload.name}] 已更新！`)
        } else {
            await axios.post('/api/scenarios', payload)
            ElMessage.success(`场景 [${payload.name}] 创建成功！`)
        }
        scenarioDialogVisible.value = false
        fetchScenarios()
    } catch (err) {
        ElMessage.error('保存场景失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        scenarioSubmitting.value = false
    }
}

// ================= 删除 =================
const handleDeleteScenario = async (row) => {
    try {
        await axios.delete(`/api/scenarios/${row.id}`)
        ElMessage.success(`场景 [${row.name}] 已删除`)
        fetchScenarios()
    } catch (err) {
        ElMessage.error('删除场景失败: ' + (err.response?.data?.detail || err.message))
    }
}

// ================= 样式工具 =================
const getMethodBadgeStyle = (method) => {
    switch ((method || 'GET').toUpperCase()) {
        case 'GET': return { background: '#ecfdf5', color: '#059669', border: '1px solid #a7f3d0' }
        case 'POST': return { background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe' }
        case 'PUT': return { background: '#fffbeb', color: '#d97706', border: '1px solid #fde68a' }
        case 'DELETE': return { background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' }
        case 'PATCH': return { background: '#f5f3ff', color: '#7c3aed', border: '1px solid #ddd6fe' }
        default: return { background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0' }
    }
}

const getScenarioStatusBadgeClass = (status) => {
    switch (status) {
        case 'HEALTHY': return 'status-badge healthy'
        case 'DOWN': return 'status-badge down'
        default: return 'status-badge unknown'
    }
}

const getScenarioStatusText = (status) => {
    switch (status) {
        case 'HEALTHY': return '运行正常'
        case 'DOWN': return '存在异常'
        default: return '待首次拨测'
    }
}

export {
    scenarioList, scenarioLoading, scenarioSearchQuery, selectedScenarioEnv,
    scenarioDialogVisible, editingScenarioId, scenarioSubmitting, scenarioForm,
    scenarioIntervalValue, scenarioIntervalUnit, setQuickScenarioInterval,
    scenarioSteps, activeStepIndex, activeStep, stepActiveTab,
    fetchScenarios, currentEnvScenarios, filteredScenarios, scenarioMachineOptions,
    scenarioTotalCount, scenarioActiveCount, scenarioCleanupCount, scenarioStepTotalCount,
    scenarioMachineDisplayName,
    createEmptyStep, addScenarioStep, removeScenarioStep, selectScenarioStep,
    resetScenarioBaseUrlToMachine,
    scenarioSystemDefaultHeaders, showStepDefaultHeaders, activeScenarioDefaultHeadersCount, isStepHeaderOverridden,
    addStepParamRow, removeStepParamRow, addStepHeaderRow, removeStepHeaderRow,
    formatStepBodyJson, minifyStepBodyJson, clearStepBodyJson,
    syncStepParamsToPath, onStepPathInput,
    addStepPreActionRow, removeStepPreActionRow, applyStepPreActionPreset,
    addStepPostActionRow, removeStepPostActionRow, onStepPostActionTypeChange, applyStepPostActionPreset,
    openCreateScenarioDialog, openEditScenarioDialog, submitScenarioForm, handleDeleteScenario,
    scenarioRunningId, scenarioResultVisible, scenarioResult, stepTestRunning, stepTestResult,
    handleRunScenario, getStepResultBadge, handleTestRunStep,
    apiImportDialogVisible, apiImportSearch, apiImportMethodFilter, apiImportSelection, apiImportTableRef,
    importableApis, openApiImportDialog, handleApiImportSelectionChange, confirmImportApisAsSteps, fillActiveStepFromApi,
    getMethodBadgeStyle, getScenarioStatusBadgeClass, getScenarioStatusText
}
