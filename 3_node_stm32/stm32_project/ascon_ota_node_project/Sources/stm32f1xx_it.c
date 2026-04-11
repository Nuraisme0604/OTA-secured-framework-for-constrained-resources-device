/**
 * @file stm32f1xx_it.c
 * @brief Interrupt handlers implementation
 */

#include "stm32f1xx_hal.h"
#include "stm32f1xx_it.h"

/* ============== Cortex-M3 Processor Exceptions ============== */

void NMI_Handler(void)
{
    while (1) {}
}

void HardFault_Handler(void)
{
    while (1) {}
}

void MemManage_Handler(void)
{
    while (1) {}
}

void BusFault_Handler(void)
{
    while (1) {}
}

void UsageFault_Handler(void)
{
    while (1) {}
}

void SVC_Handler(void)
{
}

void DebugMon_Handler(void)
{
}

void PendSV_Handler(void)
{
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

/* ============== Peripheral Interrupt Handlers ============== */

extern UART_HandleTypeDef huart1;

void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}
