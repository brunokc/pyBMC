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
        gauge = new Gauge(target).setOptions(opts);
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

    async function update_system() {
        const bmcUri = location.origin + "/api/v1/bmc";
        const response = await fetch(bmcUri);
        const bmc = await response.json();
        // console.log(mc);

        const model = document.getElementById("model");
        model.innerText = bmc.systemInfo.model;

        const totalMem = document.getElementById("totalMem");
        totalMem.innerText = bmc.systemInfo.totalMem;

        const cpuTempC = document.getElementById("cpuTempC");
        const cpuTempF = document.getElementById("cpuTempF");
        const tempInF = 32 + bmc.systemInfo.cpuTemp * 9 / 5;
        cpuTempC.innerText = bmc.systemInfo.cpuTemp.toFixed(1);
        cpuTempF.innerText = tempInF.toFixed(1);

        const throttled = document.getElementById("throttled");
        const wasThrottled = (bmc.systemInfo.throttled & 0x40000);
        if (wasThrottled) {
            throttled.innerText = "Yes";
            throttled.classList.add("text-danger");
        } else {
            throttled.innerText = "No";
            throttled.classList.remove("text-danger");
        }

        const uptime = document.getElementById("uptime");
        uptime.innerText = bmc.systemInfo.uptime;
    }

    async function update_state() {
        const stateUri = location.origin + "/api/v1/state";
        const response = await fetch(stateUri);
        const state = await response.json();
        // console.log(state);

        for (var i = 0; i < state.fans.length; ++i) {
            const fan = state.fans[i];
            fans[i].gauge.set(fan.rpm);
            fans[i].power.value = fan.dutyCycle;
        }

        const tempC = document.getElementById("tempC");
        const tempF = document.getElementById("tempF");
        const tempInF = 32 + state.tempSensor.temperatureC * 9 / 5;
        tempC.innerText = state.tempSensor.temperatureC.toFixed(1);
        tempF.innerText = tempInF.toFixed(1);

        const humidity = document.getElementById("humidity");
        humidity.innerText = state.tempSensor.humidity.toFixed(1);

        const powerState = document.getElementById("power-state");
        if (state.psu.powerState) {
            powerState.innerText = "On";
            powerState.classList.add("text-success");
        } else {
            powerState.innerText = "Off";
            powerState.classList.remove("text-success");
        }

        const powerOk = document.getElementById("power-ok");
        if (state.psu.powerOk) {
            powerOk.innerText = "Yes";
            powerOk.classList.remove("text-danger");
            powerOk.classList.add("text-success");
        } else {
            powerOk.innerText = "No";
            powerOk.classList.remove("text-success");
            if (state.psu.powerState) {
                powerOk.classList.add("text-danger");
            }
        }
    }

    const speedControls = document.getElementsByClassName("fan-speed-control");
    Array.from(speedControls).forEach((el) => {
        el.addEventListener("input", (event) => {
            const fanId = el.dataset.fanId;
            const rangeControlId = `fan${fanId}-range`;
            const rangeControl = document.getElementById(rangeControlId);
            rangeControl.innerText = el.value + '%';
        });
    });

    async function performUpdates() {
        await update_system();
        await update_state();
    }

    const autoRefresh = document.getElementById("auto-refresh-switch");
    let intervalToken = null;
    function startAutoRefresh() {
        setTimeout(() => {
            intervalToken = setInterval(performUpdates, 250);
        }, 200);
    }

    function stopAutoRefresh() {
        clearInterval(intervalToken);
        intervalToken = null;
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

    const powerButton = document.getElementById("power-button");
    powerButton.addEventListener("click", (event) => {
        console.log("Power button pressed: " + event.target.id);
    });
})();
