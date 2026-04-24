#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    printf("Pinging 8.8.8.8 every 1 second. Press Ctrl+C to stop.\n");

    while (1) {
        // -c 1 sends only one packet per loop
        system("ping -c 1 8.8.8.8");
        
        // Wait for 1 second
        sleep(1);
    }

    return 0;
}
