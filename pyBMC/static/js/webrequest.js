class WebRequest {
    static async get(url, options) {
        const response = await fetch(url, options);
        return response;
    }

    static async patch(url, body, options) {
        const requestOptions = {
            method: "PATCH",
            mode: "cors",
            cache: "no-cache",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        };

        if (options) {
            requestOptions = { ...requestOptions, options };
        }

        const response = await fetch(url, requestOptions);

        return response;
    }
}

export default WebRequest;
