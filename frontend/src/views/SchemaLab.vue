<template>
                <div v-show="currentNav === 'schema_lab'">
                    <div class="wb-card" style="margin-bottom: 20px;">
                        <!-- 实验室顶部导航与说明 -->
                        <div
                            style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 14px; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                            <div>
                                <div
                                    style="font-size: 16px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                                    <i class="fa-solid fa-flask-vial" style="color: #2563eb;"></i>
                                    <span>JSON Schema 契约生成与破坏性变更实验室</span>
                                </div>
                                <div style="font-size: 13px; color: #64748b; margin-top: 4px;">
                                    提供真实的 JSON 结构自动反向推导为 JSON Schema Draft-7 标准契约，并支持全链路破坏性变更仿真演进测试。
                                </div>
                            </div>
                            <div>
                                <el-radio-group v-model="labActiveTab" size="default">
                                    <el-radio-button label="infer">
                                        <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 4px;"></i>
                                        契约反向推导
                                    </el-radio-button>
                                    <el-radio-button label="validate">
                                        <i class="fa-solid fa-shield-halved" style="margin-right: 4px;"></i> 破坏性变更演进仿真
                                    </el-radio-button>
                                </el-radio-group>
                            </div>
                        </div>

                        <!-- 模式 1: 契约推导生成 -->
                        <div v-show="labActiveTab === 'infer'">
                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <div
                                        style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <div style="font-size: 13.5px; font-weight: 600; color: #334155;">
                                            1. 粘贴接口响应原始 JSON 样本
                                        </div>
                                        <el-checkbox v-model="labStrictMode">严格模式 (附加类型限定)</el-checkbox>
                                    </div>
                                    <el-input v-model="labJsonInput" type="textarea" :rows="18"
                                        style="font-family: Consolas, Monaco, monospace; font-size: 12.5px;"
                                        placeholder="在此粘贴标准的 JSON 数据...">
                                    </el-input>
                                    <div style="margin-top: 14px; display: flex; justify-content: flex-end; gap: 10px;">
                                        <el-button type="primary" @click="handleLabInfer" :loading="labInferring">
                                            <i class="fa-solid fa-wand-magic-sparkles" style="margin-right: 6px;"></i>执行
                                            Schema 推导
                                        </el-button>
                                    </div>
                                </el-col>
                                <el-col :span="12">
                                    <div
                                        style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <div style="font-size: 13.5px; font-weight: 600; color: #0369a1;">
                                            2. 生成的标准 Draft-7 JSON Schema 契约
                                        </div>
                                    </div>
                                    <el-input v-model="labSchemaOutput" type="textarea" :rows="18" readonly
                                        style="font-family: Consolas, Monaco, monospace; font-size: 12.5px;"
                                        placeholder="点击左下方【执行 Schema 推导】后在此实时呈现生成的契约结构...">
                                    </el-input>
                                    <div style="margin-top: 14px; display: flex; justify-content: flex-end; gap: 10px;">
                                        <el-button type="primary" plain @click="copyLabSchema"
                                            :disabled="!labSchemaOutput">
                                            <i class="fa-solid fa-copy" style="margin-right: 6px;"></i>复制 Schema
                                        </el-button>
                                        <el-button type="warning" plain @click="copySchemaToValidate"
                                            :disabled="!labSchemaOutput">
                                            <i class="fa-solid fa-arrow-right" style="margin-right: 6px;"></i>载入变更实验室测试
                                        </el-button>
                                    </div>
                                </el-col>
                            </el-row>
                        </div>

                        <!-- 模式 2: 破坏性变更仿真比对实验室 -->
                        <div v-show="labActiveTab === 'validate'">
                            <div
                                style="margin-bottom: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                                <div style="font-size: 13px; color: #475569;">
                                    <i class="fa-solid fa-circle-info" style="color: #3b82f6; margin-right: 6px;"></i>
                                    在左侧填入基准预期契约（Baseline Schema），右侧输入模拟变更后的接口返回值，验证是否会触发破坏性断言失败。
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <el-button size="small" @click="loadValidateSample('normal')">
                                        <i class="fa-solid fa-check"
                                            style="color: #10b981; margin-right: 4px;"></i>载入合规样本
                                    </el-button>
                                    <el-button size="small" type="danger" plain @click="loadValidateSample('breaking')">
                                        <i class="fa-solid fa-bolt" style="margin-right: 4px;"></i>载入破坏性突变样本
                                    </el-button>
                                </div>
                            </div>

                            <el-row :gutter="20">
                                <el-col :span="12">
                                    <div
                                        style="font-size: 13.5px; font-weight: 600; margin-bottom: 8px; color: #334155;">
                                        预期基准契约 (Draft-7 Schema)
                                    </div>
                                    <el-input v-model="labValidateSchemaText" type="textarea" :rows="16"
                                        style="font-family: Consolas, Monaco, monospace; font-size: 12.5px;"
                                        placeholder="粘贴预期 JSON Schema 契约规则...">
                                    </el-input>
                                </el-col>
                                <el-col :span="12">
                                    <div
                                        style="font-size: 13.5px; font-weight: 600; margin-bottom: 8px; color: #334155;">
                                        待测试演进数据 (模拟新版本响应 JSON)
                                    </div>
                                    <el-input v-model="labValidateJsonText" type="textarea" :rows="16"
                                        style="font-family: Consolas, Monaco, monospace; font-size: 12.5px;"
                                        placeholder="粘贴待测试接口实际返回的 JSON 样本...">
                                    </el-input>
                                </el-col>
                            </el-row>

                            <div style="margin-top: 16px; display: flex; justify-content: center;">
                                <el-button type="primary" size="large" @click="handleLabValidate"
                                    :loading="labValidating" style="padding: 12px 32px; font-weight: 600;">
                                    <i class="fa-solid fa-magnifying-glass-chart"
                                        style="margin-right: 8px;"></i>执行破坏性变更比对校验
                                </el-button>
                            </div>

                            <!-- 校验报告展示区 -->
                            <div v-if="labValidationResult" style="margin-top: 24px;">
                                <el-alert v-if="labValidationResult.valid" title="契约校验通过: 未检测到破坏性变更" type="success"
                                    description="待测 JSON 完全符合基准契约定义的字段要求与数据类型，下游消费方无兼容性风险。" show-icon :closable="false">
                                </el-alert>
                                <div v-else>
                                    <el-alert
                                        :title="`警告: 检测到 ${labValidationResult.error_count} 处契约破坏性变更 (Breaking Changes)`"
                                        type="error" description="新版本数据结构违反了已约定的契约规范，将导致下游反序列化失败或业务逻辑崩溃！" show-icon
                                        :closable="false" style="margin-bottom: 12px;">
                                    </el-alert>
                                    <el-table :data="labValidationResult.errors" border stripe size="small"
                                        style="width: 100%;">
                                        <el-table-column type="index" label="#" width="60"
                                            align="center"></el-table-column>
                                        <el-table-column prop="field" label="受损字段路径" width="180">
                                            <template #default="{ row }">
                                                <el-tag size="small" type="danger" effect="plain"
                                                    style="font-family: monospace;">
                                                    {{ row.field || 'root' }}
                                                </el-tag>
                                            </template>
                                        </el-table-column>
                                        <el-table-column prop="validator" label="违反校验规则" width="160">
                                            <template #default="{ row }">
                                                <el-tag size="small" type="warning">
                                                    {{ row.validator }}
                                                </el-tag>
                                            </template>
                                        </el-table-column>
                                        <el-table-column prop="message" label="破坏性变更详情" min-width="300">
                                            <template #default="{ row }">
                                                <span
                                                    style="color: #b91c1c; font-family: monospace; font-size: 12.5px;">
                                                    {{ row.message }}
                                                </span>
                                            </template>
                                        </el-table-column>
                                    </el-table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
</template>

<script>
import { inject } from 'vue'

// 共享工作台全局上下文 (后续可收敛为领域 composables)
export default {
    name: 'SchemaLabView',
    setup() {
        return inject('workbench')
    }
}
</script>
