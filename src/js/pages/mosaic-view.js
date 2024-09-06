import { WebsocketClient } from "../modules/ws-service-client"

(function () {
    console.log("Am in the function!")
    const locationName = document.documentElement.dataset.locationname
    const camera = window.APP_DATA.camera || {}
    const date = window.APP_DATA.date || ''
    const ws = new WebsocketClient()
    ws.subscribe('service', 'camera', locationName, camera.name)
    camera.mosaic_view_meta.forEach((view) => {
        console.log('Subscribing to:', view.channel)
        ws.subscribe('service', 'channel', locationName, camera.name, view.channel)
    })
})()

