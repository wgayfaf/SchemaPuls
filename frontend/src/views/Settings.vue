<template>
                <div v-show="currentNav === 'settings'">
                    <div class="wb-card">
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">
                            <i class="fa-solid fa-envelope-open-text"
                                style="color: #10b981; margin-right: 8px;"></i>SMTP 邮件告警配置
                        </div>
                        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
                            配置发信邮箱后，机器离线 / 恢复时将自动向机器节点上填写的告警邮箱发送邮件通知。
                        </p>

                        <el-form label-width="110px" style="max-width: 560px;">
                            <el-form-item label="SMTP 服务器">
                                <el-input v-model="smtpForm.host" placeholder="如: smtp.qq.com" />
                            </el-form-item>
                            <el-form-item label="端口">
                                <el-input-number v-model="smtpForm.port" :min="1" :max="65535" />
                                <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">
                                    SSL 常用 465，STARTTLS 常用 587
                                </span>
                            </el-form-item>
                            <el-form-item label="发件人邮箱">
                                <el-input v-model="smtpForm.user" placeholder="如: your_name@qq.com" />
                            </el-form-item>
                            <el-form-item label="授权码">
                                <el-input v-model="smtpForm.password" type="password" show-password
                                    :placeholder="passwordSet ? '已保存 (留空则不修改)' : '邮箱 SMTP 授权码 (非登录密码)'" />
                            </el-form-item>
                            <el-form-item label="SSL 加密">
                                <el-switch v-model="smtpForm.useSsl" />
                            </el-form-item>
                            <el-form-item>
                                <el-button type="primary" :loading="saving" @click="saveSmtp">
                                    保存配置
                                </el-button>
                            </el-form-item>
                        </el-form>

                        <el-divider style="max-width: 560px;" />

                        <div style="max-width: 560px;">
                            <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">
                                <i class="fa-solid fa-paper-plane" style="color: #6366f1; margin-right: 6px;"></i>发送测试邮件
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <el-input v-model="testReceiver" placeholder="填写你的收件邮箱" style="max-width: 320px;" />
                                <el-button type="success" :loading="testing" @click="sendTest">发送测试</el-button>
                            </div>
                        </div>
                    </div>

                    <div class="wb-card" style="margin-top: 14px;">
                        <div style="font-size: 14px; font-weight: 600; margin-bottom: 10px;">
                            <i class="fa-solid fa-circle-info" style="color: #64748b; margin-right: 6px;"></i>告警触发规则
                        </div>
                        <p style="font-size: 13px; color: var(--text-muted); line-height: 1.9;">
                            · 告警仅针对<b>机器节点</b>：连续失败达到 <b>retry_threshold</b>（默认 3）次后发送 🚨 告警邮件<br>
                            · 机器恢复上线后自动发送 🟢 恢复通知邮件<br>
                            · 防抖：同一机器 <b>silence_minutes</b>（默认 30 分钟）内不重复发送<br>
                            · 收件人在「机器管理 → 编辑机器 → 告警通知邮箱」中配置，多个邮箱用逗号隔开
                        </p>
                    </div>
                </div>
</template>

<script setup>
// SMTP 配置为设置页私有状态, 不与其它视图共享, 采用组件内自管理模式
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { inject } from 'vue'
import { ElMessage } from 'element-plus'

const currentNav = inject('workbench').currentNav

const smtpForm = ref({
    host: 'smtp.qq.com',
    port: 465,
    user: '',
    password: '',
    useSsl: true
})
const passwordSet = ref(false)
const saving = ref(false)
const testing = ref(false)
const testReceiver = ref('')

const loadConfig = async () => {
    try {
        const res = await axios.get('/api/settings/smtp')
        smtpForm.value.host = res.data.smtp_host
        smtpForm.value.port = res.data.smtp_port
        smtpForm.value.user = res.data.smtp_user
        smtpForm.value.useSsl = res.data.smtp_use_ssl
        passwordSet.value = res.data.password_set
    } catch (err) {
        ElMessage.error('读取 SMTP 配置失败: ' + (err.response?.data?.detail || err.message))
    }
}

const saveSmtp = async () => {
    if (!smtpForm.value.user) {
        ElMessage.warning('请填写发件人邮箱')
        return
    }
    saving.value = true
    try {
        await axios.put('/api/settings/smtp', {
            smtp_host: smtpForm.value.host,
            smtp_port: smtpForm.value.port,
            smtp_user: smtpForm.value.user,
            smtp_password: smtpForm.value.password,   // 留空表示保留原密码
            smtp_use_ssl: smtpForm.value.useSsl
        })
        ElMessage.success('SMTP 配置已保存')
        smtpForm.value.password = ''                  // 清空明文, 避免回显
        await loadConfig()
    } catch (err) {
        ElMessage.error('保存失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        saving.value = false
    }
}

const sendTest = async () => {
    testing.value = true
    try {
        await axios.post('/api/settings/smtp/test', { receiver: testReceiver.value })
        ElMessage.success('测试邮件已发送，请查收')
    } catch (err) {
        ElMessage.error('发送失败: ' + (err.response?.data?.detail || err.message))
    } finally {
        testing.value = false
    }
}

onMounted(loadConfig)
</script>
