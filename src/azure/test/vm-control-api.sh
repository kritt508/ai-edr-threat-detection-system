#!/bin/bash

VERSION="1.6.8"

SUB_ID="cb69e37f-0359-486c-ae60-bb7d1dee3934"
API_VERSION="2023-09-01"
DISK_API_VERSION="2023-10-02"

ACTION=$1      # start, stop, status, snapshot, restore, list-snaps, delete-snap
TARGET_VM=$2   # win, linux, or custom name

show_help() {
    echo "========================================================="
    echo "  Azure VM Sandbox Control Script"
    echo "========================================================="
    echo "Usage: ./vm-control-api.sh [action] [vm_name/custom_name]"
    echo ""
    echo "Supported Actions:"
    echo "  start       : Start the virtual machine (with timer)"
    echo "  stop        : Deallocate the VM (Stops billing, with timer)"
    echo "  status      : Check current Power State"
    echo "  snapshot    : Stop VM and create/overwrite a snapshot"
    echo "  restore     : Stop VM and swap to a fresh disk from snapshot"
    echo "  list-snaps  : List all snapshots in the resource group"
    echo "  delete-snap : Delete a specific snapshot"
    echo ""
    echo "Target VM (Optional):"
    echo "  win         : Windows VM (win2 group)"
    echo "  linux       : Linux VM (Docker group)"
    echo "  [name]      : Custom snapshot name (for delete-snap)"
    echo "  (empty)     : Run on BOTH VMs"
    echo "========================================================="
}

run_azure_api() {
    local VM_TYPE=$1; local RG=$2; local NAME=$3; local CMD=$4
    local TOKEN=$(./get-token.sh)

    local SNAP_NAME=$5
    if [ -z "$SNAP_NAME" ]; then
        SNAP_NAME="snapshot-${NAME}"
    fi

    case "$CMD" in
        start)
            echo "--- Starting $VM_TYPE ($NAME) ---"
            DATE=$(date +%s)
            echo "$DATE: Sending start request for $VM_TYPE ($NAME)..."
            START_TIMER=$(date +%s)
            
            # ส่งคำสั่ง Start
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/start?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null

            echo -n "Waiting for VM to start..."
            while true; do
                CURRENT_STATUS=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/instanceView?api-version=$API_VERSION" \
                     -H "Authorization: Bearer $TOKEN" | jq -r '.statuses[] | select(.code | startswith("PowerState/")) | .displayStatus')
                
                if [[ "$CURRENT_STATUS" == "VM running" ]]; then
                    echo " Done."
                    break
                fi
                echo -n "."
                sleep 5
            done
            
            # --- ส่วนที่เพิ่ม: HTTP Health Check (Port 5000) ---
            local SVC_URL=""
            [[ "$NAME" == "win" ]] && SVC_URL="http://win.sandbox.npu.world:5000/status"
            [[ "$NAME" == "CPE-Docker" ]] && SVC_URL="http://linux.sandbox.npu.world:5000/status"

            if [ -n "$SVC_URL" ]; then
                echo -n "Waiting for Service Online ($SVC_URL)..."
                while true; do
                    HTTP_RES=$(curl -s --max-time 2 "$SVC_URL")
                    SVC_STATUS=$(echo "$HTTP_RES" | jq -r '.status' 2>/dev/null)
                    if [[ "$SVC_STATUS" == "online" ]]; then
                        echo " Online!"
                        echo "Service Version: $(echo "$HTTP_RES" | jq -r '.version')"
                        break
                    fi
                    echo -n "."
                    sleep 5
                done
            fi
            # -----------------------------------------------

            END_TIMER=$(date +%s)
            DURATION=$((END_TIMER - START_TIMER))
            echo "$END_TIMER Success: $VM_TYPE ($NAME) is now running! (Took $DURATION seconds)"
            ;;
            
        stop)
            echo "--- Deallocating $VM_TYPE ($NAME) ---"
            DATE=$(date +%s)
            echo "$DATE: Sending deallocate request for $VM_TYPE ($NAME)..."
            START_TIMER=$(date +%s)
            
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/deallocate?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null
                 
            echo -n "Waiting for VM to deallocate..."
            while true; do
                CURRENT_STATUS=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/instanceView?api-version=$API_VERSION" \
                     -H "Authorization: Bearer $TOKEN" | jq -r '.statuses[] | select(.code | startswith("PowerState/")) | .displayStatus')
                
                if [[ "$CURRENT_STATUS" == "VM deallocated" ]]; then
                    echo " Done."
                    break
                fi
                echo -n "."
                sleep 5
            done
            
            END_TIMER=$(date +%s)
            DURATION=$((END_TIMER - START_TIMER))
            echo "$END_TIMER Success: $VM_TYPE ($NAME) is now deallocated! (Took $DURATION seconds)"
            ;;
            
        status)
            echo -n "$VM_TYPE ($NAME): "
            DATE=$(date +%s)
            echo "$DATE"
            curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/instanceView?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" | jq -r '.statuses[] | select(.code | startswith("PowerState/")) | .displayStatus'
            ;;
        snapshot)
            echo "--- Creating/Updating Frozen Snapshot: $SNAP_NAME ---"
            DATE=$(date +%s)
            echo "$DATE:  Creating/Updating Frozen Snapshot: $SNAP_NAME"
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/deallocate?api-version=$API_VERSION" -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null

            VM_INFO=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" -H "Authorization: Bearer $TOKEN")
            DISK_ID=$(echo "$VM_INFO" | jq -r '.properties.storageProfile.osDisk.managedDisk.id')
            LOC=$(echo "$VM_INFO" | jq -r '.location')

            curl -X PUT -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_NAME?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                 -d "{\"location\":\"$LOC\",\"properties\":{\"creationData\":{\"createOption\":\"Copy\",\"sourceResourceId\":\"$DISK_ID\"}}}" | jq -r '.properties.provisioningState'
            ;;
        restore)
            echo "--- Restoring $NAME from Frozen Snapshot: $SNAP_NAME ---"
            DATE=$(date +%s)
            echo "$DATE: Restoring $NAME from Frozen Snapshot: $SNAP_NAME"
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/deallocate?api-version=$API_VERSION" -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null

            echo "$DATE: 2. Get Metadata & Old Disk ID "
            VM_DATA=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" -H "Authorization: Bearer $TOKEN")
            LOC=$(echo "$VM_DATA" | jq -r '.location')
            OLD_DISK_ID=$(echo "$VM_DATA" | jq -r '.properties.storageProfile.osDisk.managedDisk.id')

            NEW_DISK="disk-restore-${NAME}-$(date +%s)"
            echo "$DATE: Use timestamp to ensure unique disk name "
            SNAP_ID="/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_NAME"

            echo "$DATE: Step 1: Cloning Snapshot to New Disk ($NEW_DISK)..."
            curl -X PUT -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/disks/$NEW_DISK?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                 -d "{\"location\":\"$LOC\",\"properties\":{\"creationData\":{\"createOption\":\"Copy\",\"sourceResourceId\":\"$SNAP_ID\"}}}" > /dev/null

            echo "$DATE: Step 2: Swapping OS Disk..."
            SWAP_RESULT=$(curl -X PATCH -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                 -d "{\"properties\":{\"storageProfile\":{\"osDisk\":{\"managedDisk\":{\"id\":\"/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/disks/$NEW_DISK\"}}}}}")

            echo -n "$DATE: Waiting for Swap to complete..."
            while true; do
                CURRENT_STATE=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" \
                    -H "Authorization: Bearer $TOKEN" | jq -r '.properties.provisioningState')

                if [[ "$CURRENT_STATE" == "Succeeded" ]]; then
                    echo " Done."
                    break
                elif [[ "$CURRENT_STATE" == "Failed" ]]; then
                    echo " Error: Swap failed."
                    exit 1
                fi
                echo -n "."
                sleep 5
            done
            echo -n "$DATE: Finished for Swap to complete..."

            STATE=$(echo "$SWAP_RESULT" | jq -r '.properties.provisioningState')
            echo "Swap Status: $STATE"

            echo "$DATE: Step 3: Cleaning up old disk to save costs..."
            curl -X DELETE -s "https://management.azure.com$OLD_DISK_ID?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN"
            echo "Old disk ($OLD_DISK_ID) deleted."
            ;;
        list-snaps)
            echo "--- Snapshots in $RG ---"
            DATE=$(date +%s)
            echo "$DATE:  Snapshots in $RG "
            curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" | jq -r '.value[] | "Name: \(.name) | Created: \(.properties.timeCreated)"'
            ;;
        delete-snap)
            echo "--- Deleting Snapshot: $SNAP_NAME from $RG ---"
            DATE=$(date +%s)
            echo "$DATE:  Deleting Snapshot: $SNAP_NAME from $RG  "
            curl -X DELETE -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_NAME?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN"
            echo "Request sent."
            ;;
    esac
}

# Validation Logic
if [[ -z "$ACTION" || "$ACTION" == "-h" || "$ACTION" == "--help" ]]; then
    show_help ; exit 0
fi

valid_actions=("start" "stop" "status" "snapshot" "restore" "list-snaps" "delete-snap")
if [[ ! " ${valid_actions[@]} " =~ " ${ACTION} " ]]; then
    echo "Error: Action '$ACTION' is not supported." ; show_help ; exit 1
fi

# Execution Logic
if [[ "$TARGET_VM" == "win" ]]; then
    run_azure_api "Windows" "win2" "win" "$ACTION"
elif [[ "$TARGET_VM" == "linux" ]]; then
    run_azure_api "Linux" "Docker" "CPE-Docker" "$ACTION"
elif [[ -n "$TARGET_VM" ]]; then
    run_azure_api "Custom" "win2" "win" "$ACTION" "$TARGET_VM"
    run_azure_api "Custom" "Docker" "CPE-Docker" "$ACTION" "$TARGET_VM"
else
    run_azure_api "Windows" "win2" "win" "$ACTION"
    run_azure_api "Linux" "Docker" "CPE-Docker" "$ACTION"
fi
