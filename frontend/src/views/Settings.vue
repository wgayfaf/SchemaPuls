<template>
                <div v-show="currentNav === 'settings'">
                    <div class="wb-card">
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">
                            <i class="fa-solid fa-envelope-open-text"
                                style="color: #10b981; margin-right: 8px;"></i>SMTP 邮件与告警参数说明
                        </div>
                        <p style="font-size: 13px; color: var(--text-muted); line-height: 1.8;">
                            系统底层已内置全套异步非阻塞 SMTP 邮件发信服务与专业的富文本 HTML 告警卡片。<br>
                            未配置系统环境变量时，产生的告警与恢复通告将在控制台自动进行真实格式模拟；<br>
                            如需外发真实邮件，可在后端运行环境中设置如下环境变量：
                        </p>
                        <pre
                            style="background: #f8fafc; padding: 14px; border-radius: 6px; font-size: 13px; color: #0369a1; margin: 16px 0; border: 1px solid #e2e8f0;">
export SMTP_HOST="smtp.qq.com"
export SMTP_PORT="465"
export SMTP_USER="your_email@qq.com"
export SMTP_PASSWORD="your_smtp_auth_token"
export SMTP_USE_SSL="true"
                        </pre>
                    </div>
                </div>
</template>

<script>
import { inject } from 'vue'

// 共享工作台全局上下文 (后续可收敛为领域 composables)
export default {
    name: 'SettingsView',
    setup() {
        return inject('workbench')
    }
}
</script>
