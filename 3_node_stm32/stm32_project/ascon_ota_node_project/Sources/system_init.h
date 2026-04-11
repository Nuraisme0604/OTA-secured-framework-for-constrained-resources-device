/**
 * @file system_init.h
 * @brief System initialization header
 */

#ifndef SYSTEM_INIT_H
#define SYSTEM_INIT_H

#include "stm32f1xx_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize all system peripherals (clock, GPIO, UART)
 */
void System_Init(void);

/**
 * @brief Get UART handle for OTA communication
 */
UART_HandleTypeDef* System_GetUART(void);

/**
 * @brief Toggle onboard LED (PC13)
 */
void System_ToggleLED(void);

#ifdef __cplusplus
}
#endif

#endif /* SYSTEM_INIT_H */
