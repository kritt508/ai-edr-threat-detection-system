const items = $input.all().map(item => item.json);

// 1. Extract target filename
let fileName = "Unknown_Target_File";
try {
    let nodeData = $("OS_identification").first().json || $("Webhook").first().json.body || {};
    fileName = nodeData.filename || nodeData.Filename || nodeData.fileName || "unknown.exe";
} catch (e) {}

let formattedProcessLog = [];
let formattedNetworkLog = [];

const fileNameClean = fileName.toLowerCase();
const fileNameNoExt = fileName.split('.')[0].toLowerCase();

// ==========================================
// SUSPICIOUS KEYWORDS (Focus on Reconnaissance & C2 Commands)
// ==========================================
const suspiciousKeywords = [
    "lsass", "curl", "nslookup", "ping", "whoami", "net ", "tasklist",
    "cmd", "powershell", "wscript", "cscript", "mshta", "rundll32", "regsvr32",
    "schtasks", "wmic", "certutil", "bitsadmin", "reg", "run", "startup",
    "payload", "beacon", "stager", "inject", "temp", "programdata",
    fileNameClean, fileNameNoExt
];

const ignoreList = [
    "procmon", "idle", "tshark", "windowsazure", "waappagent",
    "collectguestlogs", "logonui", "fontdrvhost", "smss.exe", 
    "sppsvc", "searchindexer", "nissrv", "taskhostw"
];

const ignoredOps = ["process profiling", "thread exit", "closefile", "queryopen"];

// Enforce collection of operations indicating malware behavior and connectivity
const criticalOps = [
    "process create", "process exit", "regsetvalue", "regcreatekey",
    "tcp send", "tcp receive", "tcp connect", "udp send", "udp receive",
    "deletefile", "renamefile", "writefile", "createfile"
];

items.forEach(item => {
    if (item["Process Name"] && item["Operation"]) {
        const time = item["Time of Day"] || "";
        const procRaw = item["Process Name"];
        const proc = procRaw.toLowerCase();
        const op = item["Operation"].toLowerCase();
        const path = (item["Path"] || "N/A").toLowerCase();
        const det = (item["Detail"] || "").toLowerCase();

        // Filter Noise
        if (ignoreList.some(noise => proc.includes(noise))) return;
        if (ignoredOps.some(noiseOp => op.includes(noiseOp))) return;

        // Check critical conditions (Keep even if not the main malware, but a command invoked by it)
        const isMainMalware = proc.includes(fileNameClean) || proc.includes(fileNameNoExt);
        const hasSuspiciousKw = suspiciousKeywords.some(k => proc.includes(k) || path.includes(k) || det.includes(k));
        const isCritical = criticalOps.some(k => op.includes(k));

        if (isMainMalware || hasSuspiciousKw || isCritical) {
            formattedProcessLog.push(`Time: ${time} | Proc: ${procRaw} | Op: ${item["Operation"]} | Path: ${item["Path"]} | Det: ${item["Detail"] || ""}`);
        }
    }

    // ==========================================
    // NETWORK LOG FILTER (Focus on C2 Signals)
    // ==========================================
    if (item.row && item.row["0"]) {
        const netLog = item.row["0"];
        const netLogLower = netLog.toLowerCase();
        
        const isNoise = ["168.63.129.16", "169.254.169.254", "azure", "frame.number"].some(n => netLogLower.includes(n));
        if (isNoise) return;

        // Enforce collection of SYN, DNS Query, ICMP Echo (Ping), and external IP communications
        const isC2Signal = netLog.includes("[SYN]") || netLogLower.includes("query") || netLogLower.includes("echo") || !netLog.includes("10.0.0.");

        if (isC2Signal) {
            formattedNetworkLog.unshift(netLog); // Prioritize C2 signals to the top
        } else {
            formattedNetworkLog.push(netLog);
        }
    }
});

function limitLines(logArray, maxLines) {
    if (logArray.length === 0) return "";
    if (logArray.length <= maxLines) return logArray.join('\n');
    const half = Math.floor(maxLines / 2);
    return `${logArray.slice(0, half).join('\n')}\n\n... [⚠️ LOG TRUNCATED] ...\n\n${logArray.slice(-half).join('\n')}`;
}

return {
    combined_data: `### WINDOWS BEHAVIORAL ANALYSIS REPORT ###\n[TARGET FILE: ${fileName}]\n\n=== FILTERED PROCESS LOG ===\n${limitLines(formattedProcessLog, 150) || "No Suspicious Process Data Detected"}\n\n=== FILTERED NETWORK TRAFFIC LOG ===\n${limitLines(formattedNetworkLog, 120) || "No Suspicious Network Traffic Detected"}`,
    os: "windows",
    target_filename: fileName
};