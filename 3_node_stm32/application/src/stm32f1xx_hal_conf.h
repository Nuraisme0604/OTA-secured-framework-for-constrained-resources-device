/**
 * @file stm32f1xx_hal_conf.h
 * @brief STM32F1 HAL Configuration - Manual setup (no CubeMX needed)
 */

#ifndef STM32F1XX_HAL_CONF_H
#define STM32F1XX_HAL_CONF_H

#ifdef __cplusplus
extern "C" {
#endif

/* ============== Module Selection ============== */
#define HAL_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_USART_MODULE_ENABLED

/* ============== Oscillator Values ============== */
#if !defined(HSE_VALUE)
#define HSE_VALUE    8000000U    /* External oscillator 8MHz */
#endif

#if !defined(HSE_STARTUP_TIMEOUT)
#define HSE_STARTUP_TIMEOUT    100U
#endif

#if !defined(HSI_VALUE)
#define HSI_VALUE    8000000U    /* Internal oscillator 8MHz */
#endif

#if !defined(LSE_VALUE)
#define LSE_VALUE    32768U      /* External low speed oscillator */
#endif

#if !defined(LSE_STARTUP_TIMEOUT)
#define LSE_STARTUP_TIMEOUT    5000U
#endif

/* ============== System Configuration ============== */
#define VDD_VALUE                    3300U    /* VDD in mV */
#define TICK_INT_PRIORITY            15U      /* SysTick priority */
#define USE_RTOS                     0U
#define PREFETCH_ENABLE              1U

/* ============== Assert Selection ============== */
/* #define USE_FULL_ASSERT    1U */

/* ============== Include HAL Modules ============== */
#ifdef HAL_RCC_MODULE_ENABLED
#include "stm32f1xx_hal_rcc.h"
#endif

#ifdef HAL_GPIO_MODULE_ENABLED
#include "stm32f1xx_hal_gpio.h"
#endif

#ifdef HAL_DMA_MODULE_ENABLED
#include "stm32f1xx_hal_dma.h"
#endif

#ifdef HAL_CORTEX_MODULE_ENABLED
#include "stm32f1xx_hal_cortex.h"
#endif

#ifdef HAL_FLASH_MODULE_ENABLED
#include "stm32f1xx_hal_flash.h"
#endif

#ifdef HAL_PWR_MODULE_ENABLED
#include "stm32f1xx_hal_pwr.h"
#endif

#ifdef HAL_UART_MODULE_ENABLED
#include "stm32f1xx_hal_uart.h"
#endif

#ifdef HAL_USART_MODULE_ENABLED
#include "stm32f1xx_hal_usart.h"
#endif

/* ============== Assert Macro ============== */
#ifdef USE_FULL_ASSERT
#define assert_param(expr) ((expr) ? (void)0U : assert_failed((uint8_t *)__FILE__, __LINE__))
void assert_failed(uint8_t *file, uint32_t line);
#else
#define assert_param(expr) ((void)0U)
#endif

#ifdef __cplusplus
}
#endif

#endif /* STM32F1XX_HAL_CONF_H */
