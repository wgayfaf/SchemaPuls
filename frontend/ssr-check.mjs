import { createServer } from 'vite'

const vite = await createServer({
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'error',
    optimizeDeps: { noDiscovery: true, include: [] },
    ssr: { external: ['vue', '@vue/server-renderer', 'element-plus', 'axios', 'echarts'] }
})

try {
    const { default: App } = await vite.ssrLoadModule('/src/App.vue')
    const vueMod = await vite.ssrLoadModule('vue')
    const srMod = await vite.ssrLoadModule('@vue/server-renderer')
    const ElementPlus = (await vite.ssrLoadModule('element-plus')).default

    const { createSSRApp } = vueMod
    const { renderToString } = srMod
    const app = createSSRApp(App)
    app.use(ElementPlus)
    app.config.errorHandler = (err, inst, info) => {
        console.error('[Vue errorHandler]', info)
        console.error(err && err.stack ? err.stack.split('\n').slice(0, 12).join('\n') : err)
        throw err
    }
    const html = await renderToString(app)
    console.log('>>> FULL APP SSR OK, html length =', html.length)
} catch (e) {
    console.error('>>> [SSR Throw]')
    console.error(e && e.stack ? e.stack.split('\n').slice(0, 16).join('\n') : e)
} finally {
    await vite.close()
}
