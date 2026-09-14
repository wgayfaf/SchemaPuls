/**
 * SchemaPulse - 前端独立工程全局配置
 * 
 * 适用于前后端分离架构：
 * - 本地独立运行（默认 http://127.0.0.1:8000）
 * - 生产 Nginx 反向代理或远程云端 API 部署
 */
window.SCHEMA_PULSE_CONFIG = {
    // 后端 RESTful API 基础访问地址 (末尾不要带斜杠)
    API_BASE_URL: window.API_BASE_URL || "http://127.0.0.1:8000"
};

// 暴露全局便捷变量供全局与调试使用
window.API_BASE_URL = window.SCHEMA_PULSE_CONFIG.API_BASE_URL;
