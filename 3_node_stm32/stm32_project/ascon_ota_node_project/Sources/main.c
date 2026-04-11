/**
 * @file main.c
 * @brief ASCON-CRA OTA Node Main Application
 * 
 * STM32F103C8 Blue Pill
 * - UART1: Communication with ESP32 Gateway
 * - PC13: Onboard LED
 */

#include <stdint.h>
#include "stm32f1xx_hal.h"
#include "system_init.h"

/* Include OTA handler when ready */
#include "ota_handler.h"

int main(void)
{
    /* Initialize system: Clock 72MHz, GPIO, UART */
    System_Init();
    
    /* Initialize OTA handler */
    ota_handler_init();
    
    /* Main loop */
    while (1)
    {
        /* Toggle LED every 500ms for heartbeat */
        System_ToggleLED();
        
        /* Check if OTA is active to speed up polling? */
        /* if (ota_is_active()) { HAL_Delay(10); } else { HAL_Delay(500); } */
        HAL_Delay(100); 
        
        /* Poll UART for new data */
        /* Note: Actual implementation depends on how UART interrupt/DMA is set up in system_init.c */
        /* For now, we assume a simple polling or flag check */
        
        /* Example:
        if (uart_data_available()) {
            packet_t pkt;
            if (uart_receive_packet(&pkt)) {
                ota_process_packet(&pkt);
            }
        }
        */
    }
}
