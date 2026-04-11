/**
 * @file system_init.c
 * @brief System initialization and clock configuration for STM32F103
 */

#include "stm32f1xx_hal.h"

/* ============== Global Variables ============== */
UART_HandleTypeDef huart1;

/* ============== Private Function Prototypes ============== */
static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void Error_Handler(void);

/* ============== System Initialization ============== */

/**
 * @brief Configure system clock to 72 MHz using HSE
 */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* Configure HSE and PLL */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;  /* 8MHz * 9 = 72MHz */
    
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    /* Configure clock dividers */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;  /* APB1 = 36MHz max */
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;  /* APB2 = 72MHz */

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK) {
        Error_Handler();
    }
}

/**
 * @brief Initialize GPIO pins
 */
static void MX_GPIO_Init(void)
{
    /* Enable GPIO clocks */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    
    /* Configure LED pin (PC13 on Blue Pill) */
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_13;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
}

/**
 * @brief Initialize USART1 for communication with Gateway
 *        PA9 = TX, PA10 = RX
 */
static void MX_USART1_UART_Init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();
    
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    
    if (HAL_UART_Init(&huart1) != HAL_OK) {
        Error_Handler();
    }
    
    /* Enable UART interrupt */
    HAL_NVIC_SetPriority(USART1_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
}

/**
 * @brief Initialize all peripherals
 */
void System_Init(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();
}

/**
 * @brief Get UART handle for OTA communication
 */
UART_HandleTypeDef* System_GetUART(void)
{
    return &huart1;
}

/**
 * @brief Toggle LED for debug
 */
void System_ToggleLED(void)
{
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
}

/**
 * @brief Error handler
 */
static void Error_Handler(void)
{
    __disable_irq();
    while (1) {}
}
