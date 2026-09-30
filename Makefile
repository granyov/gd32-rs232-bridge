PREFIX ?= arm-none-eabi-
HSE ?= 16000000
HOST_BAUD ?= 38400
LOGGER_BAUD ?= 38400
BUILD := build/hse$(HSE)-host$(HOST_BAUD)-logger$(LOGGER_BAUD)
NAME := lazarus-gd32-rs232-hse$(HSE)-$(HOST_BAUD)-$(LOGGER_BAUD)
CC := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy
SIZE := $(PREFIX)size
SDK := Drivers/GD32F10x_standard_peripheral
CMSIS := Drivers/CMSIS
INCLUDES := -ICore/Inc -I$(SDK)/Include -I$(CMSIS) -I$(CMSIS)/GD/GD32F10x/Include
DEFINES := -DGD32F10X_MD -DHXTAL_VALUE=$(HSE)U -DHOST_BAUD=$(HOST_BAUD)U -DLOGGER_BAUD=$(LOGGER_BAUD)U
CPU := -mcpu=cortex-m3 -mthumb -mfloat-abi=soft
CFLAGS := $(CPU) $(INCLUDES) $(DEFINES) -std=c11 -Os -g3 \
 -ffunction-sections -fdata-sections -fno-common -Wall -Wextra -Werror -MMD -MP
SOURCES := Core/Src/main.c Core/Src/bridge.c Core/Src/runtime.c \
 $(CMSIS)/GD/GD32F10x/Source/system_gd32f10x.c \
 $(SDK)/Source/gd32f10x_rcu.c $(SDK)/Source/gd32f10x_gpio.c \
 $(SDK)/Source/gd32f10x_usart.c $(SDK)/Source/gd32f10x_misc.c $(SDK)/Source/gd32f10x_fwdgt.c
STARTUP := Core/Startup/startup_gd32f103c8.s
OBJECTS := $(addprefix $(BUILD)/,$(SOURCES:.c=.o)) $(BUILD)/startup.o
LINKER := GD32F103C8_FLASH.ld

.PHONY: all test verify clean
all: $(BUILD)/$(NAME).hex $(BUILD)/$(NAME).bin

$(BUILD)/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/startup.o: $(STARTUP)
	@mkdir -p $(@D)
	$(CC) $(CPU) -g3 -c $< -o $@

$(BUILD)/$(NAME).elf: $(OBJECTS) $(LINKER)
	$(CC) $(CPU) -nostartfiles --specs=nano.specs --specs=nosys.specs \
	 -T$(LINKER) -Wl,--gc-sections,--print-memory-usage,-Map=$(BUILD)/$(NAME).map \
	 $(OBJECTS) -Wl,--start-group -lc -lgcc -Wl,--end-group -o $@
	$(SIZE) $@

$(BUILD)/$(NAME).hex: $(BUILD)/$(NAME).elf
	$(OBJCOPY) -O ihex $< $@
$(BUILD)/$(NAME).bin: $(BUILD)/$(NAME).elf
	$(OBJCOPY) -O binary $< $@

test:
	@mkdir -p build/tests
	$${HOST_CC:-cc} -std=c11 -Wall -Wextra -Werror -g \
	 -fsanitize=address,undefined -ICore/Inc tests/test_bridge.c Core/Src/bridge.c \
	 -o build/tests/test_bridge
	./build/tests/test_bridge

verify: all
	python3 tests/verify_firmware.py $(BUILD)/$(NAME).elf --prefix $(PREFIX) \
	 --hse $(HSE) --host-baud $(HOST_BAUD) --logger-baud $(LOGGER_BAUD)

clean:
	rm -rf build

-include $(OBJECTS:.o=.d)
