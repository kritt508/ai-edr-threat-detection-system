// 1. ดึงข้อมูลจากโหนด Extract (ตรวจสอบชื่อโหนดให้ตรงกับใน Workflow ของคุณนะครับ)
let processData = "";
let networkData = "";

try {
    processData = $items("Extract from File2")[0].json.data || "";
    networkData = $items("Extract from File3")[0].json.data || "";
} catch (e) {
    processData = "No Strace Data Found";
    networkData = "No Network Data Found";
}

// 2. 🛡️ ฟังก์ชันคัดกรองข้อมูลสำคัญ (Linux High-Value Filter)
// จะช่วยดึงเฉพาะ System Calls ที่มัลแวร์ชอบใช้มาให้ AI อ่าน
function filterLinuxLog(logStr) {
    if (!logStr) return "";
    const lines = logStr.split('\n');
    const suspiciousKeywords = [
        "execve", "connect", "bind", "socket", "chmod", "chown", 
        "ptrace", "wget", "curl", "mkdir", "/tmp", "/dev/shm", 
        "rm -rf", "kill", "fork", "vfork", "write", "openat"
    ];
    
    // กรองเอาเฉพาะบรรทัดที่มี Keyword สำคัญ
    const filteredLines = lines.filter(line => 
        suspiciousKeywords.some(kw => line.toLowerCase().includes(kw.toLowerCase()))
    );
    
    return filteredLines.length > 0 ? filteredLines.join('\n') : logStr;
}

// 3. ฟังก์ชันสำหรับตัดข้อมูลที่ยาวเกินไป
function truncateLog(logStr, maxLength) {
    if (!logStr || logStr.length <= maxLength) return logStr;
    const half = Math.floor(maxLength / 2);
    return `${logStr.substring(0, half)}\n\n... [⚠️ LOG TRUNCATED] ...\n\n${logStr.slice(-half)}`;
}

// 4. ประมวลผลข้อมูล (คัดกรองก่อนแล้วค่อยตัด)
let filteredProcess = filterLinuxLog(processData);
let filteredNetwork = filterLinuxLog(networkData);

// จำกัดขนาดส่งให้ AI
processData = truncateLog(filteredProcess, 35000); 
networkData = truncateLog(filteredNetwork, 10000);

// 5. รวมข้อมูลส่งต่อให้ AI Agent
return {
  combined_data: `### LINUX BEHAVIORAL ANALYSIS REPORT ###
[SYSTEM OPERATING: LINUX]

=== STRACE PROCESS LOG (CRITICAL SYSTEM CALLS) ===
${processData || "No suspicious system calls detected."}

=== NETWORK TRAFFIC LOG (TSHARK) ===
${networkData || "No suspicious network activity detected."}`,
  os: "linux"
};