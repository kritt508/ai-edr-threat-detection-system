// 1. Extract data from nodes (Ensure node names match your workflow)
let processData = "";
let networkData = "";

try {
    processData = $items("Extract from File2")[0].json.data || "";
    networkData = $items("Extract from File3")[0].json.data || "";
} catch (e) {
    processData = "No Strace Data Found";
    networkData = "No Network Data Found";
}

// 2. 🛡️ High-Value Linux Filter Function
// Extracts critical system calls commonly used by malware for AI analysis
function filterLinuxLog(logStr) {
    if (!logStr) return "";
    const lines = logStr.split('\n');
    const suspiciousKeywords = [
        "execve", "connect", "bind", "socket", "chmod", "chown", 
        "ptrace", "wget", "curl", "mkdir", "/tmp", "/dev/shm", 
        "rm -rf", "kill", "fork", "vfork", "write", "openat"
    ];
    
    // Filter lines containing critical keywords
    const filteredLines = lines.filter(line => 
        suspiciousKeywords.some(kw => line.toLowerCase().includes(kw.toLowerCase()))
    );
    
    return filteredLines.length > 0 ? filteredLines.join('\n') : logStr;
}

// 3. Log truncation function
function truncateLog(logStr, maxLength) {
    if (!logStr || logStr.length <= maxLength) return logStr;
    const half = Math.floor(maxLength / 2);
    return `${logStr.substring(0, half)}\n\n... [⚠️ LOG TRUNCATED] ...\n\n${logStr.slice(-half)}`;
}

// 4. Data processing (Filter first, then truncate)
let filteredProcess = filterLinuxLog(processData);
let filteredNetwork = filterLinuxLog(networkData);

// Limit payload size for AI analysis
processData = truncateLog(filteredProcess, 35000); 
networkData = truncateLog(filteredNetwork, 10000);

// 5. Combine data for AI Agent
return {
  combined_data: `### LINUX BEHAVIORAL ANALYSIS REPORT ###
[SYSTEM OPERATING: LINUX]

=== STRACE PROCESS LOG (CRITICAL SYSTEM CALLS) ===
${processData || "No suspicious system calls detected."}

=== NETWORK TRAFFIC LOG (TSHARK) ===
${networkData || "No suspicious network activity detected."}`,
  os: "linux"
};