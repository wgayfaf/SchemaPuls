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
import * as echarts from 'echarts'
import { machineList, environmentList, apiList } from './core'
import { fetchMachineEnvironment, currentMachineEnvironment } from './machines'
import { safeFormatJson, formatIntervalDisplay } from './apis'

// ================= 列表与筛选状态 =================
const scenarioList = ref([])
const scenarioLoading = ref(false)
const scenarioSearchQuery = ref('')
const selectedScenarioEnv = ref('ALL')
const selectedScenarioMachine = ref('ALL')
const selectedScenarioStatus = ref('ALL')

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

// ================= 场景专属变量池 (仅限当前场景生效, 隔离防污染) =================
// 场景专属变量结构: [{ enabled: true, key: 'userId', value: '1001', description: '用户ID' }]
const scenarioVariablesList = ref([])
const scenarioVariablesDrawerVisible = ref(false)

const scenarioVariablesCount = computed(() => {
    return scenarioVariablesList.value.filter(v => v.key && v.key.trim()).length
})

const addScenarioVariableRow = () => {
    scenarioVariablesList.value.push({ enabled: true, key: '', value: '', description: '' })
}

const removeScenarioVariableRow = (idx) => {
    scenarioVariablesList.value.splice(idx, 1)
}

const clearScenarioVariables = () => {
    scenarioVariablesList.value = []
}

const getScenarioVariablesObject = () => {
    const obj = {}
    for (const item of scenarioVariablesList.value) {
        if (item.enabled !== false && item.key && item.key.trim()) {
            obj[item.key.trim()] = item.value !== undefined && item.value !== null ? item.value : ''
        }
    }
    return obj
}

const setScenarioVariablesFromObject = (obj) => {
    if (!obj || typeof obj !== 'object') {
        scenarioVariablesList.value = []
        return
    }
    scenarioVariablesList.value = Object.entries(obj).map(([key, value]) => ({
        enabled: true,
        key,
        value: typeof value === 'object' ? JSON.stringify(value) : String(value ?? ''),
        description: ''
    }))
}

const copyVariableMacro = (key) => {
    if (!key) return
    const macro = `{{${key}}}`
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(macro)
            .then(() => ElMessage.success(`已复制宏变量: ${macro}`))
            .catch(() => ElMessage.info(`宏变量: ${macro}`))
    } else {
        ElMessage.info(`宏变量: ${macro}`)
    }
}

// ================= 拨测执行引擎交互状态 =================
const scenarioRunningId = ref(null)          // 正在手动执行的场景 id (按钮 loading)
const scenarioResultVisible = ref(false)     // 执行结果抽屉
const scenarioResult = ref(null)             // 最近一次执行的历史流水 (含逐节点明细)
const stepTestRunning = ref(false)           // 单节点调试发包中
const stepTestResult = ref(null)             // 单节点调试结果

// ================= 节点调试响应面板: 场景专属变量提取器 & 跨接口引用助手 =================
const stepResponseTab = ref('body')          // 'body' (响应体) | 'extract' (提取场景变量)
const stepExtractedVarNames = ref({})        // 路径对应自定义变量名缓存: { 'data.token': 'token' }
const customExtractPath = ref('')            // 自定义提取路径输入框: 如 data.items[0].id
const customExtractVarName = ref('')         // 自定义提取变量名输入框: 如 firstItemId

const safeParseJson = (str) => {
    if (!str || typeof str !== 'string') return null
    try {
        return JSON.parse(str)
    } catch {
        return null
    }
}

// 获取当前调试响应的 JSON 数据对象
const getStepResponseJsonObject = () => {
    if (!stepTestResult.value) return null
    if (stepTestResult.value.response_data && typeof stepTestResult.value.response_data === 'object') {
        return stepTestResult.value.response_data
    }
    return safeParseJson(stepTestResult.value.response_snippet)
}

// 格式化输出完整的响应体 JSON
const getStepResponseFormattedBody = computed(() => {
    if (!stepTestResult.value) return ''
    if (stepTestResult.value.response_data !== undefined && stepTestResult.value.response_data !== null) {
        try {
            return JSON.stringify(stepTestResult.value.response_data, null, 2)
        } catch {
            return String(stepTestResult.value.response_data)
        }
    }
    if (stepTestResult.value.response_snippet) {
        try {
            const parsed = JSON.parse(stepTestResult.value.response_snippet)
            return JSON.stringify(parsed, null, 2)
        } catch {
            return stepTestResult.value.response_snippet
        }
    }
    return stepTestResult.value.error ? '无响应内容' : '该请求未返回有效响应体'
})

// 智能推测字段对应的变量名
const getSuggestedVarName = (path) => {
    if (!path) return 'var'
    const clean = path.replace(/\[\d+\]/g, '')
    const parts = clean.split('.').filter(Boolean)
    if (parts.length === 0) return 'var'
    if (parts.length === 1) return parts[0]
    const last = parts[parts.length - 1]
    const secondLast = parts[parts.length - 2]
    if (['id', 'name', 'code', 'status', 'token', 'key', 'val'].includes(last.toLowerCase()) && secondLast && secondLast !== 'data') {
        return secondLast + last.charAt(0).toUpperCase() + last.slice(1)
    }
    return last
}

// 递归遍历响应体，提取所有叶子字段路径及其当前采样值
const extractJsonLeafPaths = (data, maxDepth = 4, maxItems = 40) => {
    const list = []
    if (data === null || data === undefined || typeof data !== 'object') {
        return list
    }

    const walk = (obj, path = '', depth = 1) => {
        if (list.length >= maxItems || depth > maxDepth) return
        if (obj === null || obj === undefined) {
            list.push({ path, value: obj, type: 'null' })
            return
        }
        if (Array.isArray(obj)) {
            if (obj.length === 0) {
                list.push({ path, value: '[]', type: 'array' })
                return
            }
            if (typeof obj[0] !== 'object' || obj[0] === null) {
                list.push({ path: `${path}[0]`, value: obj[0], type: typeof obj[0] })
            } else {
                walk(obj[0], `${path}[0]`, depth + 1)
            }
            return
        }
        if (typeof obj === 'object') {
            for (const [k, v] of Object.entries(obj)) {
                if (list.length >= maxItems) break
                const currentPath = path ? `${path}.${k}` : k
                if (v !== null && typeof v === 'object') {
                    if (Array.isArray(v)) {
                        if (v.length === 0) {
                            list.push({ path: currentPath, value: '[]', type: 'array' })
                        } else if (typeof v[0] !== 'object' || v[0] === null) {
                            list.push({ path: `${currentPath}[0]`, value: v[0], type: typeof v[0] })
                        } else {
                            walk(v[0], `${currentPath}[0]`, depth + 1)
                        }
                    } else {
                        walk(v, currentPath, depth + 1)
                    }
                } else {
                    list.push({ path: currentPath, value: v, type: typeof v })
                }
            }
        }
    }

    walk(data)
    return list
}

// 响应面板解析出的所有可提取字段列表
const stepExtractableFields = computed(() => {
    const obj = getStepResponseJsonObject()
    if (!obj) return []
    const leaves = extractJsonLeafPaths(obj)
    return leaves.map(item => {
        const defaultName = getSuggestedVarName(item.path)
        if (!stepExtractedVarNames.value[item.path]) {
            stepExtractedVarNames.value[item.path] = defaultName
        }
        return {
            ...item,
            suggestedVarName: defaultName
        }
    })
})

// 根据路径评估对象值 (支持点分与 [0] 下标)
const evaluatePathValue = (obj, path) => {
    if (!obj || !path) return undefined
    try {
        const normalized = path.replace(/\[(\d+)\]/g, '.$1').replace(/^\./, '')
        const keys = normalized.split('.').filter(Boolean)
        let curr = obj
        for (const k of keys) {
            if (curr === null || curr === undefined) return undefined
            curr = curr[k]
        }
        return curr
    } catch {
        return undefined
    }
}

// 自定义路径提取实时预览
const customExtractPreview = computed(() => {
    if (!customExtractPath.value || !customExtractPath.value.trim()) return null
    const obj = getStepResponseJsonObject()
    if (!obj) return null
    const val = evaluatePathValue(obj, customExtractPath.value.trim())
    return val !== undefined ? val : null
})

// 检查某个字段或变量名是否已在当前节点的 post_actions 中配置提取
const isFieldExtractedInActiveStep = (path, varName) => {
    if (!activeStep.value || !activeStep.value.post_actions) return false
    return activeStep.value.post_actions.some(
        a => a.enabled && a.type === 'extract_variable' && (a.expression === path || a.target_value === varName)
    )
}

// 一键将响应预览中的字段设为场景专属变量
const quickExtractFieldToScenarioVariable = (item) => {
    if (!activeStep.value) {
        ElMessage.warning('请先在业务链路中选中当前节点')
        return
    }
    const path = item.path
    const varName = (stepExtractedVarNames.value[path] || item.suggestedVarName || item.customVarName || '').trim()
    if (!varName) {
        ElMessage.warning('场景变量名不能为空')
        return
    }

    // 1. 注入当前节点的后置操作 (extract_variable)，确保场景后续运行能自动执行动态提取
    if (!activeStep.value.post_actions) {
        activeStep.value.post_actions = []
    }
    const existingAction = activeStep.value.post_actions.find(
        a => a.type === 'extract_variable' && (a.target_value === varName || a.expression === path)
    )
    if (existingAction) {
        existingAction.enabled = true
        existingAction.expression = path
        existingAction.target_value = varName
        existingAction.name = `提取 ${varName}`
    } else {
        activeStep.value.post_actions.push({
            enabled: true,
            name: `提取 ${varName}`,
            type: 'extract_variable',
            expression: path,
            operator: 'equals',
            target_value: varName
        })
    }

    // 2. 将当前调试采样值同步写入场景专属变量池 (仅限当前场景有效, 隔离防污染)
    const stringVal = typeof item.value === 'object' ? JSON.stringify(item.value) : String(item.value ?? '')
    const existingVar = scenarioVariablesList.value.find(v => v.key === varName)
    const stepLabel = `节点 ${(activeStepIndex.value + 1)} (${activeStep.value.name || '步骤'})`
    if (existingVar) {
        existingVar.value = stringVal
        existingVar.enabled = true
        existingVar.description = `来自 ${stepLabel} 响应 [${path}]`
    } else {
        scenarioVariablesList.value.push({
            enabled: true,
            key: varName,
            value: stringVal,
            description: `来自 ${stepLabel} 响应 [${path}]`
        })
    }

    ElNotification({
        title: '场景变量提取成功 (隔离保护生效)',
        message: `已将响应字段 [${path}] 设为场景变量 {{${varName}}}！可在后续节点的 Body、Params、Headers 或 URL 中一键引用，严格隔离不污染外部环境。`,
        type: 'success',
        duration: 4500
    })
}

// 自定义路径一键提取为场景专属变量
const addCustomExtractToScenarioVariable = () => {
    const path = customExtractPath.value ? customExtractPath.value.trim() : ''
    const varName = customExtractVarName.value ? customExtractVarName.value.trim() : ''
    if (!path) {
        ElMessage.warning('请输入提取表达式 (如 data.token 或 items[0].id)')
        return
    }
    if (!varName) {
        ElMessage.warning('请输入场景专属变量名')
        return
    }
    const val = customExtractPreview.value
    quickExtractFieldToScenarioVariable({
        path,
        value: val !== undefined ? val : '',
        customVarName: varName
    })
    customExtractPath.value = ''
    customExtractVarName.value = ''
}

// ================= 跨接口/后续接口一键使用场景专属变量 =================
// 1. 插入到请求 Body (JSON 或 Form)
const insertScenarioVarToStepBody = (varKey) => {
    if (!activeStep.value) return
    if (!varKey) return
    const macro = `{{${varKey}}}`

    // 若当前光标在 textarea 中, 直接在光标处插入
    const textarea = document.querySelector('.pm-code-box textarea')
    if (textarea && document.activeElement === textarea) {
        const start = textarea.selectionStart || 0
        const end = textarea.selectionEnd || 0
        const text = activeStep.value.http_body || ''
        activeStep.value.http_body = text.substring(0, start) + macro + text.substring(end)
        ElMessage.success(`已在光标处插入宏变量: ${macro}`)
        return
    }

    // 若 Body 为空, 初始化为标准包含该变量的 JSON
    const bodyStr = (activeStep.value.http_body || '').trim()
    if (!bodyStr || bodyStr === '{}') {
        activeStep.value.http_body = JSON.stringify({ [varKey]: macro }, null, 2)
        ElMessage.success(`已在 Body 中初始化插入 "${varKey}": "${macro}"`)
        return
    }

    // 若当前 Body 为合法 JSON 对象, 智能追加或更新该字段
    try {
        const parsed = JSON.parse(bodyStr)
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            parsed[varKey] = macro
            activeStep.value.http_body = JSON.stringify(parsed, null, 2)
            ElMessage.success(`已在 Body 中合并字段 "${varKey}": "${macro}"`)
            return
        }
    } catch {
        // 非合规 JSON, 文本末尾追加
    }

    activeStep.value.http_body = (activeStep.value.http_body ? activeStep.value.http_body + '\n' : '') + `"${varKey}": "${macro}"`
    ElMessage.success(`已追加宏变量 ${macro} 到 Body`)
}

// 2. 插入到 URL Params
const insertScenarioVarToStepParam = (varKey) => {
    if (!activeStep.value) return
    if (!varKey) return
    if (!activeStep.value.http_params) activeStep.value.http_params = []
    const macro = `{{${varKey}}}`
    activeStep.value.http_params.push({
        enabled: true,
        key: varKey,
        value: macro,
        description: '引用场景专属变量'
    })
    syncStepParamsToPath()
    ElMessage.success(`已添加参数: ${varKey}=${macro}`)
}

// 3. 插入到 Headers
const insertScenarioVarToStepHeader = (varKey, type = 'custom') => {
    if (!activeStep.value) return
    if (!varKey) return
    if (!activeStep.value.http_headers) activeStep.value.http_headers = []
    const macro = `{{${varKey}}}`

    let headerKey = varKey
    let headerVal = macro
    let desc = '引用场景专属变量'

    if (type === 'bearer') {
        headerKey = 'Authorization'
        headerVal = `Bearer ${macro}`
        desc = 'Bearer Token (场景变量)'
    } else if (type === 'token') {
        headerKey = 'token'
        headerVal = macro
    }

    const existing = activeStep.value.http_headers.find(h => h.key && h.key.toLowerCase() === headerKey.toLowerCase())
    if (existing) {
        existing.value = headerVal
        existing.enabled = true
        ElMessage.success(`已更新请求头: ${headerKey}: ${headerVal}`)
    } else {
        activeStep.value.http_headers.push({
            enabled: true,
            key: headerKey,
            value: headerVal,
            description: desc
        })
        ElMessage.success(`已添加请求头: ${headerKey}: ${headerVal}`)
    }
}

// 4. 插入到 URL 路径 (Path)
const insertScenarioVarToStepPath = (varKey) => {
    if (!activeStep.value) return
    if (!varKey) return
    const macro = `{{${varKey}}}`
    const current = (activeStep.value.http_path || '').trim()
    if (!current || current === '/') {
        activeStep.value.http_path = `/${macro}`
    } else if (current.includes('?')) {
        const [p, q] = current.split('?')
        activeStep.value.http_path = `${p.endsWith('/') ? p : p + '/'}${macro}?${q}`
    } else {
        activeStep.value.http_path = `${current.endsWith('/') ? current : current + '/'}${macro}`
    }
    ElMessage.success(`已插入宏变量 ${macro} 到请求路径`)
}

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

const toggleScenarioActive = async (row) => {
    try {
        const res = await axios.post(`/api/scenarios/${row.id}/toggle-active`)
        if (res.data) {
            row.is_active = res.data.is_active
            ElMessage.success(`场景 [${row.name}] 自动定时调度已${row.is_active ? '开启' : '关闭'}`)
        }
    } catch (err) {
        ElMessage.error('切换场景定时调度状态失败: ' + (err.response?.data?.detail || err.message))
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
    if (selectedScenarioMachine.value !== 'ALL') {
        list = list.filter(s => s.machine_id === selectedScenarioMachine.value)
    }
    if (selectedScenarioStatus.value !== 'ALL') {
        list = list.filter(s => s.current_status === selectedScenarioStatus.value)
    }
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

// ================= 场景列表分页状态 =================
const scenarioCurrentPage = ref(1)
const scenarioPageSize = ref(10)

const paginatedScenarios = computed(() => {
    const start = (scenarioCurrentPage.value - 1) * scenarioPageSize.value
    return filteredScenarios.value.slice(start, start + scenarioPageSize.value)
})

// 当筛选条件或搜索关键词变动时，重置分页至第 1 页
watch([selectedScenarioEnv, selectedScenarioMachine, selectedScenarioStatus, scenarioSearchQuery], () => {
    scenarioCurrentPage.value = 1
})

// 当过滤列表数量或单页条数变动导致当前页越界时，自动校准当前页
watch([filteredScenarios, scenarioPageSize], () => {
    const maxPage = Math.max(1, Math.ceil(filteredScenarios.value.length / scenarioPageSize.value))
    if (scenarioCurrentPage.value > maxPage) {
        scenarioCurrentPage.value = maxPage
    }
})

// ================= 业务链路步骤折叠与展开状态 (解决多接口平铺变形) =================
const expandedScenarioStepIds = ref(new Set())

const isScenarioStepsExpanded = (id) => expandedScenarioStepIds.value.has(id)

const toggleScenarioStepsExpand = (id) => {
    const next = new Set(expandedScenarioStepIds.value)
    if (next.has(id)) {
        next.delete(id)
    } else {
        next.add(id)
    }
    expandedScenarioStepIds.value = next
}

const isAllScenarioStepsExpanded = computed(() => {
    const scenariosWithMoreSteps = filteredScenarios.value.filter(s => (s.steps || []).length > 2)
    if (!scenariosWithMoreSteps.length) return false
    return scenariosWithMoreSteps.every(s => expandedScenarioStepIds.value.has(s.id))
})

const toggleAllScenarioStepsExpand = () => {
    if (isAllScenarioStepsExpanded.value) {
        expandedScenarioStepIds.value = new Set()
    } else {
        const next = new Set()
        filteredScenarios.value.forEach(s => {
            if ((s.steps || []).length > 2) {
                next.add(s.id)
            }
        })
        expandedScenarioStepIds.value = next
    }
}

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
    schema_text: "",
    is_cleanup: false
})

const addScenarioStep = () => {
    scenarioSteps.value.push(createEmptyStep())
    activeStepIndex.value = scenarioSteps.value.length - 1
    stepActiveTab.value = "params"
}

// 在指定索引位置插入新步骤 (未传参或越界则追加到末尾)
const insertScenarioStep = (index = null) => {
    const newStep = createEmptyStep()
    const targetIndex = (index === null || index === undefined)
        ? scenarioSteps.value.length
        : Math.min(Math.max(0, index), scenarioSteps.value.length)
    
    scenarioSteps.value.splice(targetIndex, 0, newStep)
    activeStepIndex.value = targetIndex
    stepActiveTab.value = "params"
    ElMessage.success(`已在第 ${targetIndex + 1} 位插入新节点`)
}

// 任意两步骤间移动/换位
const moveScenarioStep = (fromIndex, toIndex) => {
    if (fromIndex < 0 || fromIndex >= scenarioSteps.value.length) return
    if (toIndex < 0 || toIndex >= scenarioSteps.value.length) return
    if (fromIndex === toIndex) return

    const [movedStep] = scenarioSteps.value.splice(fromIndex, 1)
    scenarioSteps.value.splice(toIndex, 0, movedStep)

    // 保持当前聚焦节点跟随或者正确修正索引
    if (activeStepIndex.value === fromIndex) {
        activeStepIndex.value = toIndex
    } else if (fromIndex < activeStepIndex.value && toIndex >= activeStepIndex.value) {
        activeStepIndex.value -= 1
    } else if (fromIndex > activeStepIndex.value && toIndex <= activeStepIndex.value) {
        activeStepIndex.value += 1
    }
}

const moveStepLeft = (idx) => {
    if (idx <= 0) return
    moveScenarioStep(idx, idx - 1)
}

const moveStepRight = (idx) => {
    if (idx >= scenarioSteps.value.length - 1) return
    moveScenarioStep(idx, idx + 1)
}

// 复制节点配置 (在目标节点后直接追加副本)
const cloneScenarioStep = (idx) => {
    if (idx < 0 || idx >= scenarioSteps.value.length) return
    const orig = scenarioSteps.value[idx]
    const cloned = JSON.parse(JSON.stringify({
        ...orig,
        name: orig.name ? `${orig.name} (副本)` : '节点副本',
        _testResult: null
    }))
    scenarioSteps.value.splice(idx + 1, 0, cloned)
    activeStepIndex.value = idx + 1
    stepActiveTab.value = "params"
    ElMessage.success(`已复制节点为第 ${idx + 2} 位节点`)
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
        if (activeStepIndex.value > idx) {
            activeStepIndex.value -= 1
        } else if (activeStepIndex.value >= scenarioSteps.value.length) {
            activeStepIndex.value = Math.max(0, scenarioSteps.value.length - 1)
        }
        ElMessage.success('节点已删除')
    }).catch(() => { })
}

const selectScenarioStep = (idx) => {
    activeStepIndex.value = idx
    stepActiveTab.value = "params"
    stepTestResult.value = activeStep.value?._testResult || null
    stepResponseTab.value = "body"
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
// 保持用户勾选次序并支持自由上下微调的有序列表
const apiImportOrderedList = ref([])
// 插入位置: 'end' (追加到末尾) | 'after_active' (当前选中之后) | 'start' (开头) | 'after_${idx}'
const apiImportInsertPosition = ref('end')

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
        schema_text: api.expected_schema ? JSON.stringify(api.expected_schema, null, 2) : "",
        // DELETE 接口语义上即为清理脏数据, 批量导入时自动标记为清理步骤 (finally 语义)
        is_cleanup: (api.http_method || '').toUpperCase() === 'DELETE'
    }
}

const openApiImportDialog = (presetPosition = null) => {
    apiImportSearch.value = ''
    apiImportMethodFilter.value = 'ALL'
    apiImportSelection.value = []
    apiImportOrderedList.value = []
    if (presetPosition !== null && presetPosition !== undefined) {
        apiImportInsertPosition.value = presetPosition
    } else if (activeStepIndex.value >= 0 && scenarioSteps.value.length > 0) {
        apiImportInsertPosition.value = 'after_active'
    } else {
        apiImportInsertPosition.value = 'end'
    }
    apiImportDialogVisible.value = true
    nextTick(() => {
        apiImportTableRef.value?.clearSelection()
    })
}

const handleApiImportSelectionChange = (rows) => {
    apiImportSelection.value = rows || []
    const currentSelectedIds = new Set((rows || []).map(r => r.id))
    
    // 1. 过滤已取消勾选的项目
    const filtered = apiImportOrderedList.value.filter(item => currentSelectedIds.has(item.id))
    
    // 2. 将新勾选的项目顺序追加到有序列表末尾 (保留点选先后顺序)
    const existingIds = new Set(filtered.map(item => item.id))
    for (const row of (rows || [])) {
        if (!existingIds.has(row.id)) {
            filtered.push(row)
            existingIds.add(row.id)
        }
    }
    apiImportOrderedList.value = filtered
}

// 在待导入有序列表中上移一项
const moveImportedApiUp = (idx) => {
    if (idx <= 0 || idx >= apiImportOrderedList.value.length) return
    const list = [...apiImportOrderedList.value]
    const temp = list[idx]
    list[idx] = list[idx - 1]
    list[idx - 1] = temp
    apiImportOrderedList.value = list
}

// 在待导入有序列表中下移一项
const moveImportedApiDown = (idx) => {
    if (idx < 0 || idx >= apiImportOrderedList.value.length - 1) return
    const list = [...apiImportOrderedList.value]
    const temp = list[idx]
    list[idx] = list[idx + 1]
    list[idx + 1] = temp
    apiImportOrderedList.value = list
}

// 从待导入列表中移除单项并同步取消表格中的勾选状态
const removeImportedApi = (apiItem, idx) => {
    if (idx >= 0 && idx < apiImportOrderedList.value.length) {
        apiImportOrderedList.value.splice(idx, 1)
    }
    const matched = importableApis.value.find(a => a.id === apiItem.id)
    if (matched && apiImportTableRef.value) {
        apiImportTableRef.value.toggleRowSelection(matched, false)
    }
}

// 清空待导入选择
const clearAllImportedApis = () => {
    apiImportOrderedList.value = []
    apiImportSelection.value = []
    apiImportTableRef.value?.clearSelection()
}

// 批量按序导入: 根据选择的位置与排序好的接口列表插入到链路节点
const confirmImportApisAsSteps = () => {
    if (!apiImportOrderedList.value.length) {
        ElMessage.warning('请先勾选需要导入的接口！')
        return
    }
    const steps = apiImportOrderedList.value.map(mapApiToScenarioStep)
    
    let insertAt = scenarioSteps.value.length
    if (apiImportInsertPosition.value === 'start') {
        insertAt = 0
    } else if (apiImportInsertPosition.value === 'end') {
        insertAt = scenarioSteps.value.length
    } else if (apiImportInsertPosition.value === 'after_active') {
        insertAt = (activeStepIndex.value >= 0 && activeStepIndex.value < scenarioSteps.value.length)
            ? activeStepIndex.value + 1
            : scenarioSteps.value.length
    } else if (typeof apiImportInsertPosition.value === 'string' && apiImportInsertPosition.value.startsWith('after_')) {
        const targetIdx = parseInt(apiImportInsertPosition.value.replace('after_', ''), 10)
        insertAt = (!isNaN(targetIdx) && targetIdx >= 0) ? targetIdx + 1 : scenarioSteps.value.length
    } else if (typeof apiImportInsertPosition.value === 'number') {
        insertAt = apiImportInsertPosition.value
    }
    insertAt = Math.min(Math.max(0, insertAt), scenarioSteps.value.length)

    scenarioSteps.value.splice(insertAt, 0, ...steps)
    activeStepIndex.value = insertAt
    apiImportDialogVisible.value = false
    apiImportSelection.value = []
    apiImportOrderedList.value = []
    apiImportTableRef.value?.clearSelection()

    const cleanupCount = steps.filter(s => s.is_cleanup).length
    ElMessage.success(`已在第 ${insertAt + 1} 位顺序导入 ${steps.length} 个接口作为链路节点${cleanupCount ? ` (其中 ${cleanupCount} 个 DELETE 接口已自动标记为清理步骤)` : ''}`)
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
// 解析步骤的 Schema 文本为 Draft-7 对象 (非法 JSON 时返回 null 并提示)
const parseStepSchema = (s) => {
    if (!s.schema_text || !s.schema_text.trim()) return null
    try {
        const parsed = JSON.parse(s.schema_text)
        return parsed && typeof parsed === 'object' ? parsed : null
    } catch (e) {
        return undefined // 区分: 非法 JSON
    }
}

// 单步骤载荷构建 (与 buildStepsPayload 保持同一套过滤规则, 供整链提交与单步调试共用)
const buildStepPayload = (s) => {
    const schemaParsed = parseStepSchema(s)
    if (schemaParsed === undefined) {
        ElMessage.warning(`节点 [${s.name || '未命名'}] 的 Schema 不是合法 JSON, 已忽略该契约规则`)
    }
    return {
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
        expected_schema: schemaParsed === undefined ? null : schemaParsed,
        is_cleanup: !!s.is_cleanup
    }
}

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
        if (res.data.scenario) {
            Object.assign(row, res.data.scenario)
        }
        await fetchScenarios()
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
            step: buildStepPayload(activeStep.value),
            scenario_variables: getScenarioVariablesObject()
        })
        stepTestResult.value = res.data
        if (activeStep.value) {
            activeStep.value._testResult = res.data
        }
        const ok = res.data.ok
        if (ok) {
            ElMessage.success(`节点调试通过: HTTP ${res.data.status_code}, 耗时 ${res.data.latency_ms}ms`)
        } else {
            ElMessage.warning(`节点调试未通过: ${res.data.error || '断言未全部通过'} (HTTP ${res.data.status_code ?? '-'})`)
        }
        // 关键增强：将提取的场景变量同步到当前对话框的场景变量池中 (场景内隔离生效，绝不污染全局环境)
        if (res.data.extracted_scenario_variables && Object.keys(res.data.extracted_scenario_variables).length > 0) {
            for (const [k, v] of Object.entries(res.data.extracted_scenario_variables)) {
                const existing = scenarioVariablesList.value.find(item => item.key === k)
                if (existing) {
                    existing.value = typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')
                } else {
                    scenarioVariablesList.value.push({
                        enabled: true,
                        key: k,
                        value: typeof v === 'object' ? JSON.stringify(v) : String(v ?? ''),
                        description: `节点 ${(activeStepIndex.value + 1)} 调试自动提取`
                    })
                }
            }
            ElNotification({
                title: '场景变量已捕获 (场景内隔离生效)',
                message: `节点调试提取了 ${Object.keys(res.data.extracted_scenario_variables).length} 个场景变量，已同步至场景专属变量池（仅本场景可用，不污染外部环境）`,
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

// ================= Schema 契约 (节点级) =================
const stepSchemaSampleJson = ref("")
const stepInferring = ref(false)

const formatStepSchemaJson = () => {
    if (!activeStep.value) return
    if (!activeStep.value.schema_text || !activeStep.value.schema_text.trim()) {
        ElMessage.warning("当前 Schema 内容为空，无需格式化")
        return
    }
    try {
        activeStep.value.schema_text = safeFormatJson(activeStep.value.schema_text)
        ElMessage.success("Schema 契约规则格式化完成！")
    } catch (err) {
        ElMessage.error("Schema 格式错误: " + (err.message || "无法解析有效 JSON"))
    }
}

// 从自定义 JSON 样本推导 Draft-7 Schema
const inferStepSchemaFromSample = async () => {
    if (!activeStep.value) return
    if (!stepSchemaSampleJson.value.trim()) {
        ElMessage.warning("请先粘贴真实的响应 JSON 样本")
        return
    }
    stepInferring.value = true
    try {
        const parsed = JSON.parse(stepSchemaSampleJson.value)
        const res = await axios.post("/api/tools/infer-schema", { sample_json: parsed, strict_mode: false })
        const schemaObj = (res.data && res.data.schema) ? res.data.schema : res.data
        activeStep.value.schema_text = JSON.stringify(schemaObj, null, 2)
        ElMessage.success("成功从样本推导生成 Draft-7 契约规则！")
    } catch (err) {
        ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message))
    } finally {
        stepInferring.value = false
    }
}

// 从当前节点调试响应一键推导 Schema
const inferStepSchemaFromTestResult = async () => {
    if (!activeStep.value) return
    if (!stepTestResult.value || !stepTestResult.value.response_snippet) {
        ElMessage.warning("当前没有调试响应数据可供推导, 请先发送调试")
        return
    }
    stepInferring.value = true
    try {
        // 优先使用后端透出的完整响应, 兼容回退解析 snippet
        let responseData = stepTestResult.value.response_data || null
        if (!responseData) {
            try { responseData = JSON.parse(stepTestResult.value.response_snippet) } catch (e) { responseData = null }
        }
        if (!responseData) {
            ElMessage.warning("调试响应不是合法 JSON, 无法推导契约")
            return
        }
        const res = await axios.post("/api/tools/infer-schema", { sample_json: responseData, strict_mode: false })
        const schemaObj = (res.data && res.data.schema) ? res.data.schema : res.data
        activeStep.value.schema_text = JSON.stringify(schemaObj, null, 2)
        stepActiveTab.value = "schema"
        ElMessage.success("已从当前实际响应数据一键推导生成 Draft-7 Schema 契约！")
    } catch (err) {
        ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message))
    } finally {
        stepInferring.value = false
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
    scenarioVariablesList.value = []
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
    // 加载场景专属初始变量池
    setScenarioVariablesFromObject(row.variables || {})

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
        schema_text: s.expected_schema ? JSON.stringify(s.expected_schema, null, 2) : "",
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
        variables: getScenarioVariablesObject(),
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

// ================= 删除与批量操作 =================
const handleDeleteScenario = async (row) => {
    try {
        await axios.delete(`/api/scenarios/${row.id}`)
        ElMessage.success(`场景 [${row.name}] 已删除`)
        selectedScenarioRows.value = selectedScenarioRows.value.filter(r => r.id !== row.id)
        await fetchScenarios()
    } catch (err) {
        ElMessage.error('删除场景失败: ' + (err.response?.data?.detail || err.message))
    }
}

// 批量操作状态
const selectedScenarioRows = ref([])
const scenarioTableRef = ref(null)
const isScenarioBatchOperating = ref(false)

const handleScenarioSelectionChange = (rows) => {
    selectedScenarioRows.value = rows || []
}

const clearScenarioSelection = () => {
    if (scenarioTableRef.value) {
        scenarioTableRef.value.clearSelection()
    }
    selectedScenarioRows.value = []
}

// 批量删除场景
const handleBatchDeleteScenarios = async () => {
    if (!selectedScenarioRows.value.length) {
        ElMessage.warning('请先勾选需要批量删除的场景！')
        return
    }
    const count = selectedScenarioRows.value.length
    const ids = selectedScenarioRows.value.map(r => r.id)
    isScenarioBatchOperating.value = true
    try {
        const res = await axios.post('/api/scenarios/batch-delete', { ids })
        ElMessage.success(res.data.message || `成功批量删除 ${count} 个拨测场景`)
        clearScenarioSelection()
        await fetchScenarios()
    } catch (err) {
        ElMessage.error('批量删除场景失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        isScenarioBatchOperating.value = false
    }
}

// 批量启用/关闭场景探测周期
const handleBatchToggleScenarioActive = async (targetActiveState = false) => {
    if (!selectedScenarioRows.value.length) {
        ElMessage.warning(`请先勾选需要批量${targetActiveState ? '开启' : '关闭'}探测周期的场景！`)
        return
    }
    const count = selectedScenarioRows.value.length
    const ids = selectedScenarioRows.value.map(r => r.id)
    isScenarioBatchOperating.value = true
    try {
        const res = await axios.post('/api/scenarios/batch-toggle-active', { ids, is_active: targetActiveState })
        ElMessage.success(res.data.message || `成功批量${targetActiveState ? '开启' : '关闭'} ${count} 个场景的定时探测！`)
        selectedScenarioRows.value.forEach(r => {
            r.is_active = targetActiveState
        })
        clearScenarioSelection()
        await fetchScenarios()
    } catch (err) {
        ElMessage.error(`批量${targetActiveState ? '开启' : '关闭'}失败: ` + (err.response?.data?.detail || err.message))
    } finally {
        isScenarioBatchOperating.value = false
    }
}

// 批量修改场景探测周期
const handleBatchSetScenarioInterval = async (intervalMinutes) => {
    if (!selectedScenarioRows.value.length) {
        ElMessage.warning('请先勾选需要批量设置探测周期的场景！')
        return
    }
    const ids = selectedScenarioRows.value.map(r => r.id)
    isScenarioBatchOperating.value = true
    try {
        const res = await axios.post('/api/scenarios/batch-set-interval', { ids, cron_interval_minutes: intervalMinutes })
        ElMessage.success(res.data.message || `成功将 ${ids.length} 个场景的探测周期修改为 ${formatIntervalDisplay(intervalMinutes, true)}！`)
        selectedScenarioRows.value.forEach(r => {
            r.cron_interval_minutes = intervalMinutes
        })
        clearScenarioSelection()
        await fetchScenarios()
    } catch (err) {
        ElMessage.error('批量设置场景探测周期失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        isScenarioBatchOperating.value = false
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

// ================= 场景时序排障报表与运行历史抽屉 =================
const scenarioMetricsDrawerVisible = ref(false)
const scenarioMetricsLoading = ref(false)
const activeScenarioMetrics = ref(null)
const scenarioHistoryList = ref([])
let scenarioEchartsInstance = null

const renderScenarioChart = (points) => {
    const dom = document.getElementById('scenarioChartContainer')
    if (!dom) return

    if (scenarioEchartsInstance) {
        scenarioEchartsInstance.dispose()
    }
    scenarioEchartsInstance = echarts.init(dom)

    const times = points.map(p => p.time)
    const latencyData = points.map(p => (p.total_latency_ms !== undefined && p.total_latency_ms !== null ? p.total_latency_ms : null))

    const markPoints = points
        .filter(p => !p.is_success || p.schema_matched === false)
        .map(p => ({
            name: p.schema_matched === false ? "契约突变" : "链路失败",
            coord: [p.time, p.total_latency_ms || 10],
            value: p.schema_matched === false ? "MUTATE" : "FAIL",
            itemStyle: { color: "#dc2626" }
        }))

    const option = {
        backgroundColor: "transparent",
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "cross", crossStyle: { color: "#94a3b8" } },
            backgroundColor: "rgba(255, 255, 255, 0.96)",
            borderColor: "#fed7aa",
            borderWidth: 1,
            textStyle: { color: "#0f172a" },
            extraCssText: "box-shadow: 0 4px 14px rgba(249, 115, 22, 0.12); border-radius: 8px;",
            formatter: (params) => {
                if (!params || !params.length) return ""
                const idx = params[0].dataIndex
                const pt = points[idx]
                if (!pt) return ""
                let html = `<div style="font-weight: 700; font-size: 12.5px; margin-bottom: 4px; color: #0f172a;">${pt.timestamp ? pt.timestamp.replace('T', ' ').slice(0, 19) : pt.time}</div>`
                html += `<div style="font-size: 11.5px; color: #475569; margin-bottom: 2px;">触发方式: <b style="color: ${pt.trigger === 'manual' ? '#2563eb' : '#64748b'}">${pt.trigger === 'manual' ? '手动触发' : '定时调度'}</b></div>`
                html += `<div style="font-size: 11.5px; color: #475569; margin-bottom: 2px;">整链耗时: <b style="color: #ea580c;">${pt.total_latency_ms || 0} ms</b></div>`
                html += `<div style="font-size: 11.5px; margin-bottom: 2px;">执行状态: <b style="color: ${pt.is_success ? '#059669' : '#dc2626'}">${pt.is_success ? '整链通过' : '存在失败节点'}</b></div>`
                if (pt.schema_configured) {
                    html += `<div style="font-size: 11.5px; color: #475569; margin-bottom: 2px;">契约校验: <b style="color: ${pt.schema_matched === true ? '#059669' : '#dc2626'}">${pt.schema_matched === true ? '契约一致' : '契约突变'}</b></div>`
                } else {
                    html += `<div style="font-size: 11.5px; color: #94a3b8;">契约校验: 未配置</div>`
                }
                if (pt.error_message) {
                    html += `<div style="font-size: 11px; color: #dc2626; margin-top: 4px; max-width: 260px; word-break: break-all;">${pt.error_message}</div>`
                }
                return html
            }
        },
        legend: {
            data: ["整链耗时 (ms)"],
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
            name: "总耗时 (ms)",
            nameTextStyle: { color: "#64748b" },
            axisLine: { lineStyle: { color: "#cbd5e1" } },
            splitLine: { lineStyle: { color: "#f3f4f6", type: "dashed" } },
            axisLabel: { color: "#64748b", fontSize: 11 }
        },
        series: [
            {
                name: "整链耗时 (ms)",
                type: "line",
                smooth: true,
                data: latencyData,
                itemStyle: { color: "#f97316" },
                lineStyle: { width: 2.2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: "rgba(249, 115, 22, 0.22)" },
                        { offset: 1, color: "rgba(249, 115, 22, 0.01)" }
                    ])
                },
                markPoint: { data: markPoints }
            }
        ]
    }
    scenarioEchartsInstance.setOption(option)
}

const openScenarioMetricsDrawer = async (row) => {
    activeScenarioMetrics.value = { ...row }
    scenarioMetricsDrawerVisible.value = true
    scenarioMetricsLoading.value = true
    scenarioHistoryList.value = []
    try {
        const [historyRes, metricsRes] = await Promise.all([
            axios.get(`/api/scenarios/${row.id}/history?limit=50`),
            axios.get(`/api/scenarios/${row.id}/metrics`)
        ])
        scenarioHistoryList.value = Array.isArray(historyRes.data) ? historyRes.data : []
        scenarioMetricsLoading.value = false
        await nextTick()
        setTimeout(() => {
            renderScenarioChart(metricsRes.data?.points || [])
        }, 150)
    } catch (err) {
        console.error("加载场景时序与历史异常:", err)
        ElMessage.error("加载场景专属时序历史失败: " + (err.response?.data?.detail || err.message))
        scenarioHistoryList.value = []
        scenarioMetricsLoading.value = false
        await nextTick()
        setTimeout(() => {
            renderScenarioChart([])
        }, 150)
    }
}

window.addEventListener('resize', () => {
    if (scenarioEchartsInstance) {
        scenarioEchartsInstance.resize()
    }
})

export {
    scenarioList, scenarioLoading, scenarioSearchQuery, selectedScenarioEnv,
    selectedScenarioMachine, selectedScenarioStatus, toggleScenarioActive,
    scenarioDialogVisible, editingScenarioId, scenarioSubmitting, scenarioForm,
    scenarioIntervalValue, scenarioIntervalUnit, setQuickScenarioInterval,
    scenarioSteps, activeStepIndex, activeStep, stepActiveTab,
    fetchScenarios, currentEnvScenarios, filteredScenarios, scenarioMachineOptions,
    scenarioTotalCount, scenarioActiveCount, scenarioCleanupCount, scenarioStepTotalCount,
    scenarioMachineDisplayName,
    createEmptyStep, addScenarioStep, removeScenarioStep, selectScenarioStep,
    insertScenarioStep, moveScenarioStep, moveStepLeft, moveStepRight, cloneScenarioStep,
    resetScenarioBaseUrlToMachine,
    scenarioSystemDefaultHeaders, showStepDefaultHeaders, activeScenarioDefaultHeadersCount, isStepHeaderOverridden,
    addStepParamRow, removeStepParamRow, addStepHeaderRow, removeStepHeaderRow,
    formatStepBodyJson, minifyStepBodyJson, clearStepBodyJson,
    syncStepParamsToPath, onStepPathInput,
    addStepPreActionRow, removeStepPreActionRow, applyStepPreActionPreset,
    addStepPostActionRow, removeStepPostActionRow, onStepPostActionTypeChange, applyStepPostActionPreset,
    openCreateScenarioDialog, openEditScenarioDialog, submitScenarioForm, handleDeleteScenario,
    stepSchemaSampleJson, stepInferring, formatStepSchemaJson, inferStepSchemaFromSample, inferStepSchemaFromTestResult,
    scenarioRunningId, scenarioResultVisible, scenarioResult, stepTestRunning, stepTestResult,
    handleRunScenario, getStepResultBadge, handleTestRunStep,
    apiImportDialogVisible, apiImportSearch, apiImportMethodFilter, apiImportSelection, apiImportTableRef,
    apiImportOrderedList, apiImportInsertPosition, moveImportedApiUp, moveImportedApiDown, removeImportedApi, clearAllImportedApis,
    importableApis, openApiImportDialog, handleApiImportSelectionChange, confirmImportApisAsSteps, fillActiveStepFromApi,
    getMethodBadgeStyle, getScenarioStatusBadgeClass, getScenarioStatusText,
    scenarioMetricsDrawerVisible, scenarioMetricsLoading, activeScenarioMetrics, scenarioHistoryList,
    openScenarioMetricsDrawer, renderScenarioChart,
    expandedScenarioStepIds, isScenarioStepsExpanded, toggleScenarioStepsExpand, isAllScenarioStepsExpanded, toggleAllScenarioStepsExpand,
    scenarioVariablesList, scenarioVariablesDrawerVisible, scenarioVariablesCount,
    addScenarioVariableRow, removeScenarioVariableRow, clearScenarioVariables,
    getScenarioVariablesObject, setScenarioVariablesFromObject, copyVariableMacro,
    stepResponseTab, stepExtractedVarNames, customExtractPath, customExtractVarName,
    customExtractPreview, stepExtractableFields, getStepResponseFormattedBody,
    isFieldExtractedInActiveStep, quickExtractFieldToScenarioVariable, addCustomExtractToScenarioVariable,
    insertScenarioVarToStepBody, insertScenarioVarToStepParam, insertScenarioVarToStepHeader, insertScenarioVarToStepPath,
    selectedScenarioRows, scenarioTableRef, isScenarioBatchOperating,
    handleScenarioSelectionChange, clearScenarioSelection,
    handleBatchDeleteScenarios, handleBatchToggleScenarioActive, handleBatchSetScenarioInterval,
    scenarioCurrentPage, scenarioPageSize, paginatedScenarios
}
