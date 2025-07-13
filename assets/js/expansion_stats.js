document$.subscribe(async () => {
    const names = ["formatter", "math", "randomcolor", "shortcut"];
    
    const formatterStats = document.querySelector('[data-md-component="expansion-formatter"]');
    const mathStats = document.querySelector('[data-md-component="expansion-math"]');
    const randomcolorStats = document.querySelector('[data-md-component="expansion-randomcolor"]');
    const shortcutStats = document.querySelector('[data-md-component="expansion-shortcut"]');
    
    async function loadFormatterData(data) {
        const count = data["formatter"];
        
        formatterStats.textContent = `The Formatter expansion is used on ${count} Servers.`;
    }
    
    async function loadMathStats(data) {
        const count = data["math"];
        
        mathStats.textContent = `The Math expansion is used on ${count} Servers.`;
    }
    
    async function loadRandomcolorStats(data) {
        const count = data["randomcolor"];
        
        randomcolorStats.textContent = `The RandomColor expansion is used on ${count} Servers.`;
    }
    
    async function loadShortcutStats(data) {
        const count = data["shortcut"];
        
        shortcutStats.textContent = `The Shortcut expansion is used on ${count} Servers.`;
    }
    
    async function loadStats(target) {
        const json = await fetch("https://bstats.org/api/v1/plugins/438/charts/expansions_used/data").then(_ => _.json());
        
        data = {}
        for(let i = 0; i < json.length; i++){
            const d = json[i];
            
            if(names.includes(d["name"])){
                data[d["name"]] = d["y"];
            }
        }
        
        __md_set("__expansion_stats", data, sessionStorage);
        
        if (target == "formatter") {
            loadFormatterData(data);
        }else
        if (target == "math") {
            loadMathStats(data);
        }else
        if (target == "randomcolor") {
            loadRandomcolorStats(data);
        }else
        if (target == "shortcut") {
            loadShortcutStats(data);
        }
    }
    
    if (document.querySelector('[data-md-component="expansion-formatter"]')) {
        const cache = __md_get("__expansion_stats", sessionStorage);
        if ((cache != null) && cache["formatter"]) {
            loadFormatterData(cache);
        } else {
            loadStats("formatter");
        }
    }
    
    if (document.querySelector('[data-md-component="expansion-math"]')) {
        const cache = __md_get("__expansion_stats", sessionStorage);
        if ((cache != null) && cache["math"]) {
            loadMathStats(cache);
        } else {
            loadStats("math");
        }
        
    }
    
    if (document.querySelector('[data-md-component="expansion-randomcolor"]')) {
        const cache = __md_get("__expansion_stats", sessionStorage);
        if ((cache != null) && cache["randomcolor"]) {
            loadRandomcolorStats(cache);
        } else {
            loadStats("randomcolor");
        }
        
    }
    
    if (document.querySelector('[data-md-component="expansion-shortcut"]')) {
        const cache = __md_get("__expansion_stats", sessionStorage);
        if ((cache != null) && cache["shortcut"]) {
            loadShortcutStats(cache);
        } else {
            loadStats("shortcut");
        }
        
    }
})