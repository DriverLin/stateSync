import { useEffect, useRef, useState } from "react"
import ReconnectingWebSocket from "reconnecting-websocket"



const INIT = 0
const READY = 1
const WAITING = 2

const SET_KV = 0
const DEL_K = 1
const SYNC_ALL = 2
const LOAD = 3

export default function useSyncDict(wsUrl) {
    const [data, setData] = useState({})
    const version = useRef(-1)
    const state = useRef(INIT)
    const ws = useRef(null)
    useEffect(() => {
        if (ws.current) return;
        const onmessage = (event) => {
            const recv = JSON.parse(event.data);
            // console.log(recv)
            if (state.current === READY) {
                if (recv.current === version.current) {
                    version.current = recv.next;
                    if (recv.action === SET_KV) {//set
                        setData(data => ({ ...data, [recv.key]: recv.value }))
                    } else if (recv.action === DEL_K) {//delete
                        setData(data => ({ ...data, [recv.key]: undefined }))
                    } else if (recv.action === LOAD) {
                        setData(recv.data)
                    }
                } else {
                    state.current = WAITING;
                    ws.current.send("sync")
                }
            } else {
                if (recv.action === SYNC_ALL) {//sync all
                    version.current = recv.next
                    setData(recv.data)
                    state.current = READY;
                }
            }
        }
        const onopen = () => {
            ws.current.send("sync")
        }
        ws.current = new ReconnectingWebSocket(wsUrl, [], {
            maxReconnectionDelay: 100,
        })
        ws.current.addEventListener("message", onmessage)
        ws.current.addEventListener("open", onopen)
        return () => {
            if (ws.current && ws.current.readyState === 1) {
                ws.current.close()
            }
        }
    }, [])
    return data
}