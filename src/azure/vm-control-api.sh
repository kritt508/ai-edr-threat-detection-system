#!/bin/bash

source .env

ACTION=$1
TARGET_VM=$2

# ฟังก์ชันสำหรับดึงเวลาเป็น Unix Timestamp ระดับมิลลิวินาที (13 หลัก)
get_time() {
    # ใช้ python3 ช่วยเนื่องจากคำสั่ง date ในเครื่องไม่รองรับ %N
    local MS=$(python3 -c 'import time; print(int(time.time() * 1000))')
    echo -n "[$MS] "
}

show_help() {
    echo "========================================================="
    echo "  Azure VM Sandbox Control Script v$VERSION"
    echo "========================================================="
    echo "Usage: ./vm-control-api.sh [action] [vm_name/custom_name]"
    echo ""
    echo "Supported Actions:"
    echo "  start       : Start VM and wait for running state"
    echo "  stop        : Deallocate VM (Stop billing)"
    echo "  status      : Check current Power State"
    echo "  snapshot    : Stop VM and create/overwrite snapshot"
    echo "  restore     : Stop VM and swap to fresh disk from snapshot"
    echo "  list-snaps  : List all snapshots in the resource group"
    echo "  delete-snap : Delete a specific snapshot"
    echo "========================================================="
}

wait_for_state() {
    local RG=$1; local NAME=$2; local TOKEN=$3; local TARGET_STATE=$4
    echo -n "$(get_time)Waiting for VM to reach '$TARGET_STATE'..."
    while true; do
        CURRENT_STATUS=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/instanceView?api-version=$API_VERSION" \
             -H "Authorization: Bearer $TOKEN" | jq -r '.statuses[] | select(.code | startswith("PowerState/")) | .displayStatus' 2>/dev/null)

        if [[ "$CURRENT_STATUS" == "$TARGET_STATE" ]]; then
            echo " Done."
            break
        fi
        echo -n "."
        sleep 5
    done
}

run_azure_api() {
    local VM_TYPE=$1; local RG=$2; local NAME=$3; local CMD=$4
    local TOKEN=$(./get-token.sh)
    local SNAP_NAME=$5
    [ -z "$SNAP_NAME" ] && SNAP_NAME="snapshot-${NAME}"

    case "$CMD" in
        start)
            echo "$(get_time)--- Starting $VM_TYPE ($NAME) ---"
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/start?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null
            wait_for_state "$RG" "$NAME" "$TOKEN" "VM running"
            ;;

        stop)
            echo "$(get_time)--- Deallocating $VM_TYPE ($NAME) ---"
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/deallocate?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null
            wait_for_state "$RG" "$NAME" "$TOKEN" "VM deallocated"
            ;;

        status)
            echo -n "$(get_time)$VM_TYPE ($NAME): "
            curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/instanceView?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" | jq -r '.statuses[] | select(.code | startswith("PowerState/")) | .displayStatus'
            ;;

        snapshot)
            SNAP_LATEST="snapshot-${NAME}"
            SNAP_ORIG="snapshot-${NAME}-orig"

            echo "$(get_time)--- Creating/Updating Snapshots for $NAME ---"
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/deallocate?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null
            wait_for_state "$RG" "$NAME" "$TOKEN" "VM deallocated"

            VM_INFO=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" -H "Authorization: Bearer $TOKEN")
            DISK_ID=$(echo "$VM_INFO" | jq -r '.properties.storageProfile.osDisk.managedDisk.id')
            LOC=$(echo "$VM_INFO" | jq -r '.location')

            CHECK_ORIG=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_ORIG?api-version=$DISK_API_VERSION" -H "Authorization: Bearer $TOKEN" | jq -r '.name')

            if [[ "$CHECK_ORIG" == "null" ]]; then
                echo "$(get_time)Original snapshot not found. Creating $SNAP_ORIG..."
                curl -X PUT -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_ORIG?api-version=$DISK_API_VERSION" \
                     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                     -d "{\"location\":\"$LOC\",\"properties\":{\"creationData\":{\"createOption\":\"Copy\",\"sourceResourceId\":\"$DISK_ID\"}}}" > /dev/null
            fi

            echo "$(get_time)Updating latest snapshot: $SNAP_LATEST..."
            curl -X DELETE -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_LATEST?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" > /dev/null

            RAW_RES=$(curl -X PUT -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_LATEST?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                 -d "{\"location\":\"$LOC\",\"properties\":{\"creationData\":{\"createOption\":\"Copy\",\"sourceResourceId\":\"$DISK_ID\"}}}")

            PROV_STATE=$(echo "$RAW_RES" | jq -r '.properties.provisioningState // .error.code')
            echo "$(get_time)Result: $PROV_STATE"
            ;;

        restore)
            echo "$(get_time)--- Restoring $NAME from Snapshot: $SNAP_NAME ---"
            curl -X POST -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME/deallocate?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" > /dev/null
            wait_for_state "$RG" "$NAME" "$TOKEN" "VM deallocated"

            VM_DATA=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" -H "Authorization: Bearer $TOKEN")
            LOC=$(echo "$VM_DATA" | jq -r '.location')
            OLD_DISK_ID=$(echo "$VM_DATA" | jq -r '.properties.storageProfile.osDisk.managedDisk.id')
            SNAP_ID="/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_NAME"
            NEW_DISK="disk-restore-${NAME}-$(date +%s)"

            echo "$(get_time)Step 1: Creating disk $NEW_DISK..."
            curl -X PUT -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/disks/$NEW_DISK?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                 -d "{\"location\":\"$LOC\",\"properties\":{\"creationData\":{\"createOption\":\"Copy\",\"sourceResourceId\":\"$SNAP_ID\"}}}" > /dev/null

            echo "$(get_time)Step 2: Swapping OS Disk..."
            curl -X PATCH -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                 -d "{\"properties\":{\"storageProfile\":{\"osDisk\":{\"managedDisk\":{\"id\":\"/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/disks/$NEW_DISK\"}}}}}" > /dev/null

            while true; do
                PROV=$(curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/virtualMachines/$NAME?api-version=$API_VERSION" \
                    -H "Authorization: Bearer $TOKEN" | jq -r '.properties.provisioningState')
                [[ "$PROV" == "Succeeded" ]] && break
                sleep 5
            done

            echo "$(get_time)Step 3: Deleting old disk $OLD_DISK_ID..."
            curl -X DELETE -s "https://management.azure.com$OLD_DISK_ID?api-version=$DISK_API_VERSION" -H "Authorization: Bearer $TOKEN"
            echo "$(get_time)Restore completed."
            ;;

        list-snaps)
            echo "$(get_time)--- Snapshots in $RG ---"
            curl -X GET -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN" | jq -r '.value[] | "Name: \(.name) | Created: \(.properties.timeCreated)"'
            ;;

        delete-snap)
            echo "$(get_time)--- Deleting Snapshot: $SNAP_NAME ---"
            curl -X DELETE -s "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Compute/snapshots/$SNAP_NAME?api-version=$DISK_API_VERSION" \
                 -H "Authorization: Bearer $TOKEN"
            echo "$(get_time)Delete request sent."
            ;;
    esac
}

# Execution Logic
if [[ -z "$ACTION" ]]; then show_help; exit 0; fi

if [[ "$ACTION" == "delete-snap" ]]; then
    if [[ -z "$TARGET_VM" ]]; then
        echo "Error: Please specify the snapshot name to delete."
        exit 1
    fi
    run_azure_api "Custom" "win2" "win" "$ACTION" "$TARGET_VM"
    run_azure_api "Custom" "Docker" "CPE-Docker" "$ACTION" "$TARGET_VM"
elif [[ "$TARGET_VM" == "win" ]]; then
    run_azure_api "Windows" "win2" "win" "$ACTION"
elif [[ "$TARGET_VM" == "linux" ]]; then
    run_azure_api "Linux" "Docker" "CPE-Docker" "$ACTION"
else
    run_azure_api "Windows" "win2" "win" "$ACTION"
    run_azure_api "Linux" "Docker" "CPE-Docker" "$ACTION"
fi
