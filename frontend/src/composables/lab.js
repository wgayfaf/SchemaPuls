import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

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

const handleLabInfer = async () => {
    if (!labJsonInput.value.trim()) {
        ElMessage.warning("请先输入合法的 JSON 样本");
        return;
    }
    let parsed = null;
    try {
        parsed = JSON.parse(labJsonInput.value);
    } catch (e) {
        ElMessage.error("JSON 格式校验失败: " + e.message);
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
        ElMessage.success("实验室 Schema 结构推导完毕！");
    } catch (err) {
        ElMessage.error("推导失败: " + (err.response?.data?.detail || err.message));
    } finally {
        labInferring.value = false;
    }
};

const copyLabSchema = () => {
    if (!labSchemaOutput.value) return;
    navigator.clipboard.writeText(labSchemaOutput.value).then(() => {
        ElMessage.success("已复制 Schema 到剪贴板！");
    });
};

const copySchemaToValidate = () => {
    if (!labSchemaOutput.value) return;
    labValidateSchemaText.value = labSchemaOutput.value;
    labValidateJsonText.value = labJsonInput.value;
    labActiveTab.value = "validate";
    labValidationResult.value = null;
    ElMessage.success("已将生成的 Schema 及样本数据载入破坏性变更仿真！");
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
        ElMessage.warning("请先输入或从推导结果导入预期 Schema 契约规则！");
        return;
    }
    if (!labValidateJsonText.value.trim()) {
        ElMessage.warning("请先输入待测试的实际响应 JSON 数据！");
        return;
    }
    let parsedSchema, parsedData;
    try {
        parsedSchema = JSON.parse(labValidateSchemaText.value);
    } catch (e) {
        ElMessage.error("预期 Schema 格式错误: " + e.message);
        return;
    }
    try {
        parsedData = JSON.parse(labValidateJsonText.value);
    } catch (e) {
        ElMessage.error("待测 JSON 格式错误: " + e.message);
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
            ElMessage.success("契约校验完全通过！未发现破坏性变更");
        } else {
            ElMessage.warning(`捕获到 ${res.data.error_count} 项破坏性结构变更！`);
        }
    } catch (err) {
        ElMessage.error("校验请求失败: " + (err.response?.data?.detail || err.message));
    } finally {
        labValidating.value = false;
    }
};

export { copyLabSchema, copySchemaToValidate, handleLabInfer, handleLabValidate, labActiveTab, labInferring, labJsonInput, labSchemaOutput, labStrictMode, labValidateJsonText, labValidateSchemaText, labValidating, labValidationResult, loadValidateSample }
