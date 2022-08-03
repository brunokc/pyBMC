import WebRequest from "./webrequest.js";

(function () {
    const opts = {
        angle: -0.2, // The span of the gauge arc
        lineWidth: 0.2, // The line thickness
        radiusScale: 1, // Relative radius
        pointer: {
        length: 0.6, // // Relative to gauge radius
        strokeWidth: 0.035, // The thickness
        color: '#000000' // Fill color
        },
        limitMax: false,     // If false, max value increases automatically if value > maxValue
        limitMin: false,     // If true, the min value of the gauge will be fixed
        colorStart: '#6F6EA0',   // Colors
        colorStop: '#C0C0DB',    // just experiment with them
        strokeColor: '#EEEEEE',  // to see which ones work best for you
        generateGradient: true,
        highDpiSupport: true,     // High resolution support

        // percentColors: [
        //     [0.0, "#a9d70b" ],
        //     [0.50, "#f9c802"],
        //     [1.0, "#ff0000"]
        // ],
        staticLabels: {
            font: "10px sans-serif",  // Specifies font
            labels: [200, 500, 2100, 2800],  // Print labels at these values
            color: "#000000",  // Optional: Label text color
            fractionDigits: 0  // Optional: Numerical precision. 0=round off.
        },
        staticZones: [
            {strokeStyle: "#F03E3E", min:   0, max: 200}, // Red
            {strokeStyle: "#FFDD00", min: 200, max: 500}, // Yellow
            {strokeStyle: "#30B32D", min: 500, max: 2100}, // Green
            {strokeStyle: "#FFDD00", min: 2100, max: 2800}, // Yellow
            {strokeStyle: "#F03E3E", min: 2800, max: 3000}  // Red
        ],
        // renderTicks: {
        //     divisions: 5,
        //     divWidth: 1.1,
        //     divLength: 0.7,
        //     divColor: "#333333",
        //     subDivisions: 3,
        //     subLength: 0.5,
        //     subWidth: 0.6,
        //     subColor: "#666666"
        // },
    };

    const fanCount = 3;
    let fans = [];

    for (var i = 0; i < fanCount; ++i) {
        var fanId = "fan" + (i + 1);
        var target = document.getElementById(fanId + "-gauge");
        var target_text = document.getElementById(fanId + "-text");
        let gauge = new Gauge(target).setOptions(opts);
        gauge.setTextField(target_text);
        gauge.maxValue = 3000; // set max gauge value
        gauge.setMinValue(0);  // Prefer setter over gauge.minValue = 0
        gauge.animationSpeed = 32; // set animation speed (32 is default value)
        gauge.set(3000); // set actual value

        fans.push({
            gauge: gauge,
            power: document.getElementById(fanId + "-range")
        });
    }

    let startAutoRefreshOnWebSocketConnection = false;

    const wsUri = "ws://" + location.host + "/api/v1/ws";
    let webSocket = null;
    function createWebSocket() {
        console.log("Creating websocket...");
        webSocket = new WebSocket(wsUri);
        webSocket.addEventListener("close", function (event) {
            console.log("onclose");
            document.getElementById("error-message").textContent = "Lost connection to the server. Re-connecting...";
            document.querySelector(".error-block").style.visibility = "visible";
            stopAutoRefresh();
            startAutoRefreshOnWebSocketConnection = true;
            createWebSocket();
        });

        webSocket.addEventListener("error", function (event) {
            console.log("onerror");
            console.log(event);
            document.getElementById("error-message").textContent = "Server connection error";
            document.querySelector(".error-block").style.visibility = "visible";
            // stopAutoRefresh();
            // startAutoRefreshOnWebSocketConnection = true;
            // createWebSocket();
        });

        webSocket.addEventListener("open", function (event) {
            document.querySelector(".error-block").style.visibility = "hidden";
            if (startAutoRefreshOnWebSocketConnection) {
                startAutoRefreshOnWebSocketConnection = false;
                startAutoRefresh();
            }
        });

        webSocket.addEventListener("message", function (event) {
            const data = JSON.parse(event.data);
            switch (data.request) {
                case "getBmcInfo":
                    update_bmc_info(data.response);
                    break;

                case "getBmcStats":
                    update_bmc_stats(data.response);
                    break;

                case "getSystemState":
                    update_system_state(data.response);
                    break;

                default:
                    console.log(`Unrecognized request '${data.request}'`);
                    break;
            }
        });
    }

    createWebSocket();

    async function request_bmc_info() {
        await webSocket.send(JSON.stringify({
            "command": "getBmcInfo"
        }));
    }

    function update_bmc_info(data) {
        const model = document.getElementById("model");
        model.textContent = data.systemInfo.model;

        const totalMem = document.getElementById("totalMem");
        totalMem.textContent = data.systemInfo.totalMem;
    }

    // Throttling Map
    const ThrottlingMap = {
        UnderVoltageDetected: 0x1,
        ArmFrequencyCapped: 0x2,
        CurrentlyThrottled: 0x4,
        SoftTemperatureLimitActive: 0x8,
        UnderVoltageOccurred: 0x10000,
        ArmFrequencyCappingOcurred: 0x20000,
        ThrottlingOcurred: 0x40000,
        SoftTemperatureLimitedOcurred: 0x80000,
    }

    const SECOND_IN_MS = 1000;
    const MINUTE_IN_MS = SECOND_IN_MS * 60;
    const HOUR_IN_MS = MINUTE_IN_MS * 60
    const DAY_IN_MS = HOUR_IN_MS * 24;

    function formatUptime(uptime_msec) {
        let result = [];
        const days = Math.floor(uptime_msec / DAY_IN_MS);
        uptime_msec -= days * DAY_IN_MS;
        if (days > 0) {
            result.push(`${days} day` + (days > 1 ? "s" : ""));
        }

        const hours = Math.floor(uptime_msec / HOUR_IN_MS);
        uptime_msec -= hours * HOUR_IN_MS;
        if (hours > 0) {
            result.push(`${hours} hour` + (hours > 1 ? "s" : ""));
        }

        const minutes = Math.floor(uptime_msec / MINUTE_IN_MS);
        uptime_msec -= minutes * MINUTE_IN_MS;
        if (minutes > 0) {
            result.push(`${minutes} minute` + (minutes > 1 ? "s" : ""));
        }

        const seconds = Math.floor(uptime_msec / SECOND_IN_MS);
        uptime_msec -= seconds * SECOND_IN_MS;
        if (seconds > 0) {
            result.push(`${seconds} second` + (seconds > 1 ? "s": "s"));
        }

        return result.join(", ")
    }

    function applyClassByState(element, classes, state) {
        Object.keys(classes).forEach((s) => {
            if (s == state) {
                classes[s].forEach((c) => element.classList.add(c));
            } else {
                classes[s].forEach((c) => element.classList.remove(c));
            }
        });
    }

    async function request_bmc_stats() {
        console.log("request_bmc_stats");
        await webSocket.send(JSON.stringify({
            "command": "getBmcStats"
        }));
    }

    function update_bmc_stats(data) {
        const cpuTempC = document.getElementById("cpuTempC");
        const cpuTempF = document.getElementById("cpuTempF");
        const tempInF = 32 + data.systemStats.cpuTemp * 9 / 5;
        cpuTempC.textContent = data.systemStats.cpuTemp.toFixed(1);
        cpuTempF.textContent = tempInF.toFixed(1);

        const classes = {
            0: ["bi-check-circle-fill", "text-success"],
            1: ["bi-bell-fill", "text-warning"],
            2: ["bi-exclamation-circle-fill", "text-danger"],
        };

        const isUndervoltage = (data.systemStats.throttled & ThrottlingMap.UnderVoltageDetected);
        const wasUndervoltage = (data.systemStats.throttled & ThrottlingMap.UnderVoltageOccurred);
        const undervoltage = document.getElementById("under-voltage");
        applyClassByState(undervoltage, classes, (isUndervoltage ? 2 : (wasUndervoltage ? 1 : 0)));

        const isFrequencyLimited = (data.systemStats.throttled & ThrottlingMap.ArmFrequencyCapped);
        const wasFrequencyLimited = (data.systemStats.throttled & ThrottlingMap.ArmFrequencyCappingOcurred);
        const frequencyLimited = document.getElementById("frequency-capped");
        applyClassByState(frequencyLimited, classes, (isFrequencyLimited ? 2 : (wasFrequencyLimited ? 1 : 0)));

        const isThrottled = (data.systemStats.throttled & ThrottlingMap.CurrentlyThrottled);
        const wasThrottled = (data.systemStats.throttled & ThrottlingMap.ThrottlingOcurred);
        const throttled = document.getElementById("throttled");
        applyClassByState(throttled, classes, (isThrottled ? 2 : (wasThrottled ? 1 : 0)));

        const isTempLimited = (data.systemStats.throttled & ThrottlingMap.SoftTemperatureLimitActive);
        const wasTempLimited = (data.systemStats.throttled & ThrottlingMap.SoftTemperatureLimitedOcurred);
        const softTempLimited = document.getElementById("soft-temp-limited");
        applyClassByState(softTempLimited, classes, (isTempLimited ? 2 : (wasTempLimited ? 1 : 0)));

        const uptime = document.getElementById("uptime");
        uptime.textContent = formatUptime(data.systemStats.uptime * 1000);
    }

    let fakePowerState = false;
    let fakePowerOk = true;
    async function request_system_state() {
        console.log("request_system_state");
        await webSocket.send(JSON.stringify({
            "command": "getSystemState"
        }));
    }

    function update_system_state(state) {
        for (var i = 0; i < state.fans.length; ++i) {
            const fan = state.fans[i];
            fans[i].gauge.set(fan.rpm);
            fans[i].power.value = fan.dutyCycle;
        }

        const tempC = document.getElementById("tempC");
        const tempF = document.getElementById("tempF");
        const tempInF = 32 + state.tempSensor.temperatureC * 9 / 5;
        tempC.textContent = state.tempSensor.temperatureC.toFixed(1);
        tempF.textContent = tempInF.toFixed(1);

        const humidity = document.getElementById("humidity");
        humidity.textContent = state.tempSensor.humidity.toFixed(1);

        const powerButton = document.getElementById("power-button");
        const powerState = document.getElementById("power-state");
        // if (state.psu.powerState) {
        if (fakePowerState) {
            powerState.textContent = "On";
            powerState.dataset.value = true;
            powerState.classList.add("text-success");
            powerButton.classList.replace("btn-success", "btn-danger");
        } else {
            powerState.textContent = "Off";
            powerState.dataset.value = false;
            powerState.classList.remove("text-success");
            powerButton.classList.replace("btn-danger", "btn-success");
        }

        const powerOk = document.getElementById("power-ok");
        // if (state.psu.powerState && state.psu.powerOk) {
        if (fakePowerState && fakePowerOk) {
            powerOk.textContent = "Yes";
            powerOk.classList.remove("text-danger");
            powerOk.classList.add("text-success");
        } else {
            powerOk.classList.remove("text-success");
            // if (state.psu.powerState) {
            if (fakePowerState) {
                powerOk.innerHTML = "<i class='bi bi-exclamation-triangle-fill'></i>No";
                powerOk.classList.add("text-danger");
            } else {
                powerOk.textContent = "Off";
                powerOk.classList.remove("text-danger", "text-success");
            }
        }
    }

    const speedControls = document.getElementsByClassName("fan-speed-control");
    Array.from(speedControls).forEach((el) => {
        // For some reason, when the fan speed range text changes from 100% (the initial value) to
        // its new value < 100%, that causes the containing div (.fan-speed-box) to get smaller,
        // which causes contents to shift ever so slightly, which is very annoying. I wanted to set
        // the min-width of the fan-speed-box div to whatever the width value is at load time
        // which is the case of when "100%" is displayed. I couldn't get it to work though -- I tried
        // setting min-width to min-content, max-content, fit-content(100%), nothing seemed to work.
        // I'm left with JavaScript as my only option, which seems to work fine.
        const box = el.parentElement.parentElement;
        box.style.minWidth = box.clientWidth + "px";

        el.addEventListener("input", (event) => {
            const fanId = el.dataset.fanId;
            const rangeControlId = `fan${fanId}-range`;
            const rangeControl = document.getElementById(rangeControlId);
            rangeControl.textContent = el.value + "%";
        });
    });

    const autoRefresh = document.getElementById("auto-refresh-switch");
    let bmcIntervalToken = null;
    let fanIntervalToken = null;
    function startAutoRefresh() {
        setTimeout(() => {
            request_bmc_info();
            request_bmc_stats();
            request_system_state();
            bmcIntervalToken = setInterval(request_bmc_stats, 1000);
            fanIntervalToken = setInterval(request_system_state, 250);
        }, 600);
    }

    function stopAutoRefresh() {
        clearInterval(bmcIntervalToken);
        bmcIntervalToken = null;
        clearInterval(fanIntervalToken);
        fanIntervalToken = null;
    }

    autoRefresh.addEventListener("change", (event) => {
        if (event.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });

    if (autoRefresh.checked) {
        startAutoRefresh();
    }

    function toBool(v) {
        return (typeof v === "boolean" && v) ||
            (typeof v === "number" && v !== 0) ||
            (typeof v === "string" && (
                v.toLowerCase() === "true" ||
                v.toLowerCase() === "on" ||
                v.toLowerCase() === "1")
            );
    }

    async function togglePowerState() {
        const powerState = document.getElementById("power-state");
        const powerButton = document.getElementById("power-button");
        const newValue = !toBool(powerState.dataset.value);
        console.log("newValue = " + newValue);
        const stateUri = location.origin + "/api/v1/psu";
        // const response = await patchRequest(url, { "powerState": value });
        // if (response.status === 204) {
        if (newValue) {
            powerButton.classList.replace("btn-success", "btn-danger");
            fakePowerState = true;
        } else {
            powerButton.classList.replace("btn-danger", "btn-success");
            fakePowerState = false;
        }

        powerState.dataset.value = newValue;
    }

    const powerButton = document.getElementById("power-button");
    powerButton.addEventListener("click", (event) => {
        togglePowerState();
    });
})();